"""Schema 6 to 5 rollback, run by `ccdb db rollback-v6 --rollback-i-am-sure`.

It drops what the schema 6 upgrade (ccdb.sql.update_v6) added and sets the version to 5, so CCDB 2.4 can work on the
database again. Like the upgrade it checks, then acts: it takes version 6, and version 5 with some schema 6 objects
(an interrupted upgrade), and drops only the objects that exist:
    constantSets    sha256, size, the unique and the interim index on (constantTypeId, sha256)
    assignments     timeRangeId and its index
    columns         units
    directories, typeTables, variations     deprecatedTime, deprecationComment
    tags            the columns added to it and its new indexes; name back to VARCHAR(45)
    timeRanges, properties                  the tables
The schema 5 columns the upgrade added to files upgraded from v4 (isDeprecated, deprecatedByUserId, isLocked,
lockedByUserId) stay: they belong to schema 5.

What stays changed: engines and character sets (2.4 works on InnoDB and utf8mb4), and merged duplicates (their bytes
were identical, so no data is lost). After dedup many assignments share a set, and 2.4's `rm -a` of one of them would
delete the shared set on a non-strict server, so the rollback refuses there unless --allow-non-strict.

It refuses while schema 6 data exists (rows in tags, properties or timeRanges; values in units, deprecatedTime,
deprecationComment or timeRangeId) unless --drop-v6-data, which deletes those rows first. The rollback writes no
`logs` row; schemaVersions records the change.

SQLite has no DROP COLUMN before 3.35 (EL9 ships 3.34.1), so every changed table is rebuilt; the rollback works on a
copy that replaces the file and keeps the file before the rollback as <file>.before-rollback, as the upgrade does
(--in-place skips the copy).
"""
import logging
import os
import re
import sqlite3

from sqlalchemy import text

from ccdb.sql.update_v6 import (MySqlMaintenance, UpgradeRefusedError, UPGRADE_PRIVILEGES, UNIQUE_INDEX, INTERIM_INDEX,
                                SOURCE_VERSION, check_version_rows, replace_with_changed_copy,
                                split_create_table, renamed_head, sqlite_file_or_refuse, sqlite_read_only,
                                sqlite_tables, sqlite_columns)

log = logging.getLogger("ccdb.sql.rollback_v6")

ROLLBACK_PRIVILEGES = UPGRADE_PRIVILEGES + ["DROP"]
ACCEPTED_VERSIONS = (6, SOURCE_VERSION)     # 5: a partly upgraded database still says 5
VERSION_TEXT = "'ccdb db rollback-v6' takes schema version 6, or a partly upgraded 5, to 5"

# (table, column) the upgrade added
V6_COLUMNS = ([("constantSets", "sha256"), ("constantSets", "size"), ("assignments", "timeRangeId"), ("columns", "units")]
              + [(table, column) for table in ("directories", "typeTables", "variations")
                 for column in ("deprecatedTime", "deprecationComment")]
              + [("tags", column) for column in ("variationId", "snapshotTime", "comment", "authorId", "created")])

# (table, index) the upgrade added; on SQLite the index of timeRangeId is prefixed with its table's name
V6_INDEXES = [("constantSets", UNIQUE_INDEX), ("constantSets", INTERIM_INDEX),
              ("assignments", "fk_assignments_timeRanges1_idx"), ("assignments", "assignments_fk_assignments_timeRanges1_idx"),
              ("tags", "uq_tags_name"), ("tags", "fk_tags_variations1_idx")]

V6_TABLES = ["timeRanges", "properties"]

# Columns that hold schema 6 data when not NULL; sha256 and size are computed from the vault and are not data
V6_DATA_COLUMNS = [("columns", "units"), ("assignments", "timeRangeId")] + \
                  [(table, column) for table in ("directories", "typeTables", "variations")
                   for column in ("deprecatedTime", "deprecationComment")]

TAGS_V5_NAME_LENGTH = 45
STRICT_MODES = ("STRICT_TRANS_TABLES", "STRICT_ALL_TABLES")


class RollbackRefusedError(UpgradeRefusedError):
    """The rollback's preflight found a reason not to roll back. Nothing was changed; the message names the reason."""


