"""Schema 5 to 6 upgrade, run by `ccdb db upgrade --upgrade-i-am-sure`.

The operator's guide is docs/deployment/upgrade-2.5.md. Every step checks, then acts: an object that
exists already is left alone, so a rerun after an interruption continues where the last run stopped, and a run on
a database that has every schema 6 object changes nothing. The version is written last.

MySQL and MariaDB, on one connection with strict session settings:
    preflight   version 5, an empty `tags`, no foreign keys, and the character set stops; writes nothing
    step 1      one ALTER per CCDB table: engine, row format, charset, new columns (sha256 and size still NULL),
                new indexes, `tags` in its new shape; then the new tables and ALTER DATABASE
    step 2      backfill: sha256 and size of every unhashed set, in keyset batches of 500, one commit per batch
    step 3      sha256 and size NOT NULL
    step 4      the unique index (constantTypeId, sha256), or the interim index while a table holds duplicates
    step 5      schemaVersions = 6
Every ALTER names its algorithm and lock, and every ALTER and UPDATE runs under
lock_wait_timeout with retries; the last failed wait names the sessions holding the lock.

SQLite: the same objects in one transaction, with `constantSets` and `tags` rebuilt, since SQLite can
neither add a NOT NULL column without a default nor change a column type.

PHASE0 item 5 adds the dry run, the privilege, open-transaction and resource checks, and the SQLite
copy-and-replace; this module runs the upgrade in place.
"""
import logging
import os
import re
import sqlite3

from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from ccdb.model import vault_digest
from ccdb.sql import mysql_schema, sqlite_schema

log = logging.getLogger("ccdb.sql.update_v6")

SOURCE_VERSION = 5
TARGET_VERSION = 6

BACKFILL_BATCH = 500

# A remaining NULL must fail the NOT NULL step instead of becoming '' or 0, and a zero-date
# default elsewhere in a table must not fail every ALTER on MySQL 8, whose default mode adds NO_ZERO_DATE
UPGRADE_SQL_MODE = "STRICT_ALL_TABLES,NO_ENGINE_SUBSTITUTION"
LOCK_WAIT_TIMEOUT = 10       # seconds an ALTER waits for a metadata lock
LOCK_RETRIES = 3             # retries of a statement that hit a lock wait timeout (MySQL error 1205)
ER_LOCK_WAIT_TIMEOUT = 1205

UTF8 = "CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci"
TABLE_CHARSET = "DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_general_ci"
DEFAULT_COLLATION = "utf8mb4_general_ci"
BINARY_COLLATION = "utf8mb4_bin"

# The tables of a CCDB database: the only ones the upgrade touches. Others are left as they are.
CCDB_TABLES = ["schemaVersions", "users", "directories", "typeTables", "columns", "variations", "runRanges",
               "eventRanges", "constantSets", "assignments", "logs", "tags", "assignmentsMaterializedView",
               "variationsToTags", "variations_has_tags", "timeRanges", "properties"]

DEPRECATABLE_TABLES = ["directories", "typeTables", "variations"]

# Columns the upgrade adds where a table lacks them: (table, column, MySQL definition, SQLite definition).
# The definitions equal those of the fresh schema in mysql_schema.py and sqlite_schema.py, so an upgraded database
# compares equal to a fresh one. constantSets.sha256 and .size and the columns of `tags` are handled on their own.
DEPRECATION_COLUMNS = [
    # schema 5 columns that SQLite files upgraded from v4 by 2.4's update_v5 lack
    ("isDeprecated", "TINYINT(1) NOT NULL DEFAULT 0", "TINYINT(1) NOT NULL DEFAULT 0"),
    ("deprecatedByUserId", "INT NULL DEFAULT NULL", "INT(11) NULL DEFAULT NULL"),
    ("isLocked", "TINYINT(1) NOT NULL DEFAULT 0", "TINYINT(1) NOT NULL DEFAULT 0"),
    ("lockedByUserId", "INT NULL DEFAULT NULL", "INT(11) NULL DEFAULT NULL"),
    # schema 6 deprecation (D28)
    ("deprecatedTime", "DATETIME NULL DEFAULT NULL", "DATETIME NULL"),
    ("deprecationComment", f"TEXT {UTF8} NULL", "TEXT NULL"),
]
NEW_COLUMNS = [(table, column, mysql_definition, sqlite_definition)
               for table in DEPRECATABLE_TABLES
               for column, mysql_definition, sqlite_definition in DEPRECATION_COLUMNS]
NEW_COLUMNS += [
    ("assignments", "timeRangeId", "INT NULL DEFAULT NULL", "INTEGER NULL"),
    ("columns", "units", f"VARCHAR(64) {UTF8} NULL DEFAULT NULL", "VARCHAR(64) NULL"),
]

