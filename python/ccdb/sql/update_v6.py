"""Schema 5 to 6 upgrade, run by `ccdb db upgrade --upgrade-i-am-sure`, and its dry run `ccdb db upgrade --dry-run`.

The operator's guide is docs/deployment/upgrade-2.5.md. Every step checks, then acts: an object that
exists already is left alone, so a rerun after an interruption continues where the last run stopped, and a run on
a database that has every schema 6 object changes nothing. The version is written last.

MySQL and MariaDB, on one connection with strict session settings:
    preflight   version 5; the privileges the DDL needs; no open transaction on the database; an empty `tags`;
                no foreign keys; the character set stops; the resources printed. Writes nothing
    step 1      one ALTER per CCDB table: engine, row format, charset, new columns (sha256 and size still NULL),
                new indexes, `tags` in its new shape; then the new tables and ALTER DATABASE
    step 2      backfill: sha256 and size of every unhashed set, in keyset batches of 500, one commit per batch
    step 3      sha256 and size NOT NULL
    step 4      the unique index (constantTypeId, sha256), or the interim index while a table holds duplicates
    step 5      schemaVersions = 6
Every ALTER names its algorithm and lock, and every ALTER and UPDATE runs under
lock_wait_timeout with retries; the last failed wait names the sessions holding the lock.

SQLite: the same objects in one transaction, with `constantSets` and `tags` rebuilt, since SQLite can
neither add a NOT NULL column without a default nor change a column type. The upgrade works on a copy,
<file>.v6, and replaces the file with it atomically, keeping the original as <file>.v5; --in-place skips
the copy for files no job reads.

The MySQL connection helpers and the SQLite copy-and-replace are shared with `db rollback-v6`
(ccdb.sql.rollback_v6) and `db dedup` (ccdb.sql.shared_sets).
"""
import logging
import os
import re
import shutil
import sqlite3

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, OperationalError

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
LONG_QUERY_SECONDS = 60      # a query running this long on the database blocks the upgrade like an open transaction

# What the DDL of the upgrade needs; the rollback also needs DROP
UPGRADE_PRIVILEGES = ["ALTER", "CREATE", "INDEX", "INSERT", "UPDATE", "DELETE"]

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
    # schema 6: when and why a directory, table or variation was deprecated
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

# Rates measured on a trial copy of hallddb (MariaDB 10.5, local NVMe), for the dry run's time estimate:
# a COPY rebuild of constantSets moved 4.9 GB in 29 s, and the backfill hashed 821 431 sets in 97 s
TRIAL_REBUILD_BYTES_PER_SECOND = 170e6
TRIAL_BACKFILL_SETS_PER_SECOND = 8500
DUPLICATES_SAMPLE_TABLES = 20      # --duplicates sample reads the vaults of the tables with most sets


class UpgradeRefusedError(Exception):
    """The preflight found a reason not to upgrade. Nothing was changed; the message names the reason."""


def upgrade_v6(engine, dry_run=False, duplicates="none", skip_privilege_check=False, transaction_check=True,
               in_place=False):
    """Upgrades the CCDB database behind the engine from schema 5 to 6, or with dry_run prints what the upgrade would
    do and writes nothing.

    :param duplicates: dry run only: "none" reads no vault, "sample" counts duplicate sets in the tables with most sets,
                       "all" in every table
    :param skip_privilege_check: MySQL: proceed although the privilege views do not show a needed privilege
                                 (privileges granted through a role do not show there)
    :param transaction_check: MySQL: refuse while another session holds a transaction open on the database
    :param in_place: SQLite: change the file itself instead of a copy that replaces it
    :raises UpgradeRefusedError: the database is not one this upgrade takes; nothing was changed
    """
    if engine.dialect.name == "sqlite":
        upgrade = SqliteUpgrade(engine.url.database)
        if dry_run:
            upgrade.dry_run(duplicates)
        else:
            upgrade.run(in_place)
        return
    upgrade = MySqlUpgrade(engine, skip_privilege_check, transaction_check)
    if dry_run:
        upgrade.dry_run(duplicates)
    else:
        upgrade.run()


def describe_rows(count, ids):
    """'3 rows (ids 4, 9, 12)' for refusal messages: the count with up to ROW_IDS_SHOWN row ids"""
    words = f"{count} row" + ("" if count == 1 else "s")
    if ids:
        more = ", ..." if count > len(ids) else ""
        words += (" (id " if len(ids) == 1 else " (ids ") + ", ".join(str(row_id) for row_id in ids) + more + ")"
    return words


def unhashed_condition(dialect_name):
    """SQL condition on constantSets: the set has no valid hash. A sha256 that is not 64 lowercase hex characters
    counts as unhashed, since a 2.4 client on a non-strict server stores ''."""
    if dialect_name == "sqlite":
        # SQLite has no REGEXP; GLOB compares case-sensitively
        return "(\"sha256\" IS NULL OR \"size\" IS NULL OR length(\"sha256\") <> 64 OR \"sha256\" GLOB '*[^0-9a-f]*')"
    # sha256 is ascii_bin, so REGEXP compares case-sensitively on both servers
    return "(`sha256` IS NULL OR `size` IS NULL OR NOT (`sha256` REGEXP '^[0-9a-f]{64}$'))"