def rollback_v6(engine, drop_v6_data=False, allow_non_strict=False, in_place=False, skip_privilege_check=False,
                transaction_check=True):
    """Rolls the CCDB database behind the engine back from schema 6 to 5.

    :param drop_v6_data: delete the rows of tags, properties and timeRanges instead of refusing while they exist
    :param allow_non_strict: MySQL: roll back although the server's global sql_mode is not strict
    :param in_place: SQLite: change the file itself instead of a copy that replaces it
    :raises RollbackRefusedError: the preflight refused; nothing was changed
    """
    if engine.dialect.name == "sqlite":
        SqliteRollback(engine.url.database, drop_v6_data).run(in_place)
    else:
        MySqlRollback(engine, drop_v6_data, allow_non_strict, skip_privilege_check, transaction_check).run()


def refuse(problems):
    if problems:
        raise RollbackRefusedError("The rollback to schema 5 is refused, nothing was changed:\n  " + "\n  ".join(problems))


def v6_data_problem(counts):
    if not counts:
        return []
    listed = ", ".join(f"{label}: {count}" for label, count in counts)
    return [f"schema 6 data exists ({listed}). 2.4 cannot hold it; add --drop-v6-data to delete it with the rollback"]


# ----------------------------------------------------------------------------------------------------------------
#  MySQL and MariaDB
# ----------------------------------------------------------------------------------------------------------------

class MySqlRollback(MySqlMaintenance):
    """The rollback on MySQL or MariaDB: one ALTER per changed table, then the new tables dropped and version 5"""

    def __init__(self, engine, drop_v6_data, allow_non_strict, skip_privilege_check, transaction_check):
        MySqlMaintenance.__init__(self, engine, skip_privilege_check, transaction_check)
        self.drop_v6_data = drop_v6_data
        self.allow_non_strict = allow_non_strict

    def run(self):
        with self.engine.connect() as conn:
            self.conn = conn
            self.read_server()
            log.info(f"Server: {self.server_version}")
            self.preflight()
            self.set_session()
            if self.drop_v6_data:
                self.delete_v6_data()
            for statement in self.plan():
                self.execute_ddl(statement)
            self.execute_with_retries(text("UPDATE schemaVersions SET schemaVersion = :v"), "the UPDATE of schemaVersions",
                                      {"v": SOURCE_VERSION})
            log.info(f"Schema version is {SOURCE_VERSION}")

    def preflight(self):
        tables = self.tables()
        check_version_rows(self.schema_versions(tables), ACCEPTED_VERSIONS, VERSION_TEXT)
        problems = self.privilege_problems(ROLLBACK_PRIVILEGES) + self.transaction_problems() + self.strict_problems()
        if not self.drop_v6_data:
            problems += v6_data_problem(self.v6_data_counts(tables))
        refuse(problems)

    def strict_problems(self):
        """After dedup many assignments share a set. 2.4 deletes a set with its assignment (a cascade), so on a strict
        server its `rm -a` of a sharer fails; on a non-strict one it deletes the shared set and points the other
        sharers at set 0."""
        sql_mode = self.query("SELECT @@GLOBAL.sql_mode")[0][0] or ""
        if any(mode in sql_mode.upper().split(",") for mode in STRICT_MODES):
            return []
        message = (f"the server's global sql_mode '{sql_mode}' is not strict. After 'ccdb db dedup' assignments share "
                   "constant sets, and there CCDB 2.4's 'rm -a' of one of them deletes the shared set and points the "
                   "other assignments at set 0")
        if self.allow_non_strict:
            log.warning(message + "; rolling back, as --allow-non-strict asks")
            return []
        return [message + ". Make the server strict (STRICT_TRANS_TABLES), or add --allow-non-strict"]

    def v6_data_counts(self, tables):
        counts = []
        if "tags" in tables and "snapshotTime" in self.columns("tags"):
            counts.append(("rows in tags", self.query("SELECT COUNT(*) FROM `tags`")[0][0]))
        for table in V6_TABLES:
            if table in tables:
                counts.append((f"rows in {table}", self.query(f"SELECT COUNT(*) FROM `{table}`")[0][0]))
        for table, column in V6_DATA_COLUMNS:
            if table in tables and column in self.columns(table):
                count = self.query(f"SELECT COUNT(*) FROM `{table}` WHERE `{column}` IS NOT NULL")[0][0]
                counts.append((f"{table}.{column} values", count))
        return [(label, count) for label, count in counts if count]

    def delete_v6_data(self):
        """The rows of the schema 6 tables; the columns holding schema 6 values are dropped with their values"""
        tables = self.tables()
        deletes = [table for table in V6_TABLES if table in tables]
        if "tags" in tables and "snapshotTime" in self.columns("tags"):
            deletes.append("tags")
        for table in deletes:
            log.info(f"DELETE FROM `{table}`")
            self.execute_with_retries(text(f"DELETE FROM `{table}`"), f"DELETE FROM `{table}`")

    def plan(self):
        """One ALTER per changed table, with its lock clause, then the DROP TABLE statements"""
        statements = []
        tables = self.tables()
        for table in tables:
            columns = self.columns(table)
            indexes = self.indexes(table)
            clauses = [f"DROP INDEX `{index}`" for t, index in V6_INDEXES if t == table and index in indexes]
            dropped_columns = [column for t, column in V6_COLUMNS if t == table and column in columns]
            clauses += [f"DROP COLUMN `{column}`" for column in dropped_columns]
            narrows_name = table == "tags" and columns.get("name", ("",) * 5)[1] != f"varchar({TAGS_V5_NAME_LENGTH})"
            if narrows_name:
                # keep the column's charset and collation: the rollback leaves the conversion to utf8mb4 in place
                _, _, charset, collation, _ = columns["name"]
                clauses.append(f"MODIFY `name` VARCHAR({TAGS_V5_NAME_LENGTH}) CHARACTER SET {charset} COLLATE {collation} NOT NULL")
            if not clauses:
                continue
            if narrows_name:
                # a narrowing crosses the 255-byte length-prefix boundary in utf8mb4; both servers reject INPLACE
                lock_clause = "ALGORITHM=COPY, LOCK=SHARED"
            elif dropped_columns and not self.instant_add_column:
                # MariaDB before 10.6.9 drops a column instantly with a plain INPLACE, the format MDEV-18519 can corrupt
                lock_clause = "FORCE, ALGORITHM=INPLACE, LOCK=NONE"
            else:
                lock_clause = "ALGORITHM=INPLACE, LOCK=NONE"
            statements.append(f"ALTER TABLE `{table}` " + ", ".join(clauses + [lock_clause]))
        statements += [f"DROP TABLE `{table}`" for table in V6_TABLES if table in tables]
        return statements


