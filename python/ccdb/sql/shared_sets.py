"""Maintenance of shared constant sets: `ccdb db dedup` and `ccdb db rehash`.

Assignments of one CCDB table share a constant set when their data bytes are equal. A database upgraded from schema 5
still holds the duplicates history made, and the sets no assignment uses any more:

    db dedup    merges the duplicates of each table into its oldest set and removes the unused sets; once no table
                holds duplicates, it creates the unique index (constantTypeId, sha256) and drops the interim one.
                Without --dedup-i-am-sure it only reports what it would do.
    db rehash   recomputes sha256 and size of every set (or a sample) and compares them with the stored ones, and on
                MySQL with --server also with the server's own SHA2. With --rehash-i-am-sure it rewrites the
                mismatching hashes.

Both write through the provider's session, so they share its write transactions: BEGIN IMMEDIATE on SQLite, and on
MySQL the restart of a transaction chosen as a deadlock victim. Repointing assignments and deleting sets run as SQL
text: an ORM or Core update() would also rewrite the `modified` column, which neither command changes.
"""
import logging

from sqlalchemy import bindparam, exists, func, select, text
from sqlalchemy.exc import DBAPIError

from ccdb.errors import DataCollisionError, ObjectIsNotFoundInDbError
from ccdb.model import Assignment, ConstantSet, vault_digest
from ccdb.sql import sqlite_schema
from ccdb.sql.update_v6 import (MySqlMaintenance, UPGRADE_SQL_MODE, LOCK_WAIT_TIMEOUT, UNIQUE_INDEX, INTERIM_INDEX,
                                DUPLICATES_ADVICE, ROW_IDS_SHOWN, describe_rows, format_bytes, maintenance_connection,
                                unhashed_condition)

log = logging.getLogger("ccdb.sql.shared_sets")

SETS = ConstantSet.__table__
ASSIGNMENTS = Assignment.__table__

# Ids per IN list. SQLite 3.34 (EL9) allows 32 766 parameters, and one hallddb table holds 29 416 equal sets
ID_CHUNK = 500
REHASH_BATCH = 500
LOG_DESCRIPTION_LENGTH = 255
# Set ids the one rehash log record lists. logs.affectedIds is TEXT on MySQL, 65 535 bytes, and each id takes about
# 19 ('constantSets821431|'): a strict server would reject a longer list and roll back the whole repair with it
LOGGED_SET_IDS = 1000
ER_DUP_ENTRY = 1062       # MySQL: a unique index met two equal keys

REPOINT_ASSIGNMENTS = text("UPDATE assignments SET constantSetId = :survivor WHERE constantSetId IN :others") \
    .bindparams(bindparam("others", expanding=True))
# Guarded: a set that an assignment uses is never deleted, whatever happened since it was read
DELETE_UNUSED_SETS = text("DELETE FROM constantSets WHERE id IN :ids AND NOT EXISTS "
                          "(SELECT 1 FROM assignments WHERE assignments.constantSetId = constantSets.id)") \
    .bindparams(bindparam("ids", expanding=True))


def chunks(ids):
    for start in range(0, len(ids), ID_CHUNK):
        yield ids[start:start + ID_CHUNK]


def table_paths(provider, table_ids):
    """{table id: path}; a set whose table is gone (no typeTables row) gets a description instead"""
    paths = {}
    for table_id in table_ids:
        try:
            paths[table_id] = provider.get_type_table_by_id(table_id).path
        except ObjectIsNotFoundInDbError:
            paths[table_id] = f"(table id {table_id}, no typeTables row)"
    provider.session.commit()     # end the read transaction: on MySQL it would hold metadata locks
    return paths