def check_version_rows(versions, accepted=(SOURCE_VERSION,), command="'ccdb db upgrade' takes schema version 5 to 6"):
    """Exactly one schemaVersions row, with an accepted value"""
    if len(versions) != 1:
        raise UpgradeRefusedError(f"The schemaVersions table holds {len(versions)} rows; exactly one, with version "
                                  f"{' or '.join(str(v) for v in accepted)}, is expected")
    if versions[0] not in accepted:
        # an older database reaches version 5 with CCDB 2.4's own upgrade first
        older_hint = (" Upgrade it to version 5 with CCDB 2.4 first ('ccdb db upgrade --upgrade-i-am-sure' of release 2.4)."
                      if versions[0] < SOURCE_VERSION and tuple(accepted) == (SOURCE_VERSION,) else "")
        raise UpgradeRefusedError(f"The database schema version is {versions[0]}; {command}.{older_hint}")


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


def format_bytes(count):
    for unit in ("bytes", "kB", "MB", "GB"):
        if count < 1000 or unit == "GB":
            return f"{count} {unit}" if unit == "bytes" else f"{count:.1f} {unit}"
        count /= 1000.0


# ----------------------------------------------------------------------------------------------------------------
#  MySQL and MariaDB: one connection with the checks every maintenance command shares
# ----------------------------------------------------------------------------------------------------------------