# ----------------------------------------------------------------------------------------------------------------
#  SQLite
# ----------------------------------------------------------------------------------------------------------------

class SqliteRollback:
    """The rollback of an SQLite file in one transaction, every changed table rebuilt"""

    def __init__(self, path, drop_v6_data):
        self.path = path
        self.drop_v6_data = drop_v6_data
        self.conn = None

    def run(self, in_place=False):
        sqlite_file_or_refuse(self.path)
        conn = sqlite_read_only(self.path)
        try:
            self.preflight(conn, check_kept_file=not in_place)
        finally:
            conn.close()

        if not in_place:
            # tags, properties and timeRanges lose their rows with --drop-v6-data, or the tables themselves
            replace_with_changed_copy(self.path, ".rollback-v6", ".before-rollback", self.change, SOURCE_VERSION,
                                      uncounted_tables=["tags"] + V6_TABLES)
            log.info(f"Schema version is {SOURCE_VERSION}. Delete '{self.path}.before-rollback' when you are satisfied")
            return
        conn = sqlite3.connect(f"file:{self.path}?mode=rw", uri=True, isolation_level=None)
        try:
            self.change(conn, begin="BEGIN IMMEDIATE")
        finally:
            conn.close()
        log.info(f"Schema version is {SOURCE_VERSION}")

    def preflight(self, conn, check_kept_file):
        versions = [row[0] for row in conn.execute("SELECT schemaVersion FROM schemaVersions")] \
            if "schemaVersions" in sqlite_tables(conn) else []
        check_version_rows(versions, ACCEPTED_VERSIONS, VERSION_TEXT)
        problems = []
        kept = self.path + ".before-rollback"
        if check_kept_file and os.path.exists(kept):
            problems.append(f"'{kept}' exists: an earlier rollback kept its file there. Move it away, then run the "
                            "rollback again")
        if not self.drop_v6_data:
            problems += v6_data_problem(self.v6_data_counts(conn))
        refuse(problems)

    @staticmethod
    def v6_data_counts(conn):
        tables = sqlite_tables(conn)
        counts = []
        if "tags" in tables and "snapshotTime" in sqlite_columns(conn, "tags"):
            counts.append(("rows in tags", conn.execute('SELECT COUNT(*) FROM "tags"').fetchone()[0]))
        for table in V6_TABLES:
            if table in tables:
                counts.append((f"rows in {table}", conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]))
        for table, column in V6_DATA_COLUMNS:
            if table in tables and column in sqlite_columns(conn, table):
                count = conn.execute(f'SELECT COUNT(*) FROM "{table}" WHERE "{column}" IS NOT NULL').fetchone()[0]
                counts.append((f"{table}.{column} values", count))
        return [(label, count) for label, count in counts if count]

    def execute(self, sql, params=()):
        log.info(sql)
        return self.conn.execute(sql, params)

    def change(self, conn, begin="BEGIN"):
        """Every schema 6 object dropped in one transaction: an interruption changes nothing"""
        self.conn = conn
        self.conn.execute(begin)
        try:
            tables = sqlite_tables(conn)
            if self.drop_v6_data:
                for table in V6_TABLES + ["tags"]:
                    if table in tables and (table != "tags" or "snapshotTime" in sqlite_columns(conn, "tags")):
                        self.execute(f'DELETE FROM "{table}"')
            for table in sorted({table for table, _ in V6_COLUMNS} & tables):
                columns = sqlite_columns(conn, table)
                dropped = [column for t, column in V6_COLUMNS if t == table and column in columns]
                retyped = {}
                if table == "tags" and dropped:
                    retyped["name"] = f'"name" varchar({TAGS_V5_NAME_LENGTH}) NOT NULL'
                if dropped:
                    self.rebuild_table(table, dropped, retyped, {index for t, index in V6_INDEXES if t == table})
            for table in V6_TABLES:
                if table in tables:
                    self.execute(f'DROP TABLE "{table}"')
            self.execute("UPDATE schemaVersions SET schemaVersion = ?", (SOURCE_VERSION,))
            self.conn.execute("COMMIT")
        except BaseException:
            self.conn.execute("ROLLBACK")
            raise

    def rebuild_table(self, table, dropped, retyped, dropped_indexes):
        """The table without the dropped columns: a new table from its own CREATE statement, the kept columns copied,
        the old table dropped and the new one renamed; then the indexes that use no dropped column recreated"""
        create = self.conn.execute("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)).fetchone()[0]
        indexes = []
        for name, sql in self.conn.execute("SELECT name, sql FROM sqlite_master WHERE type = 'index' AND tbl_name = ? "
                                           "AND sql IS NOT NULL", (table,)).fetchall():
            index_columns = {row[2] for row in self.conn.execute(f'PRAGMA index_info("{name}")')}
            if name not in dropped_indexes and not index_columns & set(dropped):
                indexes.append(sql)
        kept = [column for column in sqlite_columns(self.conn, table) if column not in dropped]

        new_table = f"{table}_v5"
        quoted = ", ".join(f'"{column}"' for column in kept)
        self.execute(f'DROP TABLE IF EXISTS "{new_table}"')
        self.execute(create_without_columns(create, new_table, dropped, retyped))
        self.execute(f'INSERT INTO "{new_table}" ({quoted}) SELECT {quoted} FROM "{table}"')
        self.execute(f'DROP TABLE "{table}"')
        self.execute(f'ALTER TABLE "{new_table}" RENAME TO "{table}"')
        for sql in indexes:
            self.execute(sql)


_LEADING_NAME = re.compile(r'^\s*(?:"([^"]+)"|`([^`]+)`|\[([^\]]+)\]|(\w+))')


def create_without_columns(create_sql, new_name, dropped, retyped):
    """A CREATE TABLE statement from sqlite_master, renamed to new_name, without the dropped column definitions and
    with the retyped ones ({column: full definition}) replaced. Table constraints stay as they are."""
    head, items, tail = split_create_table(create_sql)
    kept = []
    for item in items:
        match = _LEADING_NAME.match(item)
        column = next((group for group in match.groups() if group), None) if match else None
        if column in dropped:
            continue
        if column in retyped:
            item = "\n  " + retyped[column]
        kept.append(item)
    return renamed_head(head, new_name) + "(" + ",".join(kept) + tail