def unhashed_sets(session, dialect_name, table_id=None):
    """(count, first ids) of the sets whose sha256 is not 64 lowercase hex characters"""
    where = unhashed_condition(dialect_name) + (" AND constantTypeId = :t" if table_id is not None else "")
    params = {"t": table_id} if table_id is not None else {}
    count = session.execute(text(f"SELECT COUNT(*) FROM constantSets WHERE {where}"), params).scalar()
    ids = session.execute(text(f"SELECT id FROM constantSets WHERE {where} ORDER BY id LIMIT {ROW_IDS_SHOWN}"),
                          params).scalars().all() if count else []
    return count, ids


def set_mysql_session(session):
    """The session settings of the upgrade for this transaction's connection: strict mode, short metadata lock waits"""
    session.execute(text(f"SET SESSION sql_mode = :mode, lock_wait_timeout = {LOCK_WAIT_TIMEOUT}"), {"mode": UPGRADE_SQL_MODE})


def listed_ids(set_ids):
    return ", ".join(str(set_id) for set_id in set_ids)


def shorten(description):
    return description if len(description) <= LOG_DESCRIPTION_LENGTH else description[:LOG_DESCRIPTION_LENGTH - 3] + "..."


# ----------------------------------------------------------------------------------------------------------------
#  db dedup
# ----------------------------------------------------------------------------------------------------------------

def dedup(provider, table_path=None, apply=False, transaction_check=True):
    """`ccdb db dedup`: reports the duplicate and unused constant sets per table, and with apply merges and removes them.

    :param provider: a connected AlchemyProvider; its current user signs the log records
    :param table_path: only this table; None for every table
    :param transaction_check: MySQL, with apply: refuse while another session holds a transaction open on the database
    :return: True on success; False when it refused or stopped on a collision (nothing of that table changed)
    """
    return Dedup(provider, table_path, transaction_check).run(apply)


class TableStats:
    """What dedup finds in one table by plain reads, before any lock"""

    def __init__(self):
        self.groups = 0        # sets of equal sha256, each group with more than one set
        self.duplicates = 0    # sets that would go: every group member but the oldest
        self.saved_bytes = 0
        self.moved = 0         # assignments that would move to their group's oldest set
        self.unused = 0        # sets no assignment uses that remain after the merge
        self.unused_bytes = 0

    def has_work(self):
        return bool(self.groups or self.unused)