class MySqlMaintenance:
    """One connection to a CCDB database on MySQL or MariaDB for the `db` maintenance commands: the reads of the
    structure, the preflight checks of privileges and open transactions, and DDL with lock wait retries.

    Every read commits at once: an open read transaction holds metadata locks that the ALTERs would wait for.
    """

    def __init__(self, engine, skip_privilege_check=False, transaction_check=True):
        self.engine = engine
        self.skip_privilege_check = skip_privilege_check
        self.transaction_check = transaction_check
        self.conn = None
        self.server_version = ""
        self.is_mariadb = False           # read_server sets these two from the server version
        self.instant_add_column = True

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
            rows = self.other_sessions()
        except Exception as error:
            log.debug(f"Reading the other sessions failed: {error}")
            return fallback
        if not rows:
            return fallback
        sessions = [describe_session(row) for row in rows[:ROW_IDS_SHOWN]]
        return (f"Other sessions on this database: {'; '.join(sessions)}. End the transaction of the one holding the "
                "lock, then run the command again; it continues where it stopped.")

    def other_sessions(self):
        """(id, user, host, command, seconds, statement keyword, transaction start) of the other sessions on this
        database, those with an open InnoDB transaction first. Without PROCESS the server shows only this user's
        sessions. Only the first word of a running statement is read: its text may carry another client's data, which
        must not reach this command's messages and the logs they are pasted into."""
        return self.query("SELECT p.ID, p.USER, p.HOST, p.COMMAND, p.TIME, SUBSTRING_INDEX(TRIM(p.INFO), ' ', 1), t.trx_started "
                          "FROM information_schema.PROCESSLIST p "
                          "LEFT JOIN information_schema.INNODB_TRX t ON t.trx_mysql_thread_id = p.ID "
                          "WHERE p.DB = DATABASE() AND p.ID <> CONNECTION_ID() "
                          "ORDER BY t.trx_started IS NULL, t.trx_started, p.ID")

    def read_server(self):
        self.server_version = self.query("SELECT VERSION()")[0][0]
        self.is_mariadb = "mariadb" in self.server_version.lower()
        numbers = tuple(int(part) for part in re.match(r"(\d+)\.(\d+)\.(\d+)", self.server_version).groups())
        # MariaDB before 10.6.9 can corrupt a table after an instant ADD COLUMN (MDEV-18519), and there INPLACE alone
        # still adds a column instantly; only FORCE rebuilds
        self.instant_add_column = not (self.is_mariadb and numbers < (10, 6, 9))

    def session_settings(self):
        """autocommit, isolation level, sql_mode, lock_wait_timeout, time_zone, system_time_zone of this session"""
        # MariaDB 10.5 knows only tx_isolation; MySQL 8 knows only transaction_isolation
        isolation = "@@session.tx_isolation" if self.is_mariadb else "@@session.transaction_isolation"
        return self.query(f"SELECT @@autocommit, {isolation}, @@session.sql_mode, @@lock_wait_timeout, @@time_zone, "
                          "@@system_time_zone")[0]

    def set_session(self):
        settings = self.session_settings()
        log.info("Session before the change: autocommit={0}, isolation={1}, sql_mode='{2}', lock_wait_timeout={3}, "
                 "time_zone={4}, system_time_zone={5}".format(*settings))
        self.conn.execute(text("SET SESSION sql_mode = :mode"), {"mode": UPGRADE_SQL_MODE})
        self.conn.execute(text(f"SET SESSION lock_wait_timeout = {LOCK_WAIT_TIMEOUT}"))
        self.conn.commit()

    def tables(self):
        """{table: (engine, collation, row_format)} of the CCDB tables present"""
        return {name: (engine, collation, row_format)
                for name, engine, collation, row_format, _ in self.all_tables() if name in CCDB_TABLES}

    def all_tables(self):
        """(name, engine, collation, row_format, size in bytes) of every base table of the database"""
        rows = self.query("SELECT TABLE_NAME, ENGINE, TABLE_COLLATION, ROW_FORMAT, "
                          "COALESCE(DATA_LENGTH, 0) + COALESCE(INDEX_LENGTH, 0) FROM information_schema.TABLES "
                          "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_TYPE = 'BASE TABLE' ORDER BY TABLE_NAME")
        return [(name, engine, collation, row_format, int(size)) for name, engine, collation, row_format, size in rows]

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

    def schema_versions(self, tables):
        if "schemaVersions" not in tables:
            raise UpgradeRefusedError("No schemaVersions table: this database has no CCDB schema")
        return [row[0] for row in self.query("SELECT schemaVersion FROM schemaVersions")]

    # ------------------------------------------------------------------ preflight: privileges

    def granted_privileges(self):
        """The privileges of the current account on this database: the global ones and those of the schema grants
        whose pattern matches it. DATABASE() LIKE TABLE_SCHEMA follows the server's own grant patterns such as
        `ccdb\\_test%`; an exact match finds nothing for those."""
        user, _, host = self.query("SELECT CURRENT_USER()")[0][0].rpartition("@")
        grantee = f"'{user}'@'{host}'"
        global_privileges = {row[0] for row in self.query(
            "SELECT PRIVILEGE_TYPE FROM information_schema.USER_PRIVILEGES WHERE GRANTEE = :g", g=grantee)}
        schema_privileges = {row[0] for row in self.query(
            "SELECT PRIVILEGE_TYPE FROM information_schema.SCHEMA_PRIVILEGES "
            "WHERE GRANTEE = :g AND DATABASE() LIKE TABLE_SCHEMA", g=grantee)}
        return grantee, global_privileges, schema_privileges

    def active_role(self):
        """The active role, or None. Privileges granted through a role do not show in the privilege views."""
        try:
            role = self.query("SELECT CURRENT_ROLE()")[0][0]
        except DBAPIError:
            return None
        return None if role in (None, "", "NONE") else role

    def has_process_privilege(self):
        return "PROCESS" in self.granted_privileges()[1]

    def privilege_problems(self, required):
        """A refusal text for each missing privilege the command needs; none with --skip-privilege-check"""
        grantee, global_privileges, schema_privileges = self.granted_privileges()
        granted = global_privileges | schema_privileges
        missing = [privilege for privilege in required if privilege not in granted]
        if not missing:
            return []
        if self.skip_privilege_check:
            log.warning(f"The privilege views do not show {', '.join(missing)} for {grantee}; "
                        "proceeding, as --skip-privilege-check asks")
            return []
        text_ = (f"the account {grantee} lacks the privileges {', '.join(missing)} on this database, which the command "
                 f"needs (it has: {', '.join(sorted(granted)) or 'none'})")
        role = self.active_role()
        if role:
            text_ += (f". The active role {role} may grant them: privileges granted through a role do not show in the "
                      "privilege views. If it does, add --skip-privilege-check")
        return [text_]

    # ------------------------------------------------------------------ preflight: open transactions

    def transaction_problems(self):
        """A refusal text when another session holds a transaction open on this database or runs a long query.

        An open transaction holds a metadata lock that blocks every ALTER and queues every later reader behind it.
        Idle autocommit sessions, such as C++ jobs between reads, are listed and do not block. Other sessions'
        transactions are visible only with the PROCESS privilege. --no-transaction-check turns the refusal into a
        warning that lists what was found.
        """
        if not self.has_process_privilege():
            message = ("open transactions of other sessions cannot be seen without the PROCESS privilege. Stop every "
                       "other CCDB client of this database, then add --no-transaction-check to proceed without the check")
            if self.transaction_check:
                return [message]
            log.warning("No transaction check: " + message.split(". ")[0])
            return []
        blocking, idle = [], []
        for row in self.other_sessions():
            command, seconds, transaction_started = row[3], row[4], row[6]
            is_blocking = transaction_started is not None or (command == "Query" and (seconds or 0) >= LONG_QUERY_SECONDS)
            (blocking if is_blocking else idle).append(describe_session(row))
        for session in idle:
            log.info(f"Idle session on this database, which does not block: {session}")
        if not blocking:
            return []
        message = ("other sessions hold a transaction open on this database or run a query longer than "
                   f"{LONG_QUERY_SECONDS} s; every ALTER would wait for them: {'; '.join(blocking)}")
        if self.transaction_check:
            return [message + ". End them (stop the clients), or add --no-transaction-check"]
        log.warning("No transaction check: " + message)
        return []

    # ------------------------------------------------------------------ preflight: resources

    def report_resources(self, report=log.info):
        """Prints what the server cannot be asked over SQL to check: the space a rebuild of the largest table needs,
        the binary log the backfill writes, the replica status"""
        tables = [table for table in self.all_tables() if table[0] in CCDB_TABLES]
        if tables:
            name, _, _, _, size = max(tables, key=lambda table: table[4])
            report(f"Resources: a rebuild of the largest table, {name}, needs about {format_bytes(size)} of free disk "
                   "space (the server cannot report free space over SQL)")
        variables = dict(self.query("SHOW VARIABLES WHERE Variable_name IN ('log_bin', 'binlog_format', 'binlog_row_image')"))
        vault_bytes = self.vault_bytes_estimate()
        binlog = (f"; the backfill writes about {format_bytes(2 * vault_bytes)} of binary log under row-based logging"
                  if variables.get("log_bin", "OFF").upper() == "ON" else "")
        report(f"Resources: log_bin={variables.get('log_bin', 'unknown')}, binlog_format={variables.get('binlog_format', 'unknown')}, "
               f"binlog_row_image={variables.get('binlog_row_image', 'unknown')}{binlog}")
        report(f"Resources: replica status: {self.replica_status()}")

    def vault_bytes_estimate(self):
        """Bytes of vault text, estimated from constantSets' DATA_LENGTH, which reads no row"""
        rows = self.query("SELECT COALESCE(DATA_LENGTH, 0) FROM information_schema.TABLES "
                          "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'constantSets'")
        return int(rows[0][0]) if rows else 0

    def replica_status(self):
        for statement in ("SHOW REPLICA STATUS", "SHOW SLAVE STATUS"):
            try:
                rows = self.conn.execute(text(statement)).mappings().all()
                self.conn.commit()
            except DBAPIError:
                self.conn.rollback()
                continue
            if not rows:
                return "not a replica"
            row = rows[0]
            source = row.get("Source_Host") or row.get("Master_Host") or "?"
            return f"a replica of {source}"
        return "unknown (reading it needs the REPLICATION CLIENT or SLAVE MONITOR privilege)"