# MySQL: new schema 6 indexes outside constantSets, which step 4 handles
NEW_INDEXES = [
    ("assignments", "fk_assignments_timeRanges1_idx", "INDEX `fk_assignments_timeRanges1_idx` (`timeRangeId`)"),
    ("tags", "uq_tags_name", "UNIQUE INDEX `uq_tags_name` (`name`)"),
    ("tags", "fk_tags_variations1_idx", "INDEX `fk_tags_variations1_idx` (`variationId`)"),
]

# MySQL: `tags` in its schema 6 shape, altered in place; schema 5 has only id and name
TAGS_NAME = f"VARCHAR(100) {UTF8} NOT NULL"
TAGS_COLUMNS = [
    ("variationId", "INT NOT NULL"),
    ("snapshotTime", "DATETIME NOT NULL"),
    ("comment", f"TEXT {UTF8} NULL"),
    ("authorId", "INT NOT NULL DEFAULT 1"),
    ("created", "DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP"),
]

# MySQL: added NULL in step 1, made NOT NULL in step 3 once the backfill hashed every set
SHA256_TYPE = "CHAR(64) CHARACTER SET ascii COLLATE ascii_bin"
SIZE_TYPE = "INT UNSIGNED"

UNIQUE_INDEX = "uq_constantSets_table_sha256"
INTERIM_INDEX = "ix_constantSets_table_sha256"
DUPLICATES_ADVICE = ("Some CCDB tables hold constant sets with equal data, so constantSets has the interim index "
                     f"{INTERIM_INDEX}. Run 'ccdb db dedup --dedup-i-am-sure' to merge them and create the unique index "
                     f"{UNIQUE_INDEX}; until then two writers can store the same data twice")

# Character sets whose every stored value maps into utf8mb4; any other source charset can hold bytes
# that do not survive the conversion, so its values are checked row by row
LOSSLESS_CHARSETS = {"utf8mb4", "utf8mb3", "utf8", "latin1"}
# Character sets whose values keep their byte length in utf8mb4, so a TEXT value cannot overflow
SAME_LENGTH_CHARSETS = {"utf8mb4", "utf8mb3", "utf8", "ascii"}
TEXT_BYTE_LIMITS = {"tinytext": 255, "text": 65535, "mediumtext": 16777215}    # LONGTEXT cannot overflow
BINARY_TYPES = {"binary", "varbinary", "tinyblob", "blob", "mediumblob", "longblob"}

# Names that must stay distinct after the conversion, and the column that groups them
# (directories under one parent, tables of one directory, all variations, all users)
NAME_SCOPES = [("directories", "parentId"), ("typeTables", "directoryId"), ("variations", None), ("users", None)]

ROW_IDS_SHOWN = 10


class UpgradeRefusedError(Exception):
    """The preflight found a reason not to upgrade. Nothing was changed; the message names the reason."""


def upgrade_v6(engine):
    """Upgrades the CCDB database behind the engine from schema 5 to 6.

    :raises UpgradeRefusedError: the database is not one this upgrade takes; nothing was changed
    """
    if engine.dialect.name == "sqlite":
        SqliteUpgrade(engine).run()
    else:
        MySqlUpgrade(engine).run()


def describe_rows(count, ids):
    """'3 rows (ids 4, 9, 12)' for refusal messages: the count with up to ROW_IDS_SHOWN row ids"""
    words = f"{count} row" + ("" if count == 1 else "s")
    if ids:
        more = ", ..." if count > len(ids) else ""
        words += (" (id " if len(ids) == 1 else " (ids ") + ", ".join(str(row_id) for row_id in ids) + more + ")"
    return words


# ----------------------------------------------------------------------------------------------------------------
#  MySQL and MariaDB
# ----------------------------------------------------------------------------------------------------------------

class TableAlter:
    """What one ALTER TABLE changes, collected before the statement is written"""

    def __init__(self, table):
        self.table = table
        self.options = []        # ENGINE, ROW_FORMAT, DEFAULT CHARSET
        self.modify = {}         # column -> full definition
        self.add_columns = []    # (column, definition)
        self.add_indexes = []    # index definitions
        self.needs_copy = False  # an engine, charset or crossing type change: ALGORITHM=COPY

    def is_empty(self):
        return not (self.options or self.modify or self.add_columns or self.add_indexes)

    def statement(self, lock_clause):
        clauses = (self.options
                   + [f"MODIFY `{column}` {definition}" for column, definition in self.modify.items()]
                   + [f"ADD COLUMN `{column}` {definition}" for column, definition in self.add_columns]
                   + [f"ADD {definition}" for definition in self.add_indexes])
        return f"ALTER TABLE `{self.table}` " + ", ".join(clauses + [lock_clause])


