"""Schema 6 upgrade and rollback through the CLI: design note schema6.md §6 and §9, matrix rows T20, T21, T22, T25.

Every database starts as the frozen schema 5 base (schema_v5_base.py) and is changed only by `ccdb db ...`
commands, driven in-process the way integ_test_cli_manager drives them. SQLite databases live in temporary
directories. The MySQL and MariaDB tests rebuild the database of CCDB_TEST_MYSQL_CONNECTION for every test,
are skipped when it is unset, and leave that database re-initialized by `db init` for the modules after them.

    CCDB_TEST_MYSQL_CONNECTION          the database the tests rebuild, as ccdb_user (pattern grant, no PROCESS)
    CCDB_TEST_MYSQL_READER_CONNECTION   the same database as ccdb_reader (SELECT only, scripts/schema/test_users.sql): T22
    CCDB_TEST_MYSQL_ROOT_CONNECTION     the same database as root: the T22 open-transaction case and the T25 non-strict
                                        case, which sets the global sql_mode for a moment and restores it

The reader and root variables are the test connections of §14.1: tests needing one skip without it, and CI sets both
(item 8). The helpers of this module are shared with unit_test_dedup and unit_test_rehash.

Contracts of §14.1 these tests rely on: `db upgrade`, `db dedup`, `db rollback-v6` and `db rehash` exit 0 on success
and 1 on a refusal, a collision or a mismatch (`rehash --rehash-i-am-sure` 0 when it repaired every mismatch); no command prompts;
the upgrade and the rollback write no `logs` row; an SQLite upgrade refuses while `<file>.v5` exists.
"""
import hashlib
import importlib.util
import logging
import os
import re
import shutil
import sqlite3
import sys
import tempfile
import threading
import time
import unittest
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from io import StringIO
from unittest import mock

import sqlalchemy
from sqlalchemy import event, text
from sqlalchemy.engine import Engine, make_url

import ccdb
from ccdb import testing as helper
from ccdb.cmd.cli_manager import CliManager, CCDB_EXCEPTIONS_THROW
from ccdb.cmd.themes import NoColorTheme
from ccdb.cmd.utility_argument_parser import ArgumentParseError

# Have to import it this way as tests may be considered a package or not depending on context
try:
    from . import schema_v5_base
except ImportError:
    import schema_v5_base


ENV_MYSQL_READER = "CCDB_TEST_MYSQL_READER_CONNECTION"
ENV_MYSQL_ROOT = "CCDB_TEST_MYSQL_ROOT_CONNECTION"

UPGRADE = "db upgrade --upgrade-i-am-sure --sqlite-time-zone UTC"
ROLLBACK = "db rollback-v6 --rollback-i-am-sure --sqlite-time-zone UTC"
BACKFILL_BATCH = 500        # §6.3 step 2 and §6.4 step 2: LIMIT 500, one commit per batch