def describe_session(row):
    session_id, user, host, command, seconds, keyword, transaction_started = row
    transaction = f", InnoDB transaction open since {transaction_started}" if transaction_started else ""
    running = f", running a {keyword} statement" if keyword else ""
    return f"id {session_id} {user}@{host} ({command} for {seconds} s{transaction}{running})"


# ----------------------------------------------------------------------------------------------------------------
#  MySQL and MariaDB: the upgrade
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


class MySqlUpgrade(MySqlMaintenance):
    """The upgrade on MySQL or MariaDB"""

    def run(self):
        with self.engine.connect() as conn:
            self.conn = conn
            self.read_server()
            log.info(f"Server: {self.server_version}")
            self.preflight()
            self.set_session()
            self.step1_ddl()
            self.step2_backfill()
            self.step3_not_null()
            self.step4_index()
            self.step5_version()

    def unhashed_condition(self):
        return unhashed_condition("mysql")

    # ------------------------------------------------------------------ preflight, writes nothing

    def preflight(self):
        tables = self.tables()
        check_version_rows(self.schema_versions(tables))
        problems = self.privilege_problems(UPGRADE_PRIVILEGES) + self.transaction_problems()
        problems += self.tags_problems(tables) + self.foreign_key_problems(tables)
        stops, _ = self.charset_problems(tables, read_vaults=True)
        problems += stops
        if problems:
            raise UpgradeRefusedError("The upgrade to schema 6 is refused, nothing was changed:\n  " + "\n  ".join(problems))
        # --upgrade-i-am-sure is the confirmation of these, as of the backup
        self.report_resources()

    def tags_problems(self, tables):
        if "tags" not in tables or "snapshotTime" in self.columns("tags"):
            return []
        rows = self.query("SELECT id, name FROM tags ORDER BY id")
        if not rows:
            return []
        listed = ", ".join(f"{tag_id} '{name}'" for tag_id, name in rows[:ROW_IDS_SHOWN])
        return [f"tags holds {len(rows)} rows ({listed}). Schema 5 tags have no variation or time; "
                "decide what they mean and empty the table before the upgrade"]

    def foreign_key_problems(self, tables):
        rows = self.query("SELECT CONSTRAINT_NAME, TABLE_NAME, REFERENCED_TABLE_NAME FROM information_schema.REFERENTIAL_CONSTRAINTS "
                          "WHERE CONSTRAINT_SCHEMA = DATABASE() ORDER BY TABLE_NAME, CONSTRAINT_NAME")
        rows = [row for row in rows if row[1] in CCDB_TABLES or row[2] in CCDB_TABLES]
        if not rows:
            return []
        # CCDB declares none, and an engine or type change can fail on them halfway
        named = ", ".join(f"{name} ({table} -> {referenced})" for name, table, referenced in rows)
        return [f"foreign key constraints on CCDB tables: {named}. CCDB declares none; remove them before the upgrade"]

    def charset_problems(self, tables, read_vaults):
        """The character set stops: values that would not survive the conversion to utf8mb4 or no longer fit,
        names that would become equal, and vault or name columns declared binary.

        Returns (problems, pending): without read_vaults the checks that would read a vault are not run and are
        returned as pending, so a dry run reads no vault; the upgrade's preflight runs them.
        """
        problems, pending = [], []
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
                skip = not read_vaults and column == "vault"
                if charset not in LOSSLESS_CHARSETS:
                    if skip:
                        pending.append(f"{table}.{column} ({charset}): round-trip check pending; the upgrade's "
                                       "preflight reads every value")
                    else:
                        problems += self.round_trip_problems(table, column, charset, has_id)
                if data_type in TEXT_BYTE_LIMITS and charset not in SAME_LENGTH_CHARSETS:
                    if skip:
                        pending.append(f"{table}.{column} ({data_type}, {charset}): length check pending; the upgrade's "
                                       "preflight reads every value")
                    else:
                        problems += self.overflow_problems(table, column, TEXT_BYTE_LIMITS[data_type], has_id)
        for table, scope in NAME_SCOPES:
            if table in tables:
                problems += self.equal_name_problems(table, scope)
        return problems, pending

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

    def plan_step1(self):
        """The statements of step 1 in order, and the constantSets changes left for the step 3 rebuild: one ALTER per
        CCDB table with everything it needs, then the new tables and the database default"""
        statements, deferred = [], None
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
                statements.append(alter.statement(self.lock_clause(alter)))

        # tags too: a schema 5 database without it must reach every schema 6 object, as on SQLite
        existing = self.tables()
        for table in ("tags", "timeRanges", "properties"):
            if table not in existing:
                statements.append(mysql_schema.mysql_tables[table]["create"].strip().rstrip(";"))
        charset, collation = self.query("SELECT DEFAULT_CHARACTER_SET_NAME, DEFAULT_COLLATION_NAME FROM information_schema.SCHEMATA "
                                        "WHERE SCHEMA_NAME = DATABASE()")[0]
        if (charset, collation) != ("utf8mb4", DEFAULT_COLLATION):
            statements.append(f"ALTER DATABASE CHARACTER SET utf8mb4 COLLATE {DEFAULT_COLLATION}")
        return statements, deferred

    def step1_ddl(self):
        statements, self.deferred = self.plan_step1()
        for statement in statements:
            self.execute_ddl(statement)

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
            target = self.column_target(table, column, column_collation)
            charset = "ascii" if target == "ascii_bin" else "utf8mb4"
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

    @staticmethod
    def column_target(table, column, collation):
        """The collation a character column gets: sha256 ascii_bin, any other by target_collation"""
        return "ascii_bin" if (table, column) == ("constantSets", "sha256") else target_collation(collation)

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

    def plan_step3(self, deferred):
        """The ALTER of step 3, or None: sha256 and size NOT NULL, with the constantSets changes step 1 deferred"""
        alter = deferred or TableAlter("constantSets")
        columns = self.columns("constantSets")
        # before step 1 (a dry run) the columns do not exist yet: they will be added NULL, so step 3 changes them
        if "sha256" not in columns or columns["sha256"][4]:
            alter.modify["sha256"] = f"{SHA256_TYPE} NOT NULL"
        if "size" not in columns or columns["size"][4]:
            alter.modify["size"] = f"{SIZE_TYPE} NOT NULL"
        if alter.is_empty():
            return None
        return alter.statement(self.lock_clause(alter))

    def step3_not_null(self):
        statement = self.plan_step3(self.deferred)
        if statement is None:
            return
        # a set that a 2.4 client wrote since step 2 is hashed by a second pass
        if self.query(f"SELECT COUNT(*) FROM constantSets WHERE {self.unhashed_condition()}")[0][0]:
            self.step2_backfill()
        self.execute_ddl(statement)

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

    # ------------------------------------------------------------------ dry run

    def dry_run(self, duplicates):
        """Prints what the upgrade would do and what its preflight would find, writing nothing. With duplicates "none"
        no statement reads a vault, so it is safe on a production server; it needs only SELECT."""
        with self.engine.connect() as conn:
            self.conn = conn
            self.read_server()
            tables = self.tables()
            versions = self.schema_versions(tables)
            print("Dry run of 'ccdb db upgrade': nothing is written")
            self.print_server()
            check_version_rows(versions)

            print("\nPreflight:")
            refusals = self.privilege_problems(UPGRADE_PRIVILEGES)
            grantee, global_privileges, schema_privileges = self.granted_privileges()
            print(f"  privileges of {grantee} on this database: {', '.join(sorted(global_privileges | schema_privileges)) or 'none'}")
            self.print_transactions()
            refusals += self.tags_problems(tables) + self.foreign_key_problems(tables)
            # only "all" reads every vault; "sample" stays the bounded read of the tables with most sets
            stops, pending = self.charset_problems(tables, read_vaults=duplicates == "all")
            refusals += stops
            for line in refusals:
                print(f"  would refuse: {line}")
            for line in pending:
                print(f"  {line}")
            if not refusals:
                print("  nothing found that would refuse the upgrade")
            self.report_resources(report=lambda line: print("  " + line))

            print("\nTables:")
            rebuild_bytes = self.print_tables()

            statements, deferred = self.plan_step1()
            step3 = self.plan_step3(deferred)
            sets = self.query("SELECT COUNT(*) FROM constantSets")[0][0]
            columns = self.columns("constantSets")
            if "sha256" in columns:
                unhashed = self.query(f"SELECT COUNT(*) FROM constantSets WHERE {self.unhashed_condition()}")[0][0]
            else:
                unhashed = sets
            print("\nStatements, in order:")
            for statement in statements:
                print(f"  step 1: {statement};")
            print(f"  step 2: hash {unhashed} of {sets} constant sets in batches of {BACKFILL_BATCH} "
                  f"(about {format_bytes(self.vault_bytes_estimate())} of vault text, estimated from DATA_LENGTH)")
            if step3:
                print(f"  step 3: {step3};")
            print(f"  step 4: ALTER TABLE `constantSets` ADD UNIQUE INDEX `{UNIQUE_INDEX}` (`constantTypeId`, `sha256`), "
                  f"ALGORITHM=INPLACE, LOCK=NONE; or, while a table holds duplicate sets, the same with the interim "
                  f"non-unique index `{INTERIM_INDEX}`")
            print(f"  step 5: UPDATE schemaVersions SET schemaVersion = {TARGET_VERSION};")

            self.print_duplicates(duplicates)

            seconds = rebuild_bytes / TRIAL_REBUILD_BYTES_PER_SECOND + unhashed / TRIAL_BACKFILL_SETS_PER_SECOND
            print(f"\nEstimated time: about {seconds:.0f} s at the rates of the trial copy of hallddb on local NVMe "
                  "(slower storage takes longer)")

    def print_server(self):
        print(f"Server: {self.server_version}")
        names = ["@@alter_algorithm", "@@innodb_instant_alter_column_allowed"] if self.is_mariadb else []
        for name in names:
            try:
                print(f"  {name.lstrip('@')}: {self.query(f'SELECT {name}')[0][0]}")
            except DBAPIError:
                self.conn.rollback()
        settings = self.session_settings()
        print("  session: autocommit={0}, isolation={1}, sql_mode='{2}', lock_wait_timeout={3}, time_zone={4}, "
              "system_time_zone={5}".format(*settings))
        print(f"  the upgrade sets sql_mode='{UPGRADE_SQL_MODE}' and lock_wait_timeout={LOCK_WAIT_TIMEOUT} for its session")

    def print_transactions(self):
        """The open-transaction check as the dry run shows it: what is visible is listed, nothing refuses here"""
        if not self.has_process_privilege():
            print("  open transactions: cannot be seen without the PROCESS privilege; the upgrade then needs "
                  "--no-transaction-check")
            return
        sessions = self.other_sessions()
        if not sessions:
            print("  open transactions: none, and no other session on this database")
        for row in sessions:
            blocking = row[6] is not None or (row[3] == "Query" and (row[4] or 0) >= LONG_QUERY_SECONDS)
            print(f"  {'blocking' if blocking else 'idle'} session: {describe_session(row)}")

    def print_tables(self):
        """Prints every table with its size and what changes; returns the bytes the upgrade rebuilds"""
        rebuild_bytes = 0
        myisam = []
        for name, engine, collation, row_format, size in self.all_tables():
            if name not in CCDB_TABLES:
                print(f"  {name}: {size} bytes, engine {engine}; not a CCDB table, left untouched")
                continue
            changes = []
            if engine != "InnoDB":
                changes.append(f"engine {engine} to InnoDB")
                myisam.append(f"{name} ({size} bytes)")
            elif row_format in ("Compact", "Redundant"):
                changes.append(f"row format {row_format} to Dynamic")
            if collation != DEFAULT_COLLATION:
                changes.append(f"table collation {collation} to {DEFAULT_COLLATION}")
            columns = self.columns(name)
            converted = [column for column, info in columns.items()
                         if info[3] is not None and info[3] != self.column_target(name, column, info[3])]
            if converted:
                changes.append(f"column collation of {', '.join(converted)}")
            if changes:
                rebuild_bytes += size
            print(f"  {name}: {size} bytes, engine {engine}, row format {row_format}, collation {collation}; "
                  f"{'; '.join(changes) if changes else 'charset and engine stay'}")
        if myisam:
            print(f"  MyISAM tables, converted to InnoDB by a copy: {', '.join(myisam)}")
        constant_sets = [size for name, _, _, _, size in self.all_tables() if name == "constantSets"]
        return rebuild_bytes + sum(constant_sets)    # step 3 rebuilds constantSets once more

    def print_duplicates(self, duplicates):
        """Duplicate groups by the server's SHA2 of the utf8mb4 text: none reads no vault, sample reads the vaults of
        the tables with most sets, all reads every vault"""
        if duplicates == "none":
            print("\nDuplicate sets: not counted (--duplicates none reads no vault); 'sample' or 'all' counts them")
            return
        where = ""
        if duplicates == "sample":
            table_ids = [row[0] for row in self.query(
                f"SELECT constantTypeId FROM constantSets GROUP BY constantTypeId ORDER BY COUNT(*) DESC "
                f"LIMIT {DUPLICATES_SAMPLE_TABLES}")]
            if not table_ids:
                print("\nDuplicate sets: no constant sets")
                return
            where = f"WHERE constantTypeId IN ({', '.join(str(table_id) for table_id in table_ids)}) "
        rows = self.query("SELECT constantTypeId, COUNT(*), SUM(LENGTH(vault)) FROM constantSets "
                          f"{where}GROUP BY constantTypeId, SHA2(CONVERT(vault USING utf8mb4), 256) HAVING COUNT(*) > 1")
        tables = {row[0] for row in rows}
        redundant = sum(row[1] - 1 for row in rows)
        saved = sum(int(row[2]) * (row[1] - 1) // row[1] for row in rows)
        scope = f"in the {DUPLICATES_SAMPLE_TABLES} tables with most sets" if duplicates == "sample" else "in all tables"
        print(f"\nDuplicate sets {scope}: {len(rows)} groups in {len(tables)} tables, {redundant} redundant sets, "
              f"about {format_bytes(saved)}; the upgrade would create the "
              f"{'interim index' if rows else 'unique index'}" + (" (other tables were not read)" if duplicates == "sample" else ""))


# ----------------------------------------------------------------------------------------------------------------
#  SQLite
# ----------------------------------------------------------------------------------------------------------------

def sqlite_file_or_refuse(path):
    if not path or path == ":memory:" or not os.path.isfile(path):
        raise UpgradeRefusedError(f"No SQLite file at '{path}'")


def sqlite_read_only(path):
    """A connection that never writes and never creates a file: preflight checks change nothing"""
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True)