class MySqlUpgrade:
    """The upgrade on MySQL or MariaDB"""

    def __init__(self, engine):
        self.engine = engine
        self.conn = None
        self.is_mariadb = False           # read_server sets these two from the server version
        self.instant_add_column = True

    def run(self):
        with self.engine.connect() as conn:
            self.conn = conn
            self.read_server()
            self.preflight()
            self.set_session()
            deferred = self.step1_ddl()
            self.step2_backfill()
            self.step3_not_null(deferred)
            self.step4_index()
            self.step5_version()

    # ------------------------------------------------------------------ database access

    def query(self, sql, **params):
        rows = [tuple(row) for row in self.conn.execute(text(sql), params)]
        self.conn.commit()    # end the read transaction at once: it would hold metadata locks the ALTERs wait for
        return rows

    def execute_ddl(self, sql):
        """Logs and runs one DDL statement and commits, with the lock wait retries of execute_with_retries"""
        log.info(sql)
        # a DDL statement has no parameters, but a column comment or default may contain a colon
        self.execute_with_retries(text(sql.replace(":", "\\:")), sql)

    def execute_with_retries(self, statement, description, params=None):
        """Runs one statement and commits. A lock wait timeout (1205: a metadata lock for an ALTER, a row lock for an
        UPDATE) is retried LOCK_RETRIES times after a rollback; the fourth wait fails, naming the blocking sessions."""
        for attempt in range(LOCK_RETRIES + 1):
            try:
                self.conn.execute(statement, params or {})
                self.conn.commit()
                return
            except OperationalError as error:
                self.conn.rollback()
                if error.orig is None or error.orig.args[0] != ER_LOCK_WAIT_TIMEOUT:
                    raise
                if attempt == LOCK_RETRIES:
                    raise RuntimeError(f"Waited {LOCK_RETRIES + 1} times {LOCK_WAIT_TIMEOUT} s for a lock and gave up. "
                                       f"{self.describe_blocking_sessions()} The statement was: {description}") from error
                log.warning(f"Lock wait timeout, retry {attempt + 1} of {LOCK_RETRIES}")

    def describe_blocking_sessions(self):
        """The other sessions on this database, those with an open InnoDB transaction first: one of them holds the
        lock a statement waits for. A MyISAM reader holds its metadata lock without an InnoDB transaction, so the
        idle sessions are listed too. Other sessions' rows need the PROCESS privilege; without it the text says
        where to look instead."""
        fallback = "Another session holds a transaction open on this database; SHOW FULL PROCESSLIST names it."
        try:
            rows = self.query("SELECT p.ID, p.USER, p.HOST, p.COMMAND, p.TIME, t.trx_started "
                              "FROM information_schema.PROCESSLIST p "
                              "LEFT JOIN information_schema.INNODB_TRX t ON t.trx_mysql_thread_id = p.ID "
                              "WHERE p.DB = DATABASE() AND p.ID <> CONNECTION_ID() "
                              "ORDER BY t.trx_started IS NULL, t.trx_started, p.ID")
        except Exception as error:
            log.debug(f"Reading the other sessions failed: {error}")
            return fallback
        if not rows:
            return fallback
        sessions = []
        for session_id, user, host, command, seconds, trx_started in rows[:ROW_IDS_SHOWN]:
            transaction = f", InnoDB transaction open since {trx_started}" if trx_started else ""
            sessions.append(f"id {session_id} {user}@{host} ({command} for {seconds} s{transaction})")
        return (f"Other sessions on this database: {'; '.join(sessions)}. End the transaction of the one holding the "
                "lock, then run the upgrade again; it continues where it stopped.")

    def read_server(self):
        version = self.query("SELECT VERSION()")[0][0]
        self.is_mariadb = "mariadb" in version.lower()
        numbers = tuple(int(part) for part in re.match(r"(\d+)\.(\d+)\.(\d+)", version).groups())
        # MariaDB before 10.6.9 can corrupt a table after an instant ADD COLUMN (MDEV-18519), and there INPLACE alone
        # still adds a column instantly; only FORCE rebuilds
        self.instant_add_column = not (self.is_mariadb and numbers < (10, 6, 9))
        log.info(f"Server: {version}")

    def set_session(self):
        # MariaDB 10.5 knows only tx_isolation; MySQL 8 knows only transaction_isolation
        isolation = "@@session.tx_isolation" if self.is_mariadb else "@@session.transaction_isolation"
        settings = self.query(f"SELECT @@autocommit, {isolation}, @@session.sql_mode, @@lock_wait_timeout, @@time_zone, @@system_time_zone")[0]
        log.info("Session before the upgrade: autocommit={0}, isolation={1}, sql_mode='{2}', lock_wait_timeout={3}, "
                 "time_zone={4}, system_time_zone={5}".format(*settings))
        self.conn.execute(text("SET SESSION sql_mode = :mode"), {"mode": UPGRADE_SQL_MODE})
        self.conn.execute(text(f"SET SESSION lock_wait_timeout = {LOCK_WAIT_TIMEOUT}"))
        self.conn.commit()

    def tables(self):
        """{table: (engine, collation, row_format)} of the CCDB tables present"""
        rows = self.query("SELECT TABLE_NAME, ENGINE, TABLE_COLLATION, ROW_FORMAT FROM information_schema.TABLES "
                          "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_TYPE = 'BASE TABLE'")
        return {name: (engine, collation, row_format) for name, engine, collation, row_format in rows if name in CCDB_TABLES}

    def columns(self, table):
        """{column: (data_type, column_type, charset, collation, is_nullable)} in table order"""
        rows = self.query("SELECT COLUMN_NAME, DATA_TYPE, COLUMN_TYPE, CHARACTER_SET_NAME, COLLATION_NAME, IS_NULLABLE "
                          "FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t "
                          "ORDER BY ORDINAL_POSITION", t=table)
        return {name: (data_type.lower(), column_type.lower(), charset, collation, nullable == "YES")
                for name, data_type, column_type, charset, collation, nullable in rows}

    def indexes(self, table):
        rows = self.query("SELECT DISTINCT INDEX_NAME FROM information_schema.STATISTICS "
                          "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t", t=table)
        return {row[0] for row in rows}

    def column_definitions(self, table):
        """{column: definition} from SHOW CREATE TABLE: the column's own type, default and attributes, which a
        MODIFY must repeat in full"""
        create = self.query(f"SHOW CREATE TABLE `{table}`")[0][1]
        definitions = {}
        for line in create.splitlines()[1:]:
            match = re.match(r"^\s*`((?:[^`]|``)+)`\s+(.*?),?\s*$", line)
            if match:
                definitions[match.group(1).replace("``", "`")] = match.group(2)
        return definitions

    def unhashed_condition(self):
        # A sha256 that is not 64 lowercase hex characters counts as unhashed, since a 2.4 client on a
        # non-strict server stores ''. sha256 is ascii_bin, so REGEXP compares case-sensitively on both servers.
        return "(`sha256` IS NULL OR `size` IS NULL OR NOT (`sha256` REGEXP '^[0-9a-f]{64}$'))"

    # ------------------------------------------------------------------ preflight, writes nothing

    def preflight(self):
        tables = self.tables()
        self.check_version(tables)
        problems = self.tags_problems(tables) + self.foreign_key_problems() + self.charset_problems(tables)
        if problems:
            raise UpgradeRefusedError("The upgrade to schema 6 is refused, nothing was changed:\n  " + "\n  ".join(problems))

    def check_version(self, tables):
        if "schemaVersions" not in tables:
            raise UpgradeRefusedError("No schemaVersions table: this database has no CCDB schema to upgrade")
        versions = [row[0] for row in self.query("SELECT schemaVersion FROM schemaVersions")]
        check_version_rows(versions)

    def tags_problems(self, tables):
        if "tags" not in tables or "snapshotTime" in self.columns("tags"):
            return []
        rows = self.query("SELECT id, name FROM tags ORDER BY id")
        if not rows:
            return []
        listed = ", ".join(f"{tag_id} '{name}'" for tag_id, name in rows[:ROW_IDS_SHOWN])
        return [f"tags holds {len(rows)} rows ({listed}). Schema 5 tags have no variation or time; "
                "decide what they mean and empty the table before the upgrade"]

    def foreign_key_problems(self):
        rows = self.query("SELECT CONSTRAINT_NAME, TABLE_NAME, REFERENCED_TABLE_NAME FROM information_schema.REFERENTIAL_CONSTRAINTS "
                          "WHERE CONSTRAINT_SCHEMA = DATABASE() ORDER BY TABLE_NAME, CONSTRAINT_NAME")
        rows = [row for row in rows if row[1] in CCDB_TABLES or row[2] in CCDB_TABLES]
        if not rows:
            return []
        # CCDB declares none, and an engine or type change can fail on them halfway
        named = ", ".join(f"{name} ({table} -> {referenced})" for name, table, referenced in rows)
        return [f"foreign key constraints on CCDB tables: {named}. CCDB declares none; remove them before the upgrade"]

    def charset_problems(self, tables):
        """The character set stops: values that would not survive the conversion to utf8mb4 or no longer fit,
        names that would become equal, and vault or name columns declared binary"""
        problems = []
        for table in tables:
            columns = self.columns(table)
            has_id = "id" in columns
            for column, (data_type, _, charset, collation, _) in columns.items():
                if column in ("vault", "name") and (data_type in BINARY_TYPES or charset == "binary"):
                    problems.append(f"{table}.{column} is declared {data_type} (binary); CCDB reads it as text. "
                                    "Convert it to a text type first")
                    continue
                if collation is None or (table, column) == ("constantSets", "sha256"):
                    continue
                if charset not in LOSSLESS_CHARSETS:
                    problems += self.round_trip_problems(table, column, charset, has_id)
                if data_type in TEXT_BYTE_LIMITS and charset not in SAME_LENGTH_CHARSETS:
                    problems += self.overflow_problems(table, column, TEXT_BYTE_LIMITS[data_type], has_id)
        for table, scope in NAME_SCOPES:
            if table in tables:
                problems += self.equal_name_problems(table, scope)
        return problems

    def round_trip_problems(self, table, column, charset, has_id):
        # CONVERT never fails: it substitutes '?' with a warning. A value survives when converting it to utf8mb4
        # and back returns the same bytes.
        condition = (f"`{column}` IS NOT NULL AND CAST(CONVERT(CONVERT(`{column}` USING utf8mb4) USING {charset}) AS BINARY) "
                     f"<> CAST(`{column}` AS BINARY)")
        count, ids = self.matching_rows(table, condition, has_id)
        if not count:
            return []
        return [f"{table}.{column} ({charset}): characters that utf8mb4 cannot represent in {describe_rows(count, ids)}; "
                "the conversion would replace them with '?'"]

    def overflow_problems(self, table, column, limit, has_id):
        longest = self.query(f"SELECT MAX(LENGTH(CONVERT(`{column}` USING utf8mb4))) FROM `{table}`")[0][0]
        if longest is None or longest <= limit:
            return []
        count, ids = self.matching_rows(table, f"LENGTH(CONVERT(`{column}` USING utf8mb4)) > {limit}", has_id)
        return [f"{table}.{column}: values longer than the {limit} bytes of the column in utf8mb4 in "
                f"{describe_rows(count, ids)} (longest {longest} bytes)"]

    def matching_rows(self, table, condition, has_id):
        count = self.query(f"SELECT COUNT(*) FROM `{table}` WHERE {condition}")[0][0]
        ids = []
        if count and has_id:
            ids = [row[0] for row in self.query(f"SELECT id FROM `{table}` WHERE {condition} ORDER BY id LIMIT {ROW_IDS_SHOWN}")]
        return count, ids

    def equal_name_problems(self, table, scope):
        columns = self.columns(table)
        if "name" not in columns or columns["name"][3] is None:
            return []
        target = target_collation(columns["name"][3])
        same_scope = f"AND a.`{scope}` = b.`{scope}` " if scope else ""
        # pairs that differ today under the column's collation and compare equal under the target collation
        pairs = self.query(
            f"SELECT a.id, b.id FROM `{table}` a JOIN `{table}` b ON a.id < b.id {same_scope}"
            f"WHERE a.name <> b.name AND CONVERT(a.name USING utf8mb4) COLLATE {target} = CONVERT(b.name USING utf8mb4) COLLATE {target} "
            "ORDER BY a.id, b.id")
        if not pairs:
            return []
        ids = sorted({row_id for pair in pairs for row_id in pair})
        where = f" in one {'parent directory' if scope == 'parentId' else 'directory'}" if scope else ""
        return [f"{table}.name: names that differ today and would compare equal{where} under {target} in "
                f"{describe_rows(len(ids), ids[:ROW_IDS_SHOWN])}. Rename them first"]

    # ------------------------------------------------------------------ step 1: per-table DDL

    def step1_ddl(self):
        """One ALTER per CCDB table with everything it needs, then the new tables and the database default.
        Returns the constantSets changes left for the step 3 rebuild."""
        deferred = None
        for table, (engine, collation, row_format) in self.tables().items():
            columns = self.columns(table)
            alter = self.table_changes(table, engine, collation, row_format, columns)
            if table == "constantSets" and self.instant_add_column and engine == "InnoDB" and alter.add_columns:
                # MySQL and MariaDB 10.6.9+: the new columns now, instantly; charset and table options join the
                # step 3 COPY, so the table is rebuilt once instead of twice
                deferred = TableAlter(table)
                deferred.options, deferred.modify, deferred.needs_copy = alter.options, alter.modify, alter.needs_copy
                alter.options, alter.modify, alter.needs_copy = [], {}, False
            if not alter.is_empty():
                self.execute_ddl(alter.statement(self.lock_clause(alter)))

        # tags too: a schema 5 database without it must reach every schema 6 object, as on SQLite
        existing = self.tables()
        for table in ("tags", "timeRanges", "properties"):
            if table not in existing:
                self.execute_ddl(mysql_schema.mysql_tables[table]["create"].strip().rstrip(";"))
        charset, collation = self.query("SELECT DEFAULT_CHARACTER_SET_NAME, DEFAULT_COLLATION_NAME FROM information_schema.SCHEMATA "
                                        "WHERE SCHEMA_NAME = DATABASE()")[0]
        if (charset, collation) != ("utf8mb4", DEFAULT_COLLATION):
            self.execute_ddl(f"ALTER DATABASE CHARACTER SET utf8mb4 COLLATE {DEFAULT_COLLATION}")
        return deferred

    def table_changes(self, table, engine, collation, row_format, columns):
        alter = TableAlter(table)
        if engine != "InnoDB":
            alter.options.append("ENGINE = InnoDB")
            alter.needs_copy = True
        elif row_format in ("Compact", "Redundant"):
            # those formats cap an index key at 767 bytes, and utf8mb4 takes 4 bytes per character
            alter.options.append("ROW_FORMAT = DYNAMIC")
        if collation != DEFAULT_COLLATION:
            alter.options.append(TABLE_CHARSET)

        # Every character column whose collation differs from its target, by MODIFY with the column's own
        # definition. CONVERT TO CHARACTER SET is not used: it widens TEXT to MEDIUMTEXT and makes _bin case-insensitive.
        definitions = None
        for column, (_, _, _, column_collation, _) in columns.items():
            if column_collation is None:
                continue
            charset, target = ("ascii", "ascii_bin") if (table, column) == ("constantSets", "sha256") \
                else ("utf8mb4", target_collation(column_collation))
            if column_collation != target:
                definitions = definitions or self.column_definitions(table)
                alter.modify[column] = with_charset(definitions[column], charset, target)
                alter.needs_copy = True

        additions = [(column, definition) for t, column, definition, _ in NEW_COLUMNS if t == table]
        if table == "constantSets":
            additions += [("sha256", f"{SHA256_TYPE} NULL DEFAULT NULL"), ("size", f"{SIZE_TYPE} NULL DEFAULT NULL")]
        if table == "tags":
            additions += TAGS_COLUMNS
            if columns["name"][1] != "varchar(100)":
                # VARCHAR(45) to VARCHAR(100) in utf8mb4 crosses the 255-byte length-prefix boundary: a COPY
                alter.modify["name"] = TAGS_NAME
                alter.needs_copy = True
        alter.add_columns = [(column, definition) for column, definition in additions if column not in columns]

        existing_indexes = self.indexes(table)
        alter.add_indexes = [definition for t, name, definition in NEW_INDEXES if t == table and name not in existing_indexes]
        return alter

    def lock_clause(self, alter):
        """The algorithm and lock clause for this ALTER, so the server never falls back silently to a blocking algorithm"""
        if alter.needs_copy:
            return "ALGORITHM=COPY, LOCK=SHARED"
        if alter.add_columns:
            if not self.instant_add_column:
                return "FORCE, ALGORITHM=INPLACE, LOCK=NONE"
            if not (alter.options or alter.modify or alter.add_indexes):
                return "ALGORITHM=INSTANT"
        # a new index, a row format or table option, or NOT NULL; both servers reject INSTANT for these
        return "ALGORITHM=INPLACE, LOCK=NONE"

    # ------------------------------------------------------------------ step 2: backfill

    def step2_backfill(self):
        """Hashes every unhashed set in keyset batches: only unhashed rows are read, and the key never rescans.
        One commit per batch, so an interrupted backfill resumes where it stopped. A batch whose UPDATE hits a lock
        wait timeout is rolled back and written again: the same ids get the same hashes."""
        last_id, hashed = 0, 0
        while True:
            rows = self.conn.execute(text(f"SELECT id, vault FROM constantSets WHERE id > :last AND {self.unhashed_condition()} "
                                          "ORDER BY id LIMIT :batch"), {"last": last_id, "batch": BACKFILL_BATCH}).fetchall()
            if not rows:
                self.conn.commit()
                break
            # SQL text, never the ORM: an ORM update would also rewrite constantSets.modified
            updates = []
            for set_id, vault in rows:
                sha256, size = vault_digest(vault)
                updates.append({"sha256": sha256, "size": size, "id": set_id})
            self.conn.commit()    # end the read transaction, so a retry below rolls back only the UPDATE
            self.execute_with_retries(text("UPDATE constantSets SET sha256 = :sha256, size = :size WHERE id = :id"),
                                      f"the backfill UPDATE of constant sets {rows[0][0]} to {rows[-1][0]}", updates)
            hashed += len(rows)
            last_id = rows[-1][0]
        if hashed:
            log.info(f"Backfill: hashed {hashed} constant sets")

    # ------------------------------------------------------------------ step 3: NOT NULL

    def step3_not_null(self, deferred):
        alter = deferred or TableAlter("constantSets")
        columns = self.columns("constantSets")
        if columns["sha256"][4]:
            alter.modify["sha256"] = f"{SHA256_TYPE} NOT NULL"
        if columns["size"][4]:
            alter.modify["size"] = f"{SIZE_TYPE} NOT NULL"
        if alter.is_empty():
            return
        # a set that a 2.4 client wrote since step 2 is hashed by a second pass
        if self.query(f"SELECT COUNT(*) FROM constantSets WHERE {self.unhashed_condition()}")[0][0]:
            self.step2_backfill()
        self.execute_ddl(alter.statement(self.lock_clause(alter)))

    # ------------------------------------------------------------------ step 4: index

    def step4_index(self):
        indexes = self.indexes("constantSets")
        if UNIQUE_INDEX in indexes:
            return
        if INTERIM_INDEX not in indexes:
            if self.has_duplicates():
                self.execute_ddl(f"ALTER TABLE `constantSets` ADD INDEX `{INTERIM_INDEX}` (`constantTypeId`, `sha256`), "
                                 "ALGORITHM=INPLACE, LOCK=NONE")
            else:
                self.execute_ddl(f"ALTER TABLE `constantSets` ADD UNIQUE INDEX `{UNIQUE_INDEX}` (`constantTypeId`, `sha256`), "
                                 "ALGORITHM=INPLACE, LOCK=NONE")
                return
        log.warning(DUPLICATES_ADVICE)

    def has_duplicates(self):
        return bool(self.query("SELECT 1 FROM constantSets GROUP BY constantTypeId, sha256 HAVING COUNT(*) > 1 LIMIT 1"))

    # ------------------------------------------------------------------ step 5: version

    def step5_version(self):
        self.execute_with_retries(text("UPDATE schemaVersions SET schemaVersion = :v"), "the UPDATE of schemaVersions",
                                  {"v": TARGET_VERSION})
        log.info(f"Schema version is {TARGET_VERSION}")