class Dedup:
    def __init__(self, provider, table_path, transaction_check):
        self.provider = provider
        self.session = provider.session
        self.dialect = provider.engine.dialect.name
        self.table_path = table_path
        self.transaction_check = transaction_check

    def run(self, apply):
        if apply and self.dialect != "sqlite" and not self.transaction_preflight():
            return False
        table_id = self.provider.get_type_table(self.table_path).id if self.table_path else None
        unhashed, unhashed_ids = unhashed_sets(self.session, self.dialect, table_id)
        stats = self.table_stats(table_id)
        paths = table_paths(self.provider, sorted(stats))
        if unhashed:
            message = (f"{describe_rows(unhashed, unhashed_ids)} of constantSets have a sha256 that is not 64 lowercase hex "
                       "characters, so their duplicates cannot be found. Run 'ccdb db rehash --rehash-i-am-sure' first")
            if apply:
                # before any change: a set without a valid hash could equal any other
                log.error("Dedup refused, nothing was changed: " + message)
                return False
            log.warning(message)
        if not apply:
            self.print_report(stats, paths)
            return True

        merged = groups = removed = 0
        for table_id in sorted(stats):
            if not stats[table_id].has_work():
                continue
            try:
                table_merged, table_groups, table_removed = self.provider._run_write_transaction(
                    lambda: self.dedup_table(table_id, paths[table_id]))
            except DataCollisionError as collision:
                # the exception's own text speaks of new data, which dedup has none of: the message is built here
                set_ids = ", ".join(str(set_id) for set_id in collision.set_ids)
                log.error(f"Dedup stopped: constant sets {set_ids} of '{collision.table_path}' have sha256 "
                          f"{collision.sha256} but different bytes. That table was left unchanged; the tables before "
                          "it are deduplicated. Two sets with one sha256 and other bytes mean corrupt data or a broken "
                          "hash: inspect them, then run dedup again")
                return False
            merged, groups, removed = merged + table_merged, groups + table_groups, removed + table_removed
            if table_merged or table_removed:
                print(f"{paths[table_id]}: merged {table_merged} constant sets into {table_groups}, "
                      f"removed {table_removed} unused sets")
        print(f"Dedup: merged {merged} constant sets into {groups}, removed {removed} unused sets")
        return self.swap_index()

    def transaction_preflight(self):
        """The open-transaction check of the upgrade: dedup locks sets and changes an index"""
        maintenance = MySqlMaintenance(self.provider.engine, transaction_check=self.transaction_check)
        with maintenance_connection(self.provider.engine) as conn:
            maintenance.conn = conn
            problems = maintenance.transaction_problems()
        if problems:
            log.error("Dedup refused, nothing was changed: " + "; ".join(problems))
            return False
        return True

    # ------------------------------------------------------------------ plain reads

    def table_stats(self, table_id):
        """{table id: TableStats} of the tables with duplicate or unused sets, by plain reads of sha256 and size"""
        only = "AND constantTypeId = :t " if table_id is not None else ""
        params = {"t": table_id} if table_id is not None else {}
        groups = (f"SELECT constantTypeId, sha256, COUNT(*) AS members, MAX(size) AS size, MIN(id) AS survivor "
                  f"FROM constantSets WHERE 1 = 1 {only}GROUP BY constantTypeId, sha256 HAVING COUNT(*) > 1")
        stats = {}
        for type_id, group_count, duplicates, saved in self.session.execute(text(
                f"SELECT g.constantTypeId, COUNT(*), SUM(g.members - 1), SUM((g.members - 1) * g.size) FROM ({groups}) g "
                "GROUP BY g.constantTypeId"), params):
            table = stats.setdefault(type_id, TableStats())
            table.groups, table.duplicates, table.saved_bytes = group_count, int(duplicates), int(saved or 0)
        for type_id, moved in self.session.execute(text(
                "SELECT s.constantTypeId, COUNT(*) FROM assignments a JOIN constantSets s ON s.id = a.constantSetId "
                f"JOIN ({groups}) g ON g.constantTypeId = s.constantTypeId AND g.sha256 = s.sha256 "
                "WHERE s.id <> g.survivor GROUP BY s.constantTypeId"), params):
            stats.setdefault(type_id, TableStats()).moved = moved
        # what step 5 of a table's dedup removes: the sets no assignment uses, unless an equal set of the table
        # has one (it is repointed to the group's oldest set then); of an unused group only its oldest set is left
        only = only.replace("constantTypeId", "s.constantTypeId")
        for type_id, unused, unused_bytes in self.session.execute(text(
                "SELECT s.constantTypeId, COUNT(*), SUM(s.size) FROM constantSets s "
                "WHERE NOT EXISTS (SELECT 1 FROM constantSets o WHERE o.constantTypeId = s.constantTypeId "
                "AND o.sha256 = s.sha256 AND o.id < s.id) "
                "AND NOT EXISTS (SELECT 1 FROM constantSets o JOIN assignments a ON a.constantSetId = o.id "
                f"WHERE o.constantTypeId = s.constantTypeId AND o.sha256 = s.sha256) {only}GROUP BY s.constantTypeId"), params):
            table = stats.setdefault(type_id, TableStats())
            table.unused, table.unused_bytes = unused, int(unused_bytes or 0)
        self.session.commit()
        return stats

    def print_report(self, stats, paths):
        print("Dedup report, nothing is changed (add --dedup-i-am-sure to merge and remove):")
        totals = TableStats()
        for table_id in sorted(stats, key=lambda key: paths[key]):
            table = stats[table_id]
            print(f"  {paths[table_id]}: {table.groups} groups of equal sets, {table.duplicates} sets would go "
                  f"({format_bytes(table.saved_bytes)}), {table.moved} assignments would move to the oldest set of their "
                  f"group, {table.unused} unused sets would be removed ({format_bytes(table.unused_bytes)})")
            for name in ("groups", "duplicates", "saved_bytes", "moved", "unused", "unused_bytes"):
                setattr(totals, name, getattr(totals, name) + getattr(table, name))
        if not stats:
            print("  no table holds duplicate or unused constant sets")
        print(f"In all: {len(stats)} tables, {totals.groups} groups, {totals.duplicates} sets would go, "
              f"{totals.moved} assignments would move, {totals.unused} unused sets would be removed, "
              f"{format_bytes(totals.saved_bytes + totals.unused_bytes)} saved")

    # ------------------------------------------------------------------ one table, one transaction

    def dedup_table(self, table_id, path):
        """Merges the table's duplicates into the oldest set of each group and removes its unused sets, in one
        transaction. Returns (sets merged, groups, unused sets removed)."""
        self.provider._begin_write_transaction()
        if self.dialect != "sqlite":
            set_mysql_session(self.session)

        # the groups by a plain read; each group is then what its lock returns, since rm -a may have deleted a member
        shas = self.session.execute(select(SETS.c.sha256).where(SETS.c.constantTypeId == table_id)
                                    .group_by(SETS.c.sha256).having(func.count() > 1)).scalars().all()
        merged = groups = 0
        for sha256 in shas:
            rows = self.session.execute(select(SETS.c.id, SETS.c.vault)
                                        .where(SETS.c.constantTypeId == table_id, SETS.c.sha256 == sha256)
                                        .order_by(SETS.c.id).with_for_update()).all()
            if len(rows) < 2:
                continue
            survivor_id, survivor_vault = rows[0]
            # bytes compared in Python: the column collation ignores case and trailing spaces
            unequal = [set_id for set_id, vault in rows[1:] if vault != survivor_vault]
            if unequal:
                raise DataCollisionError(path, sha256, [survivor_id] + unequal)
            others = [set_id for set_id, _ in rows[1:]]
            for chunk in chunks(others):
                self.session.execute(REPOINT_ASSIGNMENTS, {"survivor": survivor_id, "others": chunk})
                merged += self.session.execute(DELETE_UNUSED_SETS, {"ids": chunk}).rowcount
            groups += 1

        removed = self.remove_unused_sets(table_id)
        if merged or removed:
            self.provider.create_log_record(user=self.provider.get_current_user(),
                                            affected_ids=[f"typeTables{table_id}"],
                                            action="update",
                                            description=f"Merged {merged} constant sets into {groups}, removed {removed} unused sets",
                                            comment=f"ccdb db dedup of '{path}'",
                                            commit=False)
        self.session.commit()
        return merged, groups, removed

    def remove_unused_sets(self, table_id):
        """Deletes the table's sets that no assignment uses. The candidates come from a plain read; each is locked,
        then its assignments are read with a locking read, which sees an assignment that a writer holding the set
        committed while this transaction waited for the lock. Returns the number deleted."""
        candidates = self.session.execute(
            select(SETS.c.id).where(SETS.c.constantTypeId == table_id)
            .where(~exists().where(ASSIGNMENTS.c.constantSetId == SETS.c.id))).scalars().all()
        removed = 0
        for chunk in chunks(candidates):
            locked = self.session.execute(select(SETS.c.id).where(SETS.c.id.in_(chunk)).with_for_update()).scalars().all()
            if not locked:
                continue
            used = set(self.session.execute(select(ASSIGNMENTS.c.constantSetId)
                                            .where(ASSIGNMENTS.c.constantSetId.in_(locked))
                                            .with_for_update(read=True)).scalars().all())
            unused = [set_id for set_id in locked if set_id not in used]
            if unused:
                removed += self.session.execute(DELETE_UNUSED_SETS, {"ids": unused}).rowcount
        return removed

    # ------------------------------------------------------------------ the unique index

    def swap_index(self):
        """When no table holds duplicates any more: the unique index, created only if absent, and the interim index
        dropped only if present. Returns False when a writer stored a duplicate before the index was built."""
        # A set whose sha256 is not valid hex may equal any set of its table, so its duplicates are unknown. A --table
        # run checked only its own table before it changed anything; the index needs every table checked.
        unhashed, unhashed_ids = unhashed_sets(self.session, self.dialect)
        self.session.commit()
        if unhashed:
            log.warning(f"{describe_rows(unhashed, unhashed_ids)} of constantSets have a sha256 that is not 64 lowercase "
                        "hex characters, so their duplicates are unknown and the constantSets indexes stay as they are. "
                        "Run 'ccdb db rehash --rehash-i-am-sure', then 'ccdb db dedup --dedup-i-am-sure'")
            return True
        if self.dialect == "sqlite":
            return self.provider._run_write_transaction(self.swap_index_sqlite)
        has_duplicates = self.has_duplicates()
        self.session.commit()
        if has_duplicates:
            log.warning(DUPLICATES_ADVICE)
            return True
        maintenance = MySqlMaintenance(self.provider.engine)
        with maintenance_connection(self.provider.engine) as conn:
            maintenance.conn = conn
            maintenance.read_server()
            maintenance.set_session()
            indexes = maintenance.indexes("constantSets")
            if UNIQUE_INDEX not in indexes:
                try:
                    maintenance.execute_ddl(f"ALTER TABLE `constantSets` ADD UNIQUE INDEX `{UNIQUE_INDEX}` "
                                            "(`constantTypeId`, `sha256`), ALGORITHM=INPLACE, LOCK=NONE")
                except DBAPIError as error:
                    if error.orig is None or error.orig.args[0] != ER_DUP_ENTRY:
                        raise
                    log.error(f"The unique index {UNIQUE_INDEX} was not created: a writer stored a duplicate set while "
                              "it was built. Run 'ccdb db dedup --dedup-i-am-sure' again")
                    return False
            if INTERIM_INDEX in indexes:
                maintenance.execute_ddl(f"ALTER TABLE `constantSets` DROP INDEX `{INTERIM_INDEX}`, ALGORITHM=INPLACE, LOCK=NONE")
        return True

    def swap_index_sqlite(self):
        """The index swap on SQLite in one write transaction. The duplicate check runs inside BEGIN IMMEDIATE, so no
        writer can store a duplicate between the check and the index."""
        self.provider._begin_write_transaction()
        if self.has_duplicates():
            self.session.commit()
            log.warning(DUPLICATES_ADVICE)
            return True
        # both statements are IF [NOT] EXISTS: created only if absent, dropped only if present
        for statement in sqlite_schema._iter_statements(sqlite_schema.constant_sets_unique_index):
            self.session.execute(text(statement))
        self.session.execute(text(f'DROP INDEX IF EXISTS "{INTERIM_INDEX}"'))
        self.session.commit()
        return True

    def has_duplicates(self):
        """Whether any CCDB table holds two sets with one sha256"""
        return self.session.execute(text(
            "SELECT 1 FROM constantSets GROUP BY constantTypeId, sha256 HAVING COUNT(*) > 1 LIMIT 1")).first() is not None