def sqlite_tables(conn):
    return {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'")}


def sqlite_columns(conn, table):
    """{column: notnull} in table order"""
    return {row[1]: bool(row[3]) for row in conn.execute(f'PRAGMA table_info("{table}")')}


def sqlite_row_counts(conn):
    return {table: conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0] for table in sqlite_tables(conn)}


def sqlite_versions(conn):
    if "schemaVersions" not in sqlite_tables(conn):
        raise UpgradeRefusedError("No schemaVersions table: this file has no CCDB schema")
    return [row[0] for row in conn.execute("SELECT schemaVersion FROM schemaVersions")]


def replace_with_changed_copy(path, work_suffix, keep_suffix, change, expected_version, uncounted_tables=()):
    """Changes an SQLite file through a copy, so the file exists and is consistent at every moment.

    1. a stale <path><work_suffix> left by an interrupted run is removed, and the file is copied there through
       SQLite's backup API, which copies a consistent state even while other jobs read the file;
    2. change(connection) changes the copy, in its own transaction;
    3. the copy is verified: the version, the row count of every table but uncounted_tables, PRAGMA integrity_check;
       then VACUUM;
    4. the original is hard-linked to <path><keep_suffix>, then os.replace moves the copy over the original, which is
       atomic on POSIX. Jobs that hold the old file open keep reading it; new ones open the changed file.

    An interruption or a failure leaves the original untouched and removes the copy. When a job wrote to the original
    since the copy was taken, the copy is thrown away and the change refused, so no write is lost.
    """
    work, keep = path + work_suffix, path + keep_suffix
    if os.path.exists(work):
        log.info(f"Removing '{work}' left by an earlier run")
        os.remove(work)
    before = os.stat(path)
    try:
        source = sqlite_read_only(path)
        copy = sqlite3.connect(work, isolation_level=None)
        try:
            source.backup(copy)
        finally:
            source.close()
        try:
            # counted on the copy before the change: it is the state the backup took, while a job may write to the
            # original meanwhile, which the size and time check below reports
            original_counts = sqlite_row_counts(copy)
            change(copy)
            verify_sqlite_copy(copy, original_counts, expected_version, uncounted_tables)
            copy.execute("VACUUM")
        finally:
            copy.close()

        after = os.stat(path)
        if (after.st_size, after.st_mtime_ns) != (before.st_size, before.st_mtime_ns):
            raise UpgradeRefusedError(f"'{path}' changed while its copy was being changed: a job wrote to it. Nothing "
                                      "was changed; stop the writers and run the command again")
        try:
            os.link(path, keep)
        except FileExistsError:
            # the preflight found none; one appeared since, and the copy fallback below would overwrite it
            raise UpgradeRefusedError(f"'{keep}' appeared while the copy was being changed. Nothing was changed; move "
                                      "it away and run the command again")
        except OSError as error:
            # a file system without hard links: a copy keeps the original's bytes as well
            log.debug(f"Hard link to '{keep}' failed ({error}); copying instead")
            shutil.copy2(path, keep)
        os.replace(work, path)
    except BaseException:
        if os.path.exists(work):
            try:
                os.remove(work)
            except OSError as cleanup_error:
                log.warning(f"Could not remove '{work}': {cleanup_error}")
        raise
    log.info(f"'{path}' replaced by its changed copy; the file before the change is kept as '{keep}'")