def check_version_rows(versions):
    """Exactly one schemaVersions row, with value 5"""
    if len(versions) != 1:
        raise UpgradeRefusedError(f"The schemaVersions table holds {len(versions)} rows; exactly one, with version "
                                  f"{SOURCE_VERSION}, is expected")
    if versions[0] != SOURCE_VERSION:
        older_hint = (" Upgrade it to version 5 with CCDB 2.4 first ('ccdb db upgrade --upgrade-i-am-sure' of release 2.4)."
                      if versions[0] < SOURCE_VERSION else "")
        raise UpgradeRefusedError(f"The database schema version is {versions[0]}; 'ccdb db upgrade' takes schema version "
                                  f"{SOURCE_VERSION} to {TARGET_VERSION}.{older_hint}")


def target_collation(collation):
    """Case-sensitive collations (*_bin, *_cs, *_as_cs) become utf8mb4_bin, any other utf8mb4_general_ci"""
    return BINARY_COLLATION if collation.endswith("_bin") or collation.endswith("_cs") else DEFAULT_COLLATION


# a column type as SHOW CREATE TABLE writes it: name, an optional argument list (enum values may hold parentheses
# inside quotes) and the unsigned and zerofill attributes
_COLUMN_TYPE = re.compile(r"^\w+(?:\((?:'(?:[^']|'')*'|[^)'])*\))?(?:\s+(?:unsigned|zerofill))*", re.IGNORECASE)
_CHARSET_CLAUSES = re.compile(r"^(?:\s+(?:CHARACTER SET|COLLATE)\s+\w+)*", re.IGNORECASE)