def _load_schema_compare():
    """scripts/schema/compare.py, the structure dump the equality tests of §14 use (T2)"""
    path = os.path.join(ccdb.get_ccdb_home_path(), "scripts", "schema", "compare.py")
    spec = importlib.util.spec_from_file_location("ccdb_scripts_schema_compare", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


schema_compare = _load_schema_compare()


def digest(vault):
    """The test's own oracle for vault_digest (§4.1): hex SHA-256 and byte count of the UTF-8 bytes"""
    data = vault.encode("utf-8")
    return hashlib.sha256(data).hexdigest(), len(data)


def file_sha256(path):
    with open(path, "rb") as stream:
        return hashlib.sha256(stream.read()).hexdigest()


def engine_free(lines):
    """Structure lines of compare.dump without the table engine: T25 compares with engine and charset ignored"""
    return [re.sub(r" engine=\S+", "", line) if line.startswith("table ") else line for line in lines]


# ---------------------------------------------------------------------------------------------------------------
#  CLI
# ---------------------------------------------------------------------------------------------------------------

class CliRun(object):
    """What one in-process `ccdb` command did: its result, its printed and logged text, the exception it raised"""

    def __init__(self, command_line, result, output, error):
        self.command_line = command_line
        self.result = result
        self.output = output
        self.error = error

    @property
    def ok(self):
        """Exit status 0 under the contract of ccdb/__init__.py, where None or False (or an exception) exits 1.

        §14.1: the db commands exit 0 on success and 1 on a refusal, a collision or a mismatch, so `not ok` is exit 1.
        """
        return self.error is None and self.result is not None and self.result is not False

    def said(self):
        """What the command printed and logged, plus the text of the exception it raised; without the command line"""
        error = "" if self.error is None else "\n{}: {}".format(type(self.error).__name__, self.error)
        return self.output + error

    def text(self):
        return "$ ccdb {}\n{}".format(self.command_line, self.said())


# A statement as a command may print it (§6.5 prints every DDL statement): from its keywords to the end of the line
_SQL_TEXT = re.compile(r"\b(ALTER\s+(TABLE|DATABASE)|CREATE\s+(TABLE|(UNIQUE\s+)?INDEX)|DROP\s+(TABLE|INDEX|COLUMN)"
                       r"|ADD\s+(UNIQUE\s+)?(INDEX|COLUMN)|UPDATE\s+`?\w+`?\s+SET|MODIFY\s+(COLUMN\s+)?`?\w+`?\s+\w).*$",
                       re.IGNORECASE)
_TYPE_ARGUMENT = re.compile(r"\(\s*\d+(\s*,\s*\d+)?\s*\)")             # CHAR(64), VARCHAR(100), DECIMAL(10,2)
_IDENTIFIER_WITH_DIGIT = re.compile(r"\b[A-Za-z_]\w*\d\w*")               # utf8mb4, latin1_swedish_ci, cp1251, ..._timeRanges1_idx


def prose_lines(text):
    """The lines of a command's text with every printed SQL statement cut off, so planned DDL cannot satisfy a check
    for a word the note says the prose names (a privilege, a table's size)"""
    return [_SQL_TEXT.sub("", line) for line in text.splitlines()]


def lines_with_numbers(text):
    """prose_lines without type arguments and identifiers that contain digits: a digit left in a line is a number"""
    return [_IDENTIFIER_WITH_DIGIT.sub("", _TYPE_ARGUMENT.sub("", line)) for line in prose_lines(text)]


def run_ccdb(connection_string, command_line, allow_parse_error=False):
    """Runs one command on a fresh CliManager, as integ_test_cli_manager does, and returns a CliRun.

    A fresh manager per command: the db commands connect their provider themselves, and connect() refuses a
    provider that is connected already. An ArgumentParseError is re-raised unless allowed: an unknown subcommand
    option is a missing feature, never a refusal the note describes. §14.1: no command prompts, so a prompt raises
    AssertionError here whatever the test expects, and cannot pass for a refusal.
    """
    prompts = []

    def no_prompt(prompt=""):
        prompts.append(prompt)
        raise EOFError("§14.1: no command prompts")

    cli = CliManager()
    cli.exception_handling = CCDB_EXCEPTIONS_THROW
    cli.force_exceptions = True
    cli.theme = NoColorTheme()
    cli.connection_string = connection_string
    cli.context.user_name = "test_user"
    cli.log_sqlite = True               # log records are part of what dedup and rehash promise (§7, §8)
    cli.register_utilities()

    stream = StringIO()
    handler = logging.StreamHandler(stream)
    logger = logging.getLogger("ccdb")
    saved_level = logger.level
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    result, error = None, None
    try:
        with redirect_stdout(stream), redirect_stderr(stream), \
                mock.patch("builtins.input", no_prompt), mock.patch("getpass.getpass", no_prompt):
            try:
                result = cli.process_command_line(command_line)
            except ArgumentParseError as parse_error:
                if not allow_parse_error:
                    raise
                error = parse_error
            except Exception as ex:
                error = ex
    finally:
        logger.removeHandler(handler)
        logger.setLevel(saved_level)
        try:
            if cli.provider.is_connected:
                cli.provider.disconnect()
        except Exception:
            pass
    if prompts:
        raise AssertionError("§14.1: no command prompts, but `ccdb {}` asked {!r}".format(command_line, prompts))
    return CliRun(command_line, result, stream.getvalue(), error)


class SimulatedInterruption(Exception):
    """Raised by a patched vault_digest to cut an upgrade off in the middle of its backfill"""


@contextmanager
def patched_vault_digest(replacement):
    """Replaces ccdb.model.vault_digest, and every ccdb module's own binding of it, for the duration.

    The backfill calls vault_digest in Python (§4.1, Q35). A module that did `from ccdb.model import vault_digest`
    before the patch holds its own reference, so every ccdb module attribute that is the original is patched too;
    a module imported inside the window picks up the patched ccdb.model attribute, and gets the original back on exit.
    """
    import ccdb.model
    original = ccdb.model.vault_digest
    patches = []
    for name, module in list(sys.modules.items()):
        if module is None or not (name == "ccdb" or name.startswith("ccdb.")):
            continue
        for attribute, value in list(vars(module).items()):
            if value is original:
                patches.append(mock.patch.object(module, attribute, replacement))
    for patch in patches:
        patch.start()
    try:
        yield
    finally:
        for patch in reversed(patches):
            patch.stop()
        # A module first imported inside the window (the first CLI call imports the db command and its upgrade module)
        # bound the replacement itself, and no patch above restores it
        for name, module in list(sys.modules.items()):
            if module is None or not (name == "ccdb" or name.startswith("ccdb.")):
                continue
            for attribute, value in list(vars(module).items()):
                if value is replacement:
                    setattr(module, attribute, original)


# ---------------------------------------------------------------------------------------------------------------
#  Statements a command sends (T22)
# ---------------------------------------------------------------------------------------------------------------

_STRING_LITERAL = re.compile(r"'(?:[^'\\]|\\.|'')*'|\"(?:[^\"\\]|\\.)*\"")
_VAULT_IDENTIFIER = re.compile(r"\bvault\b", re.IGNORECASE)
_WRITE_STATEMENT = re.compile(r"^\s*(ALTER|CREATE|DROP|INSERT|UPDATE|DELETE|REPLACE|RENAME|TRUNCATE|OPTIMIZE)\b",
                              re.IGNORECASE)


class StatementLog(object):
    """Records every statement any SQLAlchemy engine sends while the block runs (MySQL quoting rules)"""

    def __init__(self):
        self.statements = []
        self._listener = self._record

    def _record(self, conn, cursor, statement, parameters, context, executemany):
        self.statements.append(statement)

    def __enter__(self):
        event.listen(Engine, "before_cursor_execute", self._listener)
        return self

    def __exit__(self, *exc_info):
        event.remove(Engine, "before_cursor_execute", self._listener)
        return False

    def vault_reads(self):
        """Statements that name the vault column outside a string literal"""
        return [s for s in self.statements if _VAULT_IDENTIFIER.search(_STRING_LITERAL.sub("''", s))]

    def writes(self):
        return [s for s in self.statements if _WRITE_STATEMENT.match(s)]


# ---------------------------------------------------------------------------------------------------------------
#  Databases
# ---------------------------------------------------------------------------------------------------------------

class _Db(object):
    """A test database reached by a fresh engine per call, so no test connection stays open across a command"""

    kind = ""
    no_tx_check = ""            # the flag every MySQL apply command needs as ccdb_user, who lacks PROCESS (§6.2 item 3)

    def __init__(self, url):
        self.url = url

    def engine(self):
        raise NotImplementedError

    def execute(self, sql, params=None):
        engine = self.engine()
        try:
            with engine.begin() as conn:
                conn.execute(text(sql), params if params is not None else {})
        finally:
            engine.dispose()

    def query(self, sql, params=None):
        engine = self.engine()
        try:
            with engine.connect() as conn:
                return [tuple(row) for row in conn.execute(text(sql), params if params is not None else {})]
        finally:
            engine.dispose()

    def scalar(self, sql, params=None):
        rows = self.query(sql, params)
        return rows[0][0] if rows else None

    def version(self):
        versions = [row[0] for row in self.query("SELECT `schemaVersion` FROM `schemaVersions`")]
        return versions[0] if len(versions) == 1 else versions

    def structure(self, with_charset=False):
        return schema_compare.dump(self.url, with_charset=with_charset)

    def max_log_id(self):
        return self.scalar("SELECT MAX(`id`) FROM `logs`") or 0

    def log_ids(self):
        return [row[0] for row in self.query("SELECT `id` FROM `logs` ORDER BY `id`")]

    def logs_after(self, log_id):
        return self.query("SELECT `id`, `affectedIds`, `action`, `description` FROM `logs` WHERE `id` > :id ORDER BY `id`",
                          {"id": log_id})

    def insert_sets(self, rows):
        """rows: (id, constantTypeId, vault), schema 5 columns only"""
        params = [{"id": i, "t": "2020-01-01 00:00:00", "v": vault, "type": type_id} for i, type_id, vault in rows]
        engine = self.engine()
        try:
            with engine.begin() as conn:
                conn.execute(text("INSERT INTO `constantSets` (`id`, `created`, `modified`, `vault`, `constantTypeId`) "
                                  "VALUES (:id, :t, :t, :v, :type)"), params)
        finally:
            engine.dispose()

    def insert_assignments(self, rows):
        """rows: (id, constantSetId, created), schema 5 columns only, variation default, run range 'all'"""
        params = [{"id": i, "set": set_id, "t": created, "c": "assignment %d" % i} for i, set_id, created in rows]
        engine = self.engine()
        try:
            with engine.begin() as conn:
                conn.execute(text("INSERT INTO `assignments` (`id`, `created`, `modified`, `variationId`, `runRangeId`, "
                                  "`eventRangeId`, `authorId`, `comment`, `constantSetId`) "
                                  "VALUES (:id, :t, :t, 1, 1, NULL, 2, :c, :set)"), params)
        finally:
            engine.dispose()

    def check_hashes(self, test, expected_vaults=None):
        """Every stored sha256 and size equals the oracle of the stored vault, and of the vault the test wrote"""
        rows = self.query("SELECT `id`, `vault`, `sha256`, `size` FROM `constantSets` ORDER BY `id`")
        test.assertTrue(rows)
        for set_id, vault, sha256, size in rows:
            test.assertEqual((sha256, size), digest(vault), "set %d" % set_id)
            if expected_vaults is not None and set_id in expected_vaults:
                test.assertEqual((sha256, size), digest(expected_vaults[set_id]), "set %d" % set_id)
        return len(rows)


class SqliteDb(_Db):
    kind = "sqlite"
    sibling_suffixes = (".v5", ".v6", ".before-rollback")

    def __init__(self, directory, name="ccdb.sqlite"):
        self.path = os.path.join(directory, name)
        _Db.__init__(self, "sqlite:///" + self.path)

    def engine(self):
        return sqlalchemy.create_engine(self.url)

    def build_v5(self):
        for path in [self.path] + [self.path + suffix for suffix in self.sibling_suffixes]:
            if os.path.exists(path):
                os.remove(path)
        engine = self.engine()
        schema_v5_base.create_v5_sqlite(engine)
        engine.dispose()

    def columns(self, table):
        """{column: nullable}"""
        return {row[1]: not row[3] for row in self.query('PRAGMA table_info("%s")' % table)}

    def indexes(self, table):
        """{index: unique}"""
        return {row[1]: bool(row[2]) for row in self.query('PRAGMA index_list("%s")' % table)}

    def collations(self):
        return []

    def instant_alter_counter(self):
        return None


class MysqlDb(_Db):
    kind = "mysql"
    no_tx_check = " --no-transaction-check"

    def engine(self):
        return schema_compare.engine_for(self.url)

    def drop_all_tables(self):
        engine = self.engine()
        try:
            with engine.begin() as conn:
                names = [row[0] for row in conn.execute(text(
                    "SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE()"))]
                for name in names:
                    conn.execute(text("DROP TABLE IF EXISTS `%s`" % name))
                # the upgrade changes the database default (§3); a fresh schema 5 takes the server default
                database, charset, collation = conn.execute(text(
                    "SELECT DATABASE(), @@character_set_server, @@collation_server")).one()
                conn.execute(text("ALTER DATABASE `%s` CHARACTER SET %s COLLATE %s" % (database, charset, collation)))
        finally:
            engine.dispose()

    def build_v5(self):
        self.drop_all_tables()
        engine = self.engine()
        schema_v5_base.create_v5_mysql(engine)
        engine.dispose()

    def columns(self, table):
        return {name: nullable == "YES" for name, nullable in self.query(
            "SELECT COLUMN_NAME, IS_NULLABLE FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t", {"t": table})}

    def indexes(self, table):
        return {name: int(non_unique) == 0 for name, non_unique in self.query(
            "SELECT DISTINCT INDEX_NAME, NON_UNIQUE FROM information_schema.STATISTICS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t", {"t": table})}

    def collations(self):
        return self.query("SELECT TABLE_NAME, COLUMN_NAME, COLLATION_NAME FROM information_schema.COLUMNS "
                          "WHERE TABLE_SCHEMA = DATABASE() ORDER BY TABLE_NAME, COLUMN_NAME")

    def instant_alter_counter(self):
        """MariaDB before 10.6.9: Innodb_instant_alter_column, which §6.3 and §9 keep unchanged; None elsewhere"""
        version = self.scalar("SELECT VERSION()")
        if "mariadb" not in version.lower():
            return None
        numbers = tuple(int(part) for part in re.match(r"(\d+)\.(\d+)\.(\d+)", version).groups())
        if numbers >= (10, 6, 9):
            return None
        rows = self.query("SHOW GLOBAL STATUS LIKE 'Innodb_instant_alter_column'")
        return int(rows[0][1])

    def has_process_privilege(self):
        return bool(self.query("SELECT 1 FROM information_schema.USER_PRIVILEGES WHERE PRIVILEGE_TYPE = 'PROCESS'"))


def mysql_url_or_skip():
    url = os.environ.get(helper.ENV_TEST_MYSQL)
    if not url:
        raise unittest.SkipTest("{} is not set".format(helper.ENV_TEST_MYSQL))
    return url


def restore_mysql_test_db(url):
    """Leaves the shared MySQL test database as `db init` creates it, for the test modules that run after"""
    db = MysqlDb(url)
    db.drop_all_tables()
    run = run_ccdb(url, "db init --init-i-am-sure")
    if not run.ok:
        raise RuntimeError("db init after the schema 6 tests failed:\n" + run.text())


def sqlite_ro(path):
    """A read-only sqlite3 connection that never creates the file"""
    return sqlite3.connect("file:{}?mode=ro".format(path), uri=True)


def sqlite_rows(path, sql):
    connection = sqlite_ro(path)
    try:
        return connection.execute(sql).fetchall()
    finally:
        connection.close()


def sqlite_table_counts(path):
    names = [row[0] for row in sqlite_rows(path, "SELECT name FROM sqlite_master WHERE type = 'table' "
                                                 "AND name NOT LIKE 'sqlite_%'")]
    return {name: sqlite_rows(path, 'SELECT COUNT(*) FROM "%s"' % name)[0][0] for name in names}


class FileWatch(object):
    """Records every moment a path is missing: polled by a thread and checked around each os file call"""

    def __init__(self, path):
        self.path = path
        self.missing = []
        self._stop = threading.Event()
        self._patches = []
        self._thread = None

    def _check(self, moment):
        if not os.path.exists(self.path):
            self.missing.append(moment)

    def _poll(self):
        while not self._stop.is_set():
            self._check("poll")
            time.sleep(0.0005)

    def _wrapped(self, name):
        original = getattr(os, name)

        def wrapper(*args, **kwargs):
            self._check("before os.{}{!r}".format(name, args))
            try:
                return original(*args, **kwargs)
            finally:
                self._check("after os.{}{!r}".format(name, args))
        return mock.patch.object(os, name, wrapper)

    def __enter__(self):
        self._patches = [self._wrapped(name) for name in ("replace", "rename", "remove", "unlink")]
        for patch in self._patches:
            patch.start()
        self._thread = threading.Thread(target=self._poll, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *exc_info):
        self._stop.set()
        self._thread.join()
        for patch in reversed(self._patches):
            patch.stop()
        return False


# ---------------------------------------------------------------------------------------------------------------
#  T25: rollback, SQLite and both servers
# ---------------------------------------------------------------------------------------------------------------

# One kind of schema 6 data each: rollback refuses while any of them exists (§9), and --drop-v6-data deletes it
V6_DATA = [
    ("a tags row", "INSERT INTO `tags` (`name`, `variationId`, `snapshotTime`) VALUES ('t25_tag', 1, '2026-01-01 00:00:00')",
     "DELETE FROM `tags`"),
    ("a properties row", "INSERT INTO `properties` (`ownerType`, `ownerId`, `name`, `value`) VALUES ('instance', 0, 't25', 'x')",
     "DELETE FROM `properties`"),
    ("a timeRanges row", "INSERT INTO `timeRanges` (`timeFrom`) VALUES ('2026-01-01 00:00:00')",
     "DELETE FROM `timeRanges`"),
    ("columns.units", "UPDATE `columns` SET `units` = 'us' WHERE `id` = 1",
     "UPDATE `columns` SET `units` = NULL"),
    ("typeTables.deprecatedTime", "UPDATE `typeTables` SET `deprecatedTime` = '2026-01-01 00:00:00' WHERE `id` = 1",
     "UPDATE `typeTables` SET `deprecatedTime` = NULL"),
    ("directories.deprecationComment", "UPDATE `directories` SET `deprecationComment` = 'old' WHERE `id` = 1",
     "UPDATE `directories` SET `deprecationComment` = NULL"),
    ("assignments.timeRangeId", "UPDATE `assignments` SET `timeRangeId` = 1 WHERE `id` = 1",
     "UPDATE `assignments` SET `timeRangeId` = NULL"),
]

SETS_SQL = "SELECT `id`, `constantTypeId`, `vault`, `sha256`, `size` FROM `constantSets` ORDER BY `id`"


class RollbackCases(object):
    """T25 for one backend: the class provides self.db, make_partial() and the file hooks"""

    def upgrade(self):
        logs = self.db.log_ids()
        run = run_ccdb(self.db.url, UPGRADE + self.db.no_tx_check)
        self.assertTrue(run.ok, run.text())
        self.assertEqual(self.db.version(), 6)
        self.assertEqual(self.db.log_ids(), logs, "§14.1: the upgrade writes no logs row")

    def assert_refusal_left_no_copy(self):
        pass

    def check_rollback_files(self):
        pass

    def before_second_upgrade(self):
        pass

    def make_partial(self):
        raise NotImplementedError

    def check_instant_counter(self, counter, elapsed):
        """MariaDB before 10.6.9: Innodb_instant_alter_column unchanged by the rollback (T25, §9).

        The counter is global to the server. When it moves during an idle window as long as the rollback took, other
        sessions are altering tables on this server, and only this check is skipped (CI's server is dedicated).
        """
        with self.subTest("Innodb_instant_alter_column"):
            after = self.db.instant_alter_counter()
            time.sleep(min(max(elapsed, 1.0), 10.0))
            if self.db.instant_alter_counter() != after:
                self.skipTest("server not dedicated: Innodb_instant_alter_column moved while this test was idle")
            self.assertEqual(after, counter, "MariaDB before 10.6.9: no instant ALTER in rollback")

    def test_rollback(self):
        """T25 (§9): rollback leaves no schema 6 object, refuses on v6 data, re-upgrade equals the first, partial v5 rolls back"""
        db = self.db
        db.build_v5()
        base = engine_free(db.structure())
        self.upgrade()
        upgraded = db.structure(with_charset=True)
        upgraded_collations = db.collations()
        upgraded_sets = db.query(SETS_SQL)

        for label, write, undo in V6_DATA:
            db.execute(write)
            run = run_ccdb(db.url, ROLLBACK + db.no_tx_check)
            self.assertFalse(run.ok, "rollback must refuse while {} holds data\n{}".format(label, run.text()))
            self.assertEqual(db.version(), 6, label)
            self.assertEqual(db.structure(with_charset=True), upgraded, label)
            self.assert_refusal_left_no_copy()
            db.execute(undo)

        for label, write, undo in V6_DATA:
            db.execute(write)
        logs = db.log_ids()
        counter = db.instant_alter_counter()
        started = time.monotonic()
        run = run_ccdb(db.url, ROLLBACK + " --drop-v6-data" + db.no_tx_check)
        elapsed = time.monotonic() - started
        self.assertTrue(run.ok, run.text())
        if counter is not None:
            self.check_instant_counter(counter, elapsed)
        self.assertEqual(db.version(), 5)
        self.assertEqual(engine_free(db.structure()), base)
        self.assertEqual(db.log_ids(), logs, "§14.1: the rollback writes no logs row")
        self.check_rollback_files()

        self.before_second_upgrade()
        self.upgrade()
        self.assertEqual(db.structure(with_charset=True), upgraded)
        self.assertEqual(db.collations(), upgraded_collations)
        self.assertEqual(db.query(SETS_SQL), upgraded_sets)

        db.build_v5()
        self.make_partial()
        run = run_ccdb(db.url, ROLLBACK + db.no_tx_check)
        self.assertTrue(run.ok, run.text())
        self.assertEqual(db.version(), 5)
        self.assertEqual(engine_free(db.structure()), base)


# ---------------------------------------------------------------------------------------------------------------
#  SQLite
# ---------------------------------------------------------------------------------------------------------------

# Schema 6 objects of §2.1 and §2.2 on a version 5 file, as an interrupted in-place run of an early build leaves them
SQLITE_PARTIAL = [
    'ALTER TABLE "columns" ADD COLUMN "units" VARCHAR(64) NULL',
    'ALTER TABLE "assignments" ADD COLUMN "timeRangeId" INTEGER NULL',
    'CREATE INDEX "fk_assignments_timeRanges1_idx" ON "assignments" ("timeRangeId")',
    'CREATE TABLE "timeRanges" ("id" INTEGER NOT NULL PRIMARY KEY, "timeFrom" DATETIME NOT NULL, '
    '"timeTo" DATETIME NULL, "comment" TEXT NULL)',
]


class SQLiteUpgradeV6Test(RollbackCases, unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db = SqliteDb(self.tmp_dir.name)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def assert_refusal_left_no_copy(self):
        self.assertFalse(os.path.exists(self.db.path + ".before-rollback"), "a refused rollback copies nothing")

    def check_rollback_files(self):
        kept = self.db.path + ".before-rollback"
        self.assertTrue(os.path.exists(kept), "§6.4, §9: rollback keeps <file>.before-rollback")
        self.assertEqual(sqlite_rows(kept, "SELECT schemaVersion FROM schemaVersions"), [(6,)])

    def before_second_upgrade(self):
        """§14.1: while <file>.v5 exists the upgrade refuses, naming it, until you move it away.

        Whether the rollback keeps the first upgrade's <file>.v5 is open, so a leftover one is made when it is gone.
        """
        path = self.db.path
        kept = path + ".v5"
        if not os.path.exists(kept):
            shutil.copyfile(path, kept)
        original_hash = file_sha256(path)
        run = run_ccdb(self.db.url, UPGRADE)
        self.assertFalse(run.ok, "the upgrade must refuse while <file>.v5 exists\n" + run.text())
        self.assertIn(os.path.basename(kept), run.said(), "the refusal names <file>.v5")
        self.assertEqual(file_sha256(path), original_hash, "the refused upgrade changed the file")
        self.assertEqual(self.db.version(), 5)
        os.remove(kept)

    def make_partial(self):
        for statement in SQLITE_PARTIAL:
            self.db.execute(statement)
        self.assertEqual(self.db.version(), 5)

    def test_confirmation_flags(self):
        """§10, §14.1 "confirmation": without its --<verb>-i-am-sure flag the upgrade and the rollback change nothing,
        name the flag and exit 1; the upgrade warns about the backup, as 2.4 does, and no command makes one"""
        db = self.db
        db.build_v5()
        original_hash = file_sha256(db.path)
        run = run_ccdb(db.url, "db upgrade")
        self.assertFalse(run.ok, "a missing --upgrade-i-am-sure is a refusal\n" + run.text())
        self.assertIn("--upgrade-i-am-sure", run.said())
        self.assertIn("BACKUP", run.said().upper(), "the upgrade without its flag warns about the backup")
        self.assertNotIn("--backup-taken", run.said())
        self.assertEqual(file_sha256(db.path), original_hash, "the upgrade without its flag changed the file")
        self.assertEqual(db.version(), 5)

        self.upgrade()
        upgraded = db.structure(with_charset=True)
        run = run_ccdb(db.url, "db rollback-v6")
        self.assertFalse(run.ok, "a missing --rollback-i-am-sure is a refusal\n" + run.text())
        self.assertIn("--rollback-i-am-sure", run.said())
        self.assertEqual(db.version(), 6)
        self.assertEqual(db.structure(with_charset=True), upgraded)

    def test_sqlite_upgrade_copy(self):
        """T21 (§6.4): an interrupted SQLite upgrade leaves the file unchanged; the rerun replaces it atomically, keeps .v5"""
        db = self.db
        path = db.path
        db.build_v5()
        vaults = {6000 + i: "|".join("{}.{}".format(i, k) for k in range(6)) for i in range(BACKFILL_BATCH + 100)}
        db.insert_sets([(set_id, 1, vault) for set_id, vault in vaults.items()])
        original_hash = file_sha256(path)
        original_inode = os.stat(path).st_ino
        original_counts = sqlite_table_counts(path)

        def interrupting(vault):
            raise SimulatedInterruption("T21: upgrade interrupted while the copy is rebuilt")

        with FileWatch(path) as watch, patched_vault_digest(interrupting):
            run = run_ccdb(db.url, UPGRADE)
        self.assertFalse(run.ok, run.text())
        self.assertEqual(watch.missing, [])
        self.assertEqual(file_sha256(path), original_hash, "the interrupted upgrade changed the original file")
        self.assertEqual(sqlite_rows(path, "SELECT schemaVersion FROM schemaVersions"), [(5,)])

        # a stale copy as an earlier run that was killed leaves it: the rerun must not build on it
        stale = path + ".v6"
        shutil.copyfile(path, stale)
        connection = sqlite3.connect(stale)
        connection.execute('CREATE TABLE "stale_marker" ("id" INTEGER)')
        connection.commit()
        connection.close()

        # a job that holds the old file open keeps reading it
        old_reader = sqlite3.connect(path)
        try:
            self.assertEqual(old_reader.execute("SELECT schemaVersion FROM schemaVersions").fetchall(), [(5,)])
            with FileWatch(path) as watch:
                run = run_ccdb(db.url, UPGRADE)
            self.assertTrue(run.ok, run.text())
            self.assertEqual(watch.missing, [], "<file> must exist at every moment of the upgrade")
            self.assertEqual(old_reader.execute("SELECT schemaVersion FROM schemaVersions").fetchall(), [(5,)])
        finally:
            old_reader.close()

        self.assertFalse(os.path.exists(stale), "<file>.v6 is gone after the replace")
        self.assertEqual(sqlite_rows(path, "SELECT schemaVersion FROM schemaVersions"), [(6,)])
        self.assertEqual(sqlite_rows(path, "PRAGMA integrity_check"), [("ok",)])
        upgraded_counts = sqlite_table_counts(path)
        self.assertNotIn("stale_marker", upgraded_counts, "the rerun built on the stale <file>.v6")
        for table, count in original_counts.items():
            self.assertEqual(upgraded_counts.get(table), count, table)      # logs too: §14.1, the upgrade writes none
        self.assertNotEqual(os.stat(path).st_ino, original_inode, "<file> was replaced by the upgraded copy")
        self.assertEqual(db.check_hashes(self, vaults), original_counts["constantSets"])

        kept = path + ".v5"
        self.assertTrue(os.path.exists(kept), "<file>.v5 is kept")
        self.assertEqual(os.stat(kept).st_ino, original_inode, "<file>.v5 is a hard link of the original")
        self.assertEqual(file_sha256(kept), original_hash)


# ---------------------------------------------------------------------------------------------------------------
#  MySQL and MariaDB
# ---------------------------------------------------------------------------------------------------------------

class MySQLUpgradeV6Test(RollbackCases, unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.db = MysqlDb(mysql_url_or_skip())

    @classmethod
    def tearDownClass(cls):
        restore_mysql_test_db(cls.db.url)

    def other_url_or_skip(self, variable):
        url = os.environ.get(variable)
        if not url:
            self.skipTest("{} is not set".format(variable))
        other, main = make_url(url), make_url(self.db.url)
        self.assertEqual((other.host, other.port, other.database), (main.host, main.port, main.database),
                         "{} must name the database of {}".format(variable, helper.ENV_TEST_MYSQL))
        return url

    def make_partial(self):
        def interrupting(vault):
            raise SimulatedInterruption("T25: upgrade interrupted in the backfill")

        with patched_vault_digest(interrupting):
            run = run_ccdb(self.db.url, UPGRADE + self.db.no_tx_check)
        self.assertFalse(run.ok, run.text())
        self.assertEqual(self.db.version(), 5)
        self.assertIn("sha256", self.db.columns("constantSets"), "step 1 ran before the interruption")

    def test_backfill_resume(self):
        """T20 (§6.3 step 2): 1 200 sets hashed in batches, interrupted after the first batch, resumed; hashes equal Python's"""
        from ccdb.model import vault_digest
        db = self.db
        db.build_v5()
        vaults = {}
        for i in range(1200):
            values = ["{}.{}".format(i, k) for k in range(6)]
            if i % 100 == 0:
                values[0] = "{}µs".format(i)            # µ survives every source charset: a hash of UTF-8 bytes
            vaults[1001 + i] = "|".join(values)
        db.insert_sets([(set_id, 1, vault) for set_id, vault in vaults.items()])
        total = db.scalar("SELECT COUNT(*) FROM `constantSets`")
        for vault in list(vaults.values())[:3]:
            self.assertEqual(vault_digest(vault), digest(vault))

        calls = []

        def interrupting(vault):
            calls.append(vault)
            if len(calls) > BACKFILL_BATCH:
                raise SimulatedInterruption("T20: upgrade interrupted after the first batch")
            return vault_digest(vault)

        with patched_vault_digest(interrupting):
            run = run_ccdb(db.url, UPGRADE + db.no_tx_check)
        self.assertFalse(run.ok, run.text())
        self.assertEqual(db.version(), 5)
        self.assertTrue(db.columns("constantSets").get("sha256"), "sha256 exists and is still NULL-able")
        hashed = db.query("SELECT `id`, `vault`, `sha256`, `size` FROM `constantSets` WHERE `sha256` IS NOT NULL")
        self.assertEqual(len(hashed), BACKFILL_BATCH, "one committed batch")
        for set_id, vault, sha256, size in hashed:
            self.assertEqual((sha256, size), digest(vault), "set %d" % set_id)

        # before the resume: a set a 2.4 client writes (no hash) and a hash that is not lowercase hex (§6.3)
        vaults[2201] = "2201|2202|2203|2204|2205|2206"
        db.execute("INSERT INTO `constantSets` (`id`, `created`, `modified`, `vault`, `constantTypeId`) "
                   "VALUES (2201, '2020-01-02 00:00:00', '2020-01-02 00:00:00', :v, 1)", {"v": vaults[2201]})
        uppercased = hashed[-1][0]
        db.execute("UPDATE `constantSets` SET `sha256` = UPPER(`sha256`) WHERE `id` = :id", {"id": uppercased})

        resumed = []

        def counting(vault):
            resumed.append(vault)
            return vault_digest(vault)

        with patched_vault_digest(counting):
            run = run_ccdb(db.url, UPGRADE + db.no_tx_check)
        self.assertTrue(run.ok, run.text())
        self.assertEqual(len(resumed), total - BACKFILL_BATCH + 2, "the resume reads only unhashed rows")
        self.assertEqual(db.version(), 6)
        columns = db.columns("constantSets")
        self.assertFalse(columns["sha256"])
        self.assertFalse(columns["size"])
        self.assertEqual(db.check_hashes(self, vaults), total + 1)
        self.assertTrue(db.indexes("constantSets").get("uq_constantSets_table_sha256"), "no duplicates: unique index")

    def test_dry_run_and_preflight(self):
        """T22 (§6.5, §6.2): dry run as ccdb_reader reads no vault and changes nothing; apply as reader fails in preflight"""
        reader_url = self.other_url_or_skip(ENV_MYSQL_READER)
        db = self.db
        db.build_v5()
        before = db.structure(with_charset=True)
        myisam = [row[0] for row in db.query("SELECT TABLE_NAME FROM information_schema.TABLES "
                                             "WHERE TABLE_SCHEMA = DATABASE() AND ENGINE = 'MyISAM'")]
        self.assertIn("assignments", myisam, "the schema 5 base is MyISAM")

        with StatementLog() as log:
            run = run_ccdb(reader_url, "db upgrade --dry-run")
        self.assertTrue(run.ok, run.text())
        self.assertEqual(db.structure(with_charset=True), before)
        self.assertEqual(db.version(), 5)
        self.assertEqual(log.vault_reads(), [], "--duplicates none (the default) reads no vault")
        self.assertEqual(log.writes(), [])
        self.assertIn("myisam", run.output.lower())
        # §6.5 gives no format: a line outside the printed DDL names the table and carries a number. constantSets is
        # left out, since the count of sets to hash names it with a number whether or not sizes are printed
        numbered = lines_with_numbers(run.said())
        for table in myisam:
            if table == "constantSets":
                continue
            self.assertTrue(any(re.search(r"\b%s\b" % table, line) and re.search(r"\d", line) for line in numbered),
                            "MyISAM table {} listed with its size\n{}".format(table, run.text()))

        # a vault in a charset that can hold unmappable bytes: the round-trip check waits for the preflight (§3)
        charset, collation = db.query("SELECT CHARACTER_SET_NAME, COLLATION_NAME FROM information_schema.COLUMNS "
                                      "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'constantSets' "
                                      "AND COLUMN_NAME = 'vault'")[0]
        db.execute("ALTER TABLE `constantSets` MODIFY `vault` LONGTEXT CHARACTER SET cp1251 NOT NULL")
        lossy = db.structure(with_charset=True)
        with StatementLog() as log:
            run = run_ccdb(reader_url, "db upgrade --dry-run --duplicates none")
        self.assertTrue(run.ok, run.text())
        self.assertEqual(log.vault_reads(), [])
        self.assertIn("round-trip check pending", run.output.lower())
        self.assertEqual(db.structure(with_charset=True), lossy)
        # back to the base charset: the rest of this test is about privileges, not the §3 stops (T6)
        db.execute("ALTER TABLE `constantSets` MODIFY `vault` LONGTEXT CHARACTER SET %s COLLATE %s NOT NULL"
                   % (charset, collation))
        self.assertEqual(db.structure(with_charset=True), before)

        with StatementLog() as log:
            run = run_ccdb(reader_url, UPGRADE + " --no-transaction-check")
        self.assertFalse(run.ok, run.text())
        self.assertEqual(log.writes(), [], "the preflight refuses before any change")
        self.assertEqual(db.structure(with_charset=True), before)
        prose = "\n".join(prose_lines(run.said()))      # planned DDL would name ALTER, CREATE, INDEX and UPDATE anyway
        for privilege in ("ALTER", "CREATE", "INDEX", "INSERT", "UPDATE", "DELETE"):
            self.assertRegex(prose, r"(?i)\b%s\b" % privilege, "the refusal names the missing privileges\n" + run.text())

        if not db.has_process_privilege():
            # §14.1: without PROCESS the upgrade refuses unless --no-transaction-check; §6.2 item 3: the message says so
            with StatementLog() as log:
                run = run_ccdb(db.url, UPGRADE)
            self.assertFalse(run.ok, run.text())
            self.assertEqual(log.writes(), [])
            self.assertRegex(run.said(), r"(?i)\bPROCESS\b|no-transaction-check", run.text())
            self.assertEqual(db.structure(with_charset=True), before)

        run = run_ccdb(db.url, UPGRADE + " --no-transaction-check")
        self.assertTrue(run.ok, run.text())
        self.assertEqual(db.version(), 6)

    def test_preflight_open_transaction(self):
        """T22 (§6.2 item 3): as root an open transaction in another session refuses; an idle autocommit reader does not"""
        root_url = self.other_url_or_skip(ENV_MYSQL_ROOT)
        db = self.db
        db.build_v5()
        for (table,) in db.query("SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE()"):
            db.execute("ALTER TABLE `%s` ENGINE = InnoDB" % table)     # hallddb-shaped: transactions are InnoDB's
        before = db.structure(with_charset=True)

        engine = db.engine()
        try:
            holder = engine.connect()           # a 2.4 provider after one read: its transaction stays open
            try:
                holder.execute(text("SELECT `id` FROM `assignments` LIMIT 1")).fetchall()
                with StatementLog() as log:
                    run = run_ccdb(root_url, UPGRADE)
                self.assertFalse(run.ok, run.text())
                self.assertEqual(log.writes(), [], "the preflight refuses before any change")
                self.assertEqual(db.structure(with_charset=True), before)
            finally:
                holder.rollback()
                holder.close()
        finally:
            engine.dispose()
        time.sleep(0.5)     # information_schema.INNODB_TRX is a cache the server refreshes at most every 0.1 s

        engine = db.engine()
        try:
            idle = engine.connect().execution_options(isolation_level="AUTOCOMMIT")
            try:
                idle.execute(text("SELECT `id` FROM `assignments` LIMIT 1")).fetchall()
                run = run_ccdb(root_url, UPGRADE)
                self.assertTrue(run.ok, run.text())
                self.assertEqual(db.version(), 6)
            finally:
                idle.close()
        finally:
            engine.dispose()

    def test_rollback_refuses_non_strict(self):
        """T25 (§9): on a server whose global sql_mode is not strict rollback refuses unless --allow-non-strict"""
        root_url = self.other_url_or_skip(ENV_MYSQL_ROOT)
        db = self.db
        db.build_v5()
        self.upgrade()
        upgraded = db.structure(with_charset=True)
        root = MysqlDb(root_url)
        sql_mode = root.scalar("SELECT @@GLOBAL.sql_mode")
        try:
            root.execute("SET GLOBAL sql_mode = 'NO_ENGINE_SUBSTITUTION'")
            run = run_ccdb(db.url, ROLLBACK + db.no_tx_check)
            self.assertFalse(run.ok, run.text())
            self.assertEqual(db.version(), 6)
            self.assertEqual(db.structure(with_charset=True), upgraded)
            run = run_ccdb(db.url, ROLLBACK + " --allow-non-strict" + db.no_tx_check)
            self.assertTrue(run.ok, run.text())
            self.assertEqual(db.version(), 5)
        finally:
            root.execute("SET GLOBAL sql_mode = :mode", {"mode": sql_mode})


if __name__ == "__main__":
    unittest.main()