# ----------------------------------------------------------------------------------------------------------------
#  db rehash
# ----------------------------------------------------------------------------------------------------------------

def rehash(provider, sample=None, server=False, apply=False):
    """`ccdb db rehash`: recomputes vault_digest of every set, or of `sample` sets spread over the id range, and compares
    it with the stored sha256 and size; with server (MySQL) also with SHA2 and LENGTH of the utf8mb4 text on the server.

    :param apply: rewrite the mismatching stored hashes. A rewrite that makes two sets of one table equal is done while
                  only the interim index exists and reported for `db dedup`; once the unique index exists it is refused
    :return: True when nothing mismatches, or apply repaired every mismatch; False otherwise
    """
    return Rehash(provider, sample, server).run(apply)


class Mismatch:
    def __init__(self, set_id, table_id, stored, computed):
        self.set_id = set_id
        self.table_id = table_id
        self.stored = stored        # (sha256, size) in the database
        self.computed = computed    # (sha256, size) of vault_digest


class Rehash:
    def __init__(self, provider, sample, server):
        self.provider = provider
        self.session = provider.session
        self.dialect = provider.engine.dialect.name
        self.sample = sample
        self.server = server

    def run(self, apply):
        if self.server and self.dialect == "sqlite":
            log.error("--server compares with the database server's SHA2() and needs MySQL or MariaDB; "
                      "it is refused on SQLite")
            return False
        if self.sample is not None and self.sample < 1:
            log.error("--sample needs a positive number of sets")
            return False

        mismatches, disagreements, checked = [], [], 0
        for rows in self.batches():
            for row in rows:
                set_id, table_id, vault, sha256, size = row[:5]
                computed = vault_digest(vault)
                checked += 1
                if (sha256, size) != computed:
                    mismatches.append(Mismatch(set_id, table_id, (sha256, size), computed))
                if self.server and (row[5], int(row[6])) != computed:
                    disagreements.append((set_id, (row[5], int(row[6])), computed))

        what = f"{checked} constant sets" + (" (a sample spread over the id range)" if self.sample else "")
        print(f"Rehash: checked {what}" + (", also against the server's SHA2" if self.server else ""))
        for mismatch in mismatches:
            print(f"  constant set {mismatch.set_id} (table id {mismatch.table_id}): stored sha256 {mismatch.stored[0]!r} "
                  f"size {mismatch.stored[1]}, its data gives sha256 {mismatch.computed[0]} size {mismatch.computed[1]}")
        for set_id, on_server, computed in disagreements:
            print(f"  constant set {set_id}: the server's SHA2 and LENGTH of the utf8mb4 text give {on_server[0]} "
                  f"{on_server[1]}, Python's vault_digest {computed[0]} {computed[1]}: the two implementations disagree")
        if not mismatches and not disagreements:
            print("  every stored hash equals the data")
            return True
        if not apply:
            print(f"  {len(mismatches)} mismatches; add --rehash-i-am-sure to rewrite the stored hashes")
            return False
        if not mismatches:
            return False

        rewritten, now_equal, refused = self.provider._run_write_transaction(lambda: self.rewrite(mismatches))
        print(f"  rewrote the hashes of {len(rewritten)} constant sets")
        for mismatch, equal_ids in now_equal:
            print(f"  constant set {mismatch.set_id} now has the hash of constant sets {listed_ids(equal_ids)} of the same "
                  "table, whose data it equals; 'ccdb db dedup --dedup-i-am-sure' merges them")
        for mismatch, equal_ids in refused:
            print(f"  constant set {mismatch.set_id} not rewritten: its data equals constant sets {listed_ids(equal_ids)} "
                  f"of the same table, and the unique index {UNIQUE_INDEX} allows one set per hash in a table. Point its "
                  f"assignments to constant set {equal_ids[0]} and delete it with SQL, then rerun rehash")
        return not refused and not disagreements

    def batches(self):
        """The sets to check in batches of (id, table id, vault, sha256, size[, server sha256, server size]).
        Each batch ends its read transaction, which on MySQL would hold metadata locks."""
        columns = "id, constantTypeId, vault, sha256, size"
        if self.server:
            columns += ", SHA2(CONVERT(vault USING utf8mb4), 256), LENGTH(CONVERT(vault USING utf8mb4))"
        if self.sample:
            ids = self.sample_ids()
            for chunk in chunks(ids):
                rows = self.session.execute(text(f"SELECT {columns} FROM constantSets WHERE id IN :ids ORDER BY id")
                                            .bindparams(bindparam("ids", expanding=True)), {"ids": chunk}).all()
                self.session.commit()
                yield rows
            return
        last_id = None
        while True:
            where = "WHERE id > :last " if last_id is not None else ""
            rows = self.session.execute(text(f"SELECT {columns} FROM constantSets {where}ORDER BY id LIMIT {REHASH_BATCH}"),
                                        {"last": last_id} if last_id is not None else {}).all()
            self.session.commit()
            if not rows:
                return
            yield rows
            last_id = rows[-1][0]

    def sample_ids(self):
        """The first set at or after each of `sample` points spread evenly between the smallest and the largest id"""
        low, high = self.session.execute(text("SELECT MIN(id), MAX(id) FROM constantSets")).one()
        if low is None:
            return []
        steps = max(self.sample - 1, 1)
        ids = set()
        for point in sorted({low + (high - low) * i // steps for i in range(self.sample)}):
            set_id = self.session.execute(text("SELECT id FROM constantSets WHERE id >= :point ORDER BY id LIMIT 1"),
                                          {"point": point}).scalar()
            if set_id is not None:
                ids.add(set_id)
        self.session.commit()
        return sorted(ids)

    def rewrite(self, mismatches):
        """Rewrites the mismatching hashes in one transaction with one log record. Equal sets are merged by dedup, never
        here: a rewrite that gives a set the hash of another set of its table is done while only the interim index
        exists, so dedup finds the pair, and refused once the unique index exists, which would reject it.
        Returns (rewritten set ids, [(mismatch, ids of the equal sets)] rewritten, [(mismatch, ids of the equal sets)]
        refused)."""
        self.provider._begin_write_transaction()
        if self.dialect != "sqlite":
            set_mysql_session(self.session)
        unique = self.has_unique_index()
        rewritten, now_equal, refused, claimed = [], [], [], {}
        for mismatch in mismatches:
            sha256, size = mismatch.computed
            equal_ids = set(self.session.execute(
                select(SETS.c.id).where(SETS.c.constantTypeId == mismatch.table_id, SETS.c.sha256 == sha256,
                                        SETS.c.id != mismatch.set_id).with_for_update()).scalars().all())
            equal_ids |= claimed.get((mismatch.table_id, sha256), set())
            if equal_ids and unique:
                refused.append((mismatch, sorted(equal_ids)))
                continue
            if equal_ids:
                now_equal.append((mismatch, sorted(equal_ids)))
            claimed.setdefault((mismatch.table_id, sha256), set()).add(mismatch.set_id)
            # SQL text: a Core or ORM update() would also rewrite constantSets.modified
            self.session.execute(text("UPDATE constantSets SET sha256 = :sha256, size = :size WHERE id = :id"),
                                 {"sha256": sha256, "size": size, "id": mismatch.set_id})
            rewritten.append(mismatch.set_id)
        if rewritten:
            listed = rewritten[:LOGGED_SET_IDS]
            what = (f"Rehashed {len(rewritten)} constant sets" +
                    (f", the first {len(listed)} listed" if len(listed) < len(rewritten) else ""))
            self.provider.create_log_record(user=self.provider.get_current_user(),
                                            affected_ids=[f"constantSets{set_id}" for set_id in listed],
                                            action="update",
                                            description=shorten(what + ": " + ", ".join(str(i) for i in listed)),
                                            comment="ccdb db rehash --rehash-i-am-sure: the stored sha256 and size did "
                                                    "not match the data",
                                            commit=False)
        self.session.commit()
        return rewritten, now_equal, refused

    def has_unique_index(self):
        """Whether constantSets has the unique index of (table, sha256) rather than the interim one"""
        if self.dialect == "sqlite":
            sql = "SELECT COUNT(*) FROM sqlite_master WHERE type = 'index' AND name = :name"
        else:
            sql = ("SELECT COUNT(*) FROM information_schema.STATISTICS "
                   "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'constantSets' AND INDEX_NAME = :name")
        return self.session.execute(text(sql), {"name": UNIQUE_INDEX}).scalar() > 0