def with_charset(definition, charset, collation):
    """A column definition from SHOW CREATE TABLE with its charset and collation replaced by the given ones"""
    type_match = _COLUMN_TYPE.match(definition)
    column_type, rest = type_match.group(0), definition[type_match.end():]
    rest = rest[_CHARSET_CLAUSES.match(rest).end():]
    return f"{column_type} CHARACTER SET {charset} COLLATE {collation}{rest}"


# ----------------------------------------------------------------------------------------------------------------
#  SQLite
# ----------------------------------------------------------------------------------------------------------------

class SqliteUpgrade:
    """The upgrade of an SQLite file, in place and in one transaction: an interruption changes nothing"""

    def __init__(self, engine):
        self.path = engine.url.database
        self.conn = None

    def run(self):
        if not self.path or self.path == ":memory:" or not os.path.isfile(self.path):
            raise UpgradeRefusedError(f"No SQLite file to upgrade at '{self.path}'")
        # mode=rw never creates a file; isolation_level=None leaves BEGIN and COMMIT to this code, since the
        # sqlite3 module would otherwise commit before every DDL statement
        self.conn = sqlite3.connect(f"file:{self.path}?mode=rw", uri=True, isolation_level=None)
        try:
            self.preflight()
            self.conn.execute("BEGIN IMMEDIATE")
            try:
                self.add_columns_and_tables()
                self.rebuild_constant_sets()
                self.create_index()
                self.execute("UPDATE schemaVersions SET schemaVersion = ?", (TARGET_VERSION,))
                self.conn.execute("COMMIT")
            except BaseException:
                self.conn.execute("ROLLBACK")
                raise
        finally:
            self.conn.close()
        log.info(f"Schema version is {TARGET_VERSION}")

    def execute(self, sql, params=()):
        log.info(sql)
        return self.conn.execute(sql, params)

    def execute_script(self, script):
        """The statements of a schema snippet of sqlite_schema, one by one (executescript would commit)"""
        for statement in sqlite_schema._iter_statements(script):
            self.execute(statement)

    def tables(self):
        return {row[0] for row in self.conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}

    def columns(self, table):
        """{column: notnull} in table order"""
        return {row[1]: bool(row[3]) for row in self.conn.execute(f'PRAGMA table_info("{table}")')}

    def preflight(self):
        tables = self.tables()
        if "schemaVersions" not in tables:
            raise UpgradeRefusedError("No schemaVersions table: this file has no CCDB schema to upgrade")
        check_version_rows([row[0] for row in self.conn.execute("SELECT schemaVersion FROM schemaVersions")])
        if "tags" in tables and "snapshotTime" not in self.columns("tags"):
            count = self.conn.execute('SELECT COUNT(*) FROM "tags"').fetchone()[0]
            if count:
                raise UpgradeRefusedError(f"The upgrade to schema 6 is refused, nothing was changed: tags holds {count} rows. "
                                          "Schema 5 tags have no variation or time; decide what they mean and empty "
                                          "the table before the upgrade")

    def add_columns_and_tables(self):
        for table, column, _, definition in NEW_COLUMNS:
            if column not in self.columns(table):
                self.execute(f'ALTER TABLE "{table}" ADD COLUMN "{column}" {definition}')
        self.execute_script(sqlite_schema.assignments_time_range_index)

        # tags is empty (preflight), and SQLite cannot change a column type: the table is created anew
        if "tags" not in self.tables() or "snapshotTime" not in self.columns("tags"):
            self.execute('DROP TABLE IF EXISTS "tags"')
            self.execute_script(sqlite_schema.tags_create)
            self.execute_script(sqlite_schema.tags_indexes)
        self.execute_script(sqlite_schema.time_ranges_create)
        self.execute_script(sqlite_schema.properties_create)
        self.execute_script(sqlite_schema.properties_index)

    def rebuild_constant_sets(self):
        """constantSets with sha256 and size NOT NULL: a new table from the old one's own CREATE statement plus the two
        columns, the rows copied in batches with vault_digest, then the old table dropped and its indexes recreated"""
        if "sha256" in self.columns("constantSets"):
            return
        old_create = self.conn.execute("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'constantSets'").fetchone()[0]
        old_indexes = [row[0] for row in self.conn.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'index' AND tbl_name = 'constantSets' AND sql IS NOT NULL")]
        old_columns = list(self.columns("constantSets"))

        new_table = "constantSets_v6"
        self.execute(f'DROP TABLE IF EXISTS "{new_table}"')
        self.execute(create_with_columns(old_create, new_table, ['"sha256" CHAR(64) NOT NULL', '"size" INTEGER NOT NULL']))

        quoted = ", ".join(f'"{column}"' for column in old_columns)
        select = f'SELECT {quoted} FROM "constantSets" WHERE "id" > ? ORDER BY "id" LIMIT {BACKFILL_BATCH}'
        insert = (f'INSERT INTO "{new_table}" ({quoted}, "sha256", "size") '
                  f'VALUES ({", ".join("?" for _ in old_columns)}, ?, ?)')
        vault_index, id_index = old_columns.index("vault"), old_columns.index("id")
        log.info(f"{select}; {insert}")
        last_id, copied = -1, 0
        while True:
            rows = self.conn.execute(select, (last_id,)).fetchall()
            if not rows:
                break
            self.conn.executemany(insert, [row + vault_digest(row[vault_index]) for row in rows])
            copied += len(rows)
            last_id = rows[-1][id_index]
        log.info(f"Copied and hashed {copied} constant sets")

        self.execute('DROP TABLE "constantSets"')
        self.execute(f'ALTER TABLE "{new_table}" RENAME TO "constantSets"')
        for index_sql in old_indexes:
            self.execute(index_sql)

    def create_index(self):
        indexes = {row[1] for row in self.conn.execute('PRAGMA index_list("constantSets")')}
        if UNIQUE_INDEX in indexes:
            return
        if INTERIM_INDEX not in indexes:
            duplicates = self.conn.execute('SELECT 1 FROM "constantSets" GROUP BY "constantTypeId", "sha256" '
                                           'HAVING COUNT(*) > 1 LIMIT 1').fetchone()
            if not duplicates:
                self.execute_script(sqlite_schema.constant_sets_unique_index)
                return
            self.execute_script(sqlite_schema.constant_sets_interim_index)
        log.warning(DUPLICATES_ADVICE)


def create_with_columns(create_sql, new_name, column_definitions):
    """A CREATE TABLE statement from sqlite_master, renamed to new_name, with column_definitions added after the last
    column definition, before the table constraints (PRIMARY KEY (...), UNIQUE (...)) if there are any.

    The rest of the statement stays as it was, so converted files keep their own key and constraint clauses.
    """
    open_at, close_at = create_sql.index("("), create_sql.rindex(")")
    head = re.sub(r'^\s*CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?("[^"]+"|`[^`]+`|\[[^\]]+\]|\S+)\s*',
                  f'CREATE TABLE "{new_name}" ', create_sql[:open_at], flags=re.IGNORECASE)
    body = create_sql[open_at + 1:close_at]

    # split the body at its top-level commas, outside parentheses and quotes
    items, depth, quote, start = [], 0, None, 0
    for position, char in enumerate(body):
        if quote:
            if char == quote:
                quote = None
        elif char in "'\"`[":
            quote = "]" if char == "[" else char
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        elif char == "," and depth == 0:
            items.append(body[start:position])
            start = position + 1
    items.append(body[start:])

    constraint = re.compile(r"\s*(CONSTRAINT|PRIMARY\s+KEY|UNIQUE|CHECK|FOREIGN\s+KEY)\b", re.IGNORECASE)
    first_constraint = next((i for i, item in enumerate(items) if constraint.match(item)), len(items))
    items[first_constraint:first_constraint] = ["\n  " + definition for definition in column_definitions]
    return head + "(" + ",".join(items) + create_sql[close_at:]