def verify_sqlite_copy(copy, original_counts, expected_version, uncounted_tables):
    versions = [row[0] for row in copy.execute("SELECT schemaVersion FROM schemaVersions")]
    if versions != [expected_version]:
        raise RuntimeError(f"The changed copy has schema version {versions}, not {expected_version}")
    copy_counts = sqlite_row_counts(copy)
    for table, count in original_counts.items():
        if table in uncounted_tables or table not in copy_counts:
            continue
        if copy_counts[table] != count:
            raise RuntimeError(f"The changed copy has {copy_counts[table]} rows in {table}, the original {count}")
    integrity = copy.execute("PRAGMA integrity_check").fetchall()
    if integrity != [("ok",)]:
        raise RuntimeError(f"PRAGMA integrity_check of the changed copy: {integrity[:ROW_IDS_SHOWN]}")


class SqliteUpgrade:
    """The upgrade of an SQLite file in one transaction, on a copy that replaces the file (or in place)"""

    def __init__(self, path):
        self.path = path
        self.conn = None

    def run(self, in_place=False):
        sqlite_file_or_refuse(self.path)
        conn = sqlite_read_only(self.path)
        try:
            self.preflight(conn, check_kept_original=not in_place)
        finally:
            conn.close()

        if not in_place:
            replace_with_changed_copy(self.path, ".v6", ".v5", self.change, TARGET_VERSION)
            log.info(f"Schema version is {TARGET_VERSION}. Delete '{self.path}.v5' when you are satisfied")
            return

        # mode=rw never creates a file; isolation_level=None leaves BEGIN and COMMIT to this code, since the
        # sqlite3 module would otherwise commit before every DDL statement
        conn = sqlite3.connect(f"file:{self.path}?mode=rw", uri=True, isolation_level=None)
        try:
            self.change(conn, begin="BEGIN IMMEDIATE")
        finally:
            conn.close()
        log.info(f"Schema version is {TARGET_VERSION}")

    def change(self, conn, begin="BEGIN"):
        """Every schema 6 object in one transaction: an interruption changes nothing"""
        self.conn = conn
        self.conn.execute(begin)
        try:
            self.add_columns_and_tables()
            self.rebuild_constant_sets()
            self.create_index()
            self.execute("UPDATE schemaVersions SET schemaVersion = ?", (TARGET_VERSION,))
            self.conn.execute("COMMIT")
        except BaseException:
            self.conn.execute("ROLLBACK")
            raise

    def execute(self, sql, params=()):
        log.info(sql)
        return self.conn.execute(sql, params)

    def execute_script(self, script):
        """The statements of a schema snippet of sqlite_schema, one by one (executescript would commit)"""
        for statement in sqlite_schema._iter_statements(script):
            self.execute(statement)

    def tables(self):
        return sqlite_tables(self.conn)

    def columns(self, table):
        return sqlite_columns(self.conn, table)

    def preflight(self, conn, check_kept_original=True):
        check_version_rows(sqlite_versions(conn))
        problems = self.preflight_problems(conn, check_kept_original)
        if problems:
            raise UpgradeRefusedError("The upgrade to schema 6 is refused, nothing was changed: " + "; ".join(problems))

    def preflight_problems(self, conn, check_kept_original):
        problems = []
        kept = self.path + ".v5"
        if check_kept_original and os.path.exists(kept):
            problems.append(f"'{kept}' exists: an earlier upgrade kept the original file there. Move it away (or delete "
                            "it when you are satisfied with that upgrade), then run the upgrade again")
        if "tags" in sqlite_tables(conn) and "snapshotTime" not in sqlite_columns(conn, "tags"):
            count = conn.execute('SELECT COUNT(*) FROM "tags"').fetchone()[0]
            if count:
                problems.append(f"tags holds {count} rows. Schema 5 tags have no variation or time; decide what they mean "
                                "and empty the table before the upgrade")
        return problems

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

    def dry_run(self, duplicates):
        """Prints what the upgrade would do, writing nothing"""
        sqlite_file_or_refuse(self.path)
        conn = sqlite_read_only(self.path)
        try:
            print("Dry run of 'ccdb db upgrade': nothing is written")
            print(f"File: {self.path}, {os.path.getsize(self.path)} bytes, encoding "
                  f"{conn.execute('PRAGMA encoding').fetchone()[0]} (SQLite text is always Unicode: nothing to convert)")
            self.conn = conn
            check_version_rows(sqlite_versions(conn))
            for problem in self.preflight_problems(conn, check_kept_original=True):
                print(f"Preflight: would refuse: {problem}")
            print(f"The upgrade works on a copy, '{self.path}.v6', and replaces the file with it, keeping the original as "
                  f"'{self.path}.v5' (--in-place changes the file itself)")
            print("Changes, in one transaction:")
            for table, column, _, definition in NEW_COLUMNS:
                if column not in self.columns(table):
                    print(f"  {table}: new column {column} {definition}")
            if "sha256" not in self.columns("constantSets"):
                sets = conn.execute('SELECT COUNT(*) FROM "constantSets"').fetchone()[0]
                print(f"  constantSets: rebuilt with sha256 and size, {sets} sets hashed in batches of {BACKFILL_BATCH}")
            if "tags" not in self.tables() or "snapshotTime" not in self.columns("tags"):
                print("  tags: created anew in its schema 6 shape")
            for table in ("timeRanges", "properties"):
                if table not in self.tables():
                    print(f"  {table}: new table")
            print(f"  constantSets: the unique index {UNIQUE_INDEX}, or the interim index {INTERIM_INDEX} while a table "
                  "holds duplicate sets")
            print(f"  schemaVersions: {TARGET_VERSION}")
            if duplicates == "none":
                print("Duplicate sets: not counted (--duplicates none reads no vault)")
            else:
                # SQLite compares text by bytes, so equal vaults are byte-identical sets
                rows = conn.execute('SELECT "constantTypeId", COUNT(*) FROM "constantSets" '
                                    'GROUP BY "constantTypeId", "vault" HAVING COUNT(*) > 1').fetchall()
                print(f"Duplicate sets: {len(rows)} groups in {len({row[0] for row in rows})} tables, "
                      f"{sum(row[1] - 1 for row in rows)} redundant sets")
        finally:
            self.conn = None
            conn.close()


def split_create_table(create_sql):
    """A CREATE TABLE statement from sqlite_master as (head, items, tail): the text before the parenthesis, the column
    definitions and table constraints split at their top-level commas (outside parentheses and quotes), and the text
    from the closing parenthesis on"""
    open_at, close_at = create_sql.index("("), create_sql.rindex(")")
    body = create_sql[open_at + 1:close_at]
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
    return create_sql[:open_at], items, create_sql[close_at:]


def renamed_head(head, new_name):
    return re.sub(r'^\s*CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?("[^"]+"|`[^`]+`|\[[^\]]+\]|\S+)\s*',
                  f'CREATE TABLE "{new_name}" ', head, flags=re.IGNORECASE)


_TABLE_CONSTRAINT = re.compile(r"\s*(CONSTRAINT|PRIMARY\s+KEY|UNIQUE|CHECK|FOREIGN\s+KEY)\b", re.IGNORECASE)


def create_with_columns(create_sql, new_name, column_definitions):
    """A CREATE TABLE statement from sqlite_master, renamed to new_name, with column_definitions added after the last
    column definition, before the table constraints (PRIMARY KEY (...), UNIQUE (...)) if there are any.

    The rest of the statement stays as it was, so converted files keep their own key and constraint clauses.
    """
    head, items, tail = split_create_table(create_sql)
    first_constraint = next((i for i, item in enumerate(items) if _TABLE_CONSTRAINT.match(item)), len(items))
    items[first_constraint:first_constraint] = ["\n  " + definition for definition in column_definitions]
    return renamed_head(head, new_name) + "(" + ",".join(items) + tail
