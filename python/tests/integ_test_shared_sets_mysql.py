"""Schema 6 shared constant sets on MySQL and MariaDB: failures and races of the write path.

These tests pin rows T16 (its MySQL twin) and T18 (its server parts) of the test matrix in
space-ccdb-2.5/notes/schema6.md, section 14, written before the feature exists: every test fails today.
Section 14.1 ("test modules") places the T16 MySQL twin and the T18 server races in this new module, since
existing test files stay unchanged until their item. The exception classes and exit codes the tests expect
are the ones section 14.1 settles.

Needs CCDB_TEST_MYSQL_CONNECTION and is skipped when it is unset. Every test re-initializes the database
it names: it drops the CCDB tables, then builds either a fresh schema 6 database with `ccdb db init` or
the frozen schema 5 base (schema_v5_base.py) with duplicate sets, upgraded with `ccdb db upgrade`. Never
point the variable at a database you need.

The races are made deterministic with SQLAlchemy engine events on the provider under test: a hook stops
one side at a named statement until the other side has finished, or for PAUSE_SECONDS. An implementation
that takes the locks of §5.1 and §5.2 holds them during that pause, so the other side waits for it; one
that does not lets the other side finish inside the pause, and the stopped side then writes an
assignment whose set or table is gone, which the orphan check reports.

`db upgrade` and `db dedup` get `--no-transaction-check`: the test user `ccdb_user` lacks PROCESS
(T22), and in a race the other session's open transaction is the point of the test.
"""
import os
import re
import sys
import threading
import time
import traceback
import unittest
from io import StringIO

from sqlalchemy import event, text
from sqlalchemy.exc import DBAPIError, OperationalError, PendingRollbackError

import ccdb.cmd.themes
from ccdb import AlchemyProvider
from ccdb import testing as helper
from ccdb.cmd.cli_manager import CliManager, CCDB_EXCEPTIONS_THROW
from ccdb.cmd.utility_argument_parser import ArgumentParseError
from ccdb.errors import ObjectIsNotFoundInDbError
from ccdb.model import RunRange, list_to_blob, gen_flatten_data

# Have to import it this way as tests may be considered a package or not depending on context
try:
    from . import schema_v5_base
except ImportError:
    import schema_v5_base


MYSQL_URL = os.environ.get(helper.ENV_TEST_MYSQL, "")

PAUSE_SECONDS = 3.0      # how long a stopped side waits for the other one to finish
JOIN_SECONDS = 120       # longer than innodb_lock_wait_timeout (50 s by default)
DEADLOCK = 1213          # ER_LOCK_DEADLOCK
LOCK_WAIT_TIMEOUT = 1205
NO_SUCH_TABLE = 1146     # ER_NO_SUCH_TABLE: what _break_statement makes the server raise

TEST_TABLE = "/test/test_vars/test_table"                     # seed table 1: 2 rows, 3 columns
SEED_SET_4_ROWS = [["2.2", "2.3", "2.4"], ["2.5", "2.6", "2.7"]]
EXISTING_RUN_RANGE = (0, 2000)                               # seed run range 3

DEDUP = "db dedup --dedup-i-am-sure --no-transaction-check"
UPGRADE = "db upgrade --upgrade-i-am-sure --no-transaction-check"

WEIGHT_TABLE = "t18_deadlock_weight"   # scratch table that makes the blocking session the heavier one

# Every table a schema 5 or schema 6 database may hold, dropped before a test builds its database
CCDB_TABLES = list(schema_v5_base.mysql_tables) + ["timeRanges", "properties", "variations_has_tags", WEIGHT_TABLE]

# Schema 5 additions for the upgraded database: set 6 holds the bytes of seed set 4 (same table), and
# assignment 6 uses it, so `db dedup` merges set 6 into set 4 and repoints assignment 6
DUPLICATE_ROWS_V5 = [
    "INSERT INTO `constantSets` (`id`, `created`, `modified`, `vault`, `constantTypeId`) "
    "VALUES (6, '2013-01-01 00:00:00', '2013-01-01 00:00:00', '2.2|2.3|2.4|2.5|2.6|2.7', 1)",
    "INSERT INTO `assignments` (`id`, `created`, `modified`, `variationId`, `runRangeId`, `eventRangeId`, "
    "`authorId`, `comment`, `constantSetId`) "
    "VALUES (6, '2013-01-01 00:00:00', '2013-01-01 00:00:00', 1, 1, NULL, 2, 'Duplicate of set 4', 6)",
]

ORPHAN_ASSIGNMENTS_SQL = """
    SELECT a.id, a.`constantSetId`, s.`constantTypeId`
    FROM assignments a
    LEFT JOIN `constantSets` s ON s.id = a.`constantSetId`
    LEFT JOIN `typeTables` t ON t.id = s.`constantTypeId`
    WHERE s.id IS NULL OR t.id IS NULL
    ORDER BY a.id"""


def _statement(pattern):
    return re.compile(pattern, re.IGNORECASE | re.DOTALL)


# Statements the hooks wait at. MySQL quotes the camelCase names with backticks
INSERT_ASSIGNMENT = _statement(r"\s*INSERT\s+INTO\s+`?assignments`?[\s(]")
INSERT_LOG = _statement(r"\s*INSERT\s+INTO\s+`?logs`?[\s(]")
SELECT_SETS = _statement(r"\s*SELECT\b.*\bFROM\s+`?constantSets`?(\s|$)")
DELETE_TYPE_TABLE = _statement(r"\s*DELETE\s+FROM\s+`?typeTables`?[\s(]")
SHARE_LOCK_TYPE_TABLE = _statement(r"\s*SELECT\b.*\bFROM\s+`?typeTables`?\s.*\b(FOR\s+SHARE|LOCK\s+IN\s+SHARE\s+MODE)\b")
UPDATE_LOCK_TYPE_TABLE = _statement(r"\s*SELECT\b.*\bFROM\s+`?typeTables`?\s.*\bFOR\s+UPDATE\b")


def _mysql_code(error):
    """MySQL error number of a DBAPI error, raw or wrapped by SQLAlchemy; None for anything else"""
    original = getattr(error, "orig", None) or error
    args = getattr(original, "args", None) or ()
    if args and isinstance(args[0], int):
        return args[0]
    return None


def _on_first(engine, when, pattern, callback):
    """Calls callback() in the executing thread the first time the engine runs a matching statement.

    when is "before_cursor_execute" (the statement has not run yet) or "after_cursor_execute"
    (it has run, so the locks it took are held).
    """
    fired = []

    def listener(conn, cursor, statement, parameters, context, executemany):
        if not fired and pattern.match(statement):
            fired.append(statement)
            callback()

    event.listen(engine, when, listener)


def _break_statement(engine, pattern, table_name):
    """Points every matching statement at a missing table, so the server fails it with error 1146"""
    def listener(conn, cursor, statement, parameters, context, executemany):
        if pattern.match(statement):
            statement = statement.replace(table_name, table_name + "_missing_t16", 1)
        return statement, parameters

    event.listen(engine, "before_cursor_execute", listener, retval=True)
    return listener


def _pause(reached, until):
    """Hook action: tell the test the point is reached, then wait for the other side or the pause"""
    def action():
        reached.set()
        until.wait(PAUSE_SECONDS)
    return action


def _wait_quietly(barrier, broken):
    """Hook action: wait at the barrier; a broken barrier is recorded, not raised inside the provider"""
    def action():
        try:
            barrier.wait()
        except threading.BrokenBarrierError:
            broken.append(True)
    return action


class _Worker(threading.Thread):
    """Runs fn in a daemon thread and keeps its result or its exception for the test thread"""

    def __init__(self, name, fn, done=None):
        threading.Thread.__init__(self, name=name, daemon=True)
        self.fn = fn
        self.done = done if done is not None else threading.Event()
        self.result = None
        self.error = None
        self.error_trace = ""

    def run(self):
        try:
            self.result = self.fn()
        except BaseException as ex:  # reported by the test thread
            self.error = ex
            self.error_trace = traceback.format_exc()
        finally:
            self.done.set()


@unittest.skipUnless(MYSQL_URL, "CCDB_TEST_MYSQL_CONNECTION is not set")
class SharedSetsMySQLTest(unittest.TestCase):
    """T16 twin and T18 of notes/schema6.md on the server CCDB_TEST_MYSQL_CONNECTION names"""

    def setUp(self):
        # cleanups, unlike tearDown, also run when setUp fails, so stdout is always restored
        self._providers = []
        self.output = StringIO()
        self.saved_stdout = sys.stdout
        sys.stdout = self.output
        self.addCleanup(setattr, sys, "stdout", self.saved_stdout)

        # raw SQL for building and checking the database; never holds a transaction between calls
        self.checker = AlchemyProvider()
        self._providers.append(self.checker)
        self.addCleanup(self._disconnect_all)
        self.checker.connect(MYSQL_URL, check_version=False)
        self.engine = self.checker.engine

    def _disconnect_all(self):
        for provider in self._providers:
            try:
                if provider.is_connected:
                    provider.disconnect()
            except Exception as ex:
                self.saved_stdout.write("cleanup: disconnect raised {0!r}\n".format(ex))

    # ------------------------------------------------------------------------------------------
    #   building the database
    # ------------------------------------------------------------------------------------------
    def _cli(self, command_line):
        """Runs one ccdb command in-process on a fresh CliManager, as integ_test_cli_manager does"""
        cli = CliManager()
        cli.exception_handling = CCDB_EXCEPTIONS_THROW
        cli.force_exceptions = True
        cli.theme = ccdb.cmd.themes.NoColorTheme()
        cli.connection_string = MYSQL_URL
        cli.context.user_name = "test_user"
        cli.register_utilities()
        try:
            return cli.process_command_line(command_line)
        finally:
            if cli.provider.is_connected:
                cli.provider.disconnect()

    def _cli_ok(self, command_line):
        """Runs the command and requires exit 0: ccdb exits 1 when a command returns None or False
        (ccdb/__init__.py), and db upgrade and db dedup exit 1 only on a refusal or a collision (§14.1)"""
        result = self._cli(command_line)
        self.assertFalse(result is None or result is False,
                         "'ccdb {0}' returned {1!r}, which exits 1. Output:\n{2}"
                         .format(command_line, result, self.output.getvalue()[-3000:]))
        return result

    def _drop_tables(self):
        with self.engine.begin() as connection:
            for name in CCDB_TABLES:
                connection.execute(text("DROP TABLE IF EXISTS `{0}`".format(name)))

    def _fresh_v6(self):
        """A fresh database from `ccdb db init`: schema 6 with the unique index (§2.3)"""
        self._drop_tables()
        self._cli_ok("db init --init-i-am-sure")

    def _upgraded_with_duplicates(self):
        """Frozen schema 5 plus a duplicate of set 4, upgraded: schema 6 with the interim index (§2.3)"""
        self._drop_tables()
        schema_v5_base.create_v5_mysql(self.engine)
        with self.engine.begin() as connection:
            for statement in DUPLICATE_ROWS_V5:
                connection.execute(text(statement))
        self._cli_ok(UPGRADE)       # no prompt: --upgrade-i-am-sure is the confirmation (§14.1 "confirmation")
        self.assertEqual(self._scalars("SELECT `schemaVersion` FROM `schemaVersions`"), [6])
        self.assertEqual(self._index("ix_constantSets_table_sha256"), [(1, "constantTypeId"), (1, "sha256")],
                         "an upgraded database with duplicates has the interim index (§2.3)")
        self.assertEqual(self._index("uq_constantSets_table_sha256"), [],
                         "the unique index waits for dedup while duplicates exist (§2.3)")

    def _provider(self, logging_enabled=True):
        """A provider of its own, connected in the calling thread, as test_user"""
        provider = AlchemyProvider()
        provider.connect(MYSQL_URL)
        provider.authentication.current_user_name = "test_user"
        provider.logging_enabled = logging_enabled
        self._providers.append(provider)
        return provider

    def _worker_body(self, fn):
        """Thread body: fn(provider) on a provider of its own, disconnected when fn returns or raises.

        A session left in a transaction holds metadata locks, which would block the DDL of a later
        `db dedup` (its CREATE UNIQUE INDEX) or `db init`.
        """
        def body():
            provider = self._provider()
            try:
                return fn(provider)
            finally:
                try:
                    provider.disconnect()
                except Exception as ex:   # the result or the error of fn is what the test needs
                    self.output.write("disconnect in {0} raised {1!r}\n".format(threading.current_thread().name, ex))
        return body

    def _make_table(self, provider, name):
        """A table of one row and two double columns under /test/test_vars, without assignments"""
        provider.create_type_table(name, "/test/test_vars", 1, [("a", "double"), ("b", "double")], "T18 race table")
        return "/test/test_vars/" + name

    def _unused_set(self, provider, path, rows):
        """Creates an assignment and removes it again; returns the id of the set that stays (§5.2)"""
        assignment = provider.create_assignment(rows, path, EXISTING_RUN_RANGE[0], EXISTING_RUN_RANGE[1],
                                                "default", "removed again")
        set_id = assignment.constant_set_id
        provider.delete_assignment(assignment)
        self.assertTrue(self._set_exists(set_id),
                        "rm -a deleted constant set {0}; in schema 6 deleting an assignment never deletes "
                        "its set (§5.2, Assignment.constant_set without cascade, §4.1)".format(set_id))
        return set_id

    # ------------------------------------------------------------------------------------------
    #   reading the database
    # ------------------------------------------------------------------------------------------
    def _rows(self, sql, **params):
        with self.engine.connect() as connection:
            return [tuple(row) for row in connection.execute(text(sql), params)]

    def _scalars(self, sql, **params):
        return [row[0] for row in self._rows(sql, **params)]

    def _row_counts(self):
        """Row count of every table of the database"""
        names = self._scalars("SELECT TABLE_NAME FROM information_schema.TABLES "
                              "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_TYPE = 'BASE TABLE' ORDER BY TABLE_NAME")
        return {name: self._scalars("SELECT COUNT(*) FROM `{0}`".format(name))[0] for name in names}

    def _index(self, name):
        """(NON_UNIQUE, column) of the constantSets index `name`, in index order; [] when it is missing"""
        return [(int(non_unique), column) for non_unique, column in self._rows(
            "SELECT NON_UNIQUE, COLUMN_NAME FROM information_schema.STATISTICS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'constantSets' AND INDEX_NAME = :name "
            "ORDER BY SEQ_IN_INDEX", name=name)]

    def _assert_unique_index(self):
        self.assertEqual(self._index("uq_constantSets_table_sha256"), [(0, "constantTypeId"), (0, "sha256")],
                         "constantSets has no UNIQUE INDEX uq_constantSets_table_sha256 (constantTypeId, sha256) "
                         "(§2.1, §2.3)")

    def _set_exists(self, set_id):
        return bool(self._scalars("SELECT COUNT(*) FROM `constantSets` WHERE id = :id", id=set_id)[0])

    def _vault(self, set_id):
        vaults = self._scalars("SELECT vault FROM `constantSets` WHERE id = :id", id=set_id)
        return vaults[0] if vaults else None

    def _set_of(self, assignment_id):
        return self._scalars("SELECT `constantSetId` FROM assignments WHERE id = :id", id=assignment_id)[0]

    def _table_id(self, name):
        return self._scalars("SELECT id FROM `typeTables` WHERE name = :name", name=name)[0]

    def _sets_of_table(self, table_id):
        """(id, vault) of every set of the table, by id"""
        return self._rows("SELECT id, vault FROM `constantSets` WHERE `constantTypeId` = :table ORDER BY id",
                          table=table_id)

    def _assert_no_orphans(self):
        orphans = self._rows(ORPHAN_ASSIGNMENTS_SQL)
        self.assertEqual(orphans, [],
                         "assignments left without their set or table, as (assignment, set, table): {0} (T18)"
                         .format(orphans))

    # ------------------------------------------------------------------------------------------
    #   threads
    # ------------------------------------------------------------------------------------------
    def _join(self, *workers):
        for worker in workers:
            worker.join(JOIN_SECONDS)
            self.assertFalse(worker.is_alive(),
                             "{0} still runs after {1} s: a lock wait that never ends".format(worker.name, JOIN_SECONDS))

    def _wait_for(self, reached, worker, what):
        """Waits until the worker's hook reports `what`, failing when the worker ends before it"""
        deadline = time.monotonic() + JOIN_SECONDS
        while not reached.wait(0.05):
            if worker.done.is_set():
                self.fail("{0} ended before {1}, so the race did not happen. {2}"
                          .format(worker.name, what, self._error_text(worker) if worker.error else "No error."))
            if time.monotonic() > deadline:
                self.fail("{0} did not reach {1} within {2} s".format(worker.name, what, JOIN_SECONDS))

    @staticmethod
    def _error_text(worker):
        error = worker.error
        code = _mysql_code(error)
        if code in (DEADLOCK, LOCK_WAIT_TIMEOUT):
            why = "MySQL error {0} escaped; §5.1 step 3 rolls back and restarts the transaction".format(code)
        elif isinstance(error, PendingRollbackError):
            why = "the session was left in a failed transaction (F10); §5.1 step 3 rolls back"
        elif isinstance(error, ArgumentParseError):
            why = "the ccdb command does not know this subcommand or option (§10)"
        else:
            why = "unexpected error"
        return "{0}: {1}: {2!r}\n{3}".format(worker.name, why, error, worker.error_trace)

    def _assert_succeeded(self, worker, cli=False):
        if worker.error is not None:
            self.fail(self._error_text(worker))
        if cli:
            self.assertFalse(worker.result is None or worker.result is False,
                             "{0} returned {1!r}, which exits 1. Output:\n{2}"
                             .format(worker.name, worker.result, self.output.getvalue()[-3000:]))

    def _assert_one_side_won(self, creator, remover):
        """create_assignment against rm -t: exactly one succeeds, the other refuses with the class §14.1 names"""
        self.assertEqual([creator.error is None, remover.error is None].count(True), 1,
                         "exactly one of create_assignment and rm -t succeeds.\ncreate_assignment: {0!r}\n"
                         "rm -t: {1!r}\n{2}{3}".format(creator.error, remover.error,
                                                       creator.error_trace, remover.error_trace))
        if creator.error is None:
            # rm -t of a table with assignments raises ValueError, as in 2.4 (§5.2, §14.1 "errors")
            loser, refusal = remover, ValueError
        else:
            # a table removed under a writer raises ObjectIsNotFoundInDbError (§5.1 step 0, §14.1 "errors")
            loser, refusal = creator, ObjectIsNotFoundInDbError
        if not isinstance(loser.error, refusal) or _mysql_code(loser.error) is not None:
            self.fail(self._error_text(loser))

    # ------------------------------------------------------------------------------------------
    #   T16: a failed create_assignment writes nothing (MySQL twin)
    # ------------------------------------------------------------------------------------------
    def test_failure_in_step_e_writes_nothing(self):
        """T16 (§5.1 steps 3-4, D22): a server error in step e, with an existing run range, writes no row; the provider stays usable"""
        self._fresh_v6()
        provider = self._provider()
        provider.get_run_range(*EXISTING_RUN_RANGE)
        rows = [["7.1", "7.2", "7.3"], ["7.4", "7.5", "7.6"]]
        before = self._row_counts()

        listener = _break_statement(provider.engine, INSERT_ASSIGNMENT, "assignments")
        try:
            with self.assertRaises(DBAPIError) as raised:
                provider.create_assignment(rows, TEST_TABLE, EXISTING_RUN_RANGE[0], EXISTING_RUN_RANGE[1],
                                           "default", "T16 step e")
        finally:
            event.remove(provider.engine, "before_cursor_execute", listener)
        # the injected error itself, re-raised (§5.1 step 3); identified by its server code, never its text
        self.assertEqual(_mysql_code(raised.exception), NO_SUCH_TABLE, repr(raised.exception))
        self.assertEqual(self._row_counts(), before,
                         "a failure in step e left rows behind; create_assignment is one transaction (§5.1)")

        assignment = provider.create_assignment(rows, TEST_TABLE, EXISTING_RUN_RANGE[0], EXISTING_RUN_RANGE[1],
                                                "default", "T16 after the failure")
        self.assertEqual(assignment.constant_set.data_table, rows)
        after = self._row_counts()
        self.assertEqual(after["assignments"], before["assignments"] + 1)
        self.assertEqual(after["constantSets"], before["constantSets"] + 1)
        self._assert_no_orphans()

    def test_failure_in_step_f_writes_nothing(self):
        """T16 (§5.1 steps 3-4, §5.3, D22): a server error in the log record of step f writes no row; the provider stays usable"""
        self._fresh_v6()
        provider = self._provider(logging_enabled=True)
        provider.get_run_range(*EXISTING_RUN_RANGE)
        rows = [["8.1", "8.2", "8.3"], ["8.4", "8.5", "8.6"]]
        before = self._row_counts()

        listener = _break_statement(provider.engine, INSERT_LOG, "logs")
        try:
            with self.assertRaises(DBAPIError) as raised:
                provider.create_assignment(rows, TEST_TABLE, EXISTING_RUN_RANGE[0], EXISTING_RUN_RANGE[1],
                                           "default", "T16 step f")
        finally:
            event.remove(provider.engine, "before_cursor_execute", listener)
        # step f flushes the log record, so its failure surfaces before the commit (§14.1 "step f")
        self.assertEqual(_mysql_code(raised.exception), NO_SUCH_TABLE, repr(raised.exception))
        self.assertEqual(self._row_counts(), before,
                         "a failure in step f left rows behind; the log record is inside the data transaction (§5.3)")

        assignment = provider.create_assignment(rows, TEST_TABLE, EXISTING_RUN_RANGE[0], EXISTING_RUN_RANGE[1],
                                                "default", "T16 after the failure")
        self.assertEqual(assignment.constant_set.data_table, rows)
        after = self._row_counts()
        self.assertEqual(after["assignments"], before["assignments"] + 1)
        self.assertEqual(after["constantSets"], before["constantSets"] + 1)
        self.assertEqual(after["logs"], before["logs"] + 1)

    def test_pending_changes_refuse(self):
        """T16 (§5.1 step 3.0): pending changes in the provider's session make create_assignment refuse and write nothing"""
        self._fresh_v6()
        try:
            from ccdb.errors import SessionHasPendingChangesError   # new in schema 6 (§4.1, §14.1)
        except ImportError:
            self.fail("ccdb.errors has no SessionHasPendingChangesError (§4.1, §14.1 'pending session changes')")
        provider = self._provider()
        rows = [["9.1", "9.2", "9.3"], ["9.4", "9.5", "9.6"]]
        pending = RunRange()
        pending.min, pending.max, pending.name, pending.comment = 7000, 7001, "", "T16 pending change"
        provider.session.add(pending)       # in session.new; autoflush has not run since (no query on this session)
        before = self._row_counts()

        # §14.1: the check runs first, before any validation read, which would autoflush the run range
        with self.assertRaises(SessionHasPendingChangesError):
            provider.create_assignment(rows, TEST_TABLE, EXISTING_RUN_RANGE[0], EXISTING_RUN_RANGE[1],
                                       "default", "T16 pending")
        self.assertEqual(self._row_counts(), before)
        self.assertEqual(self._scalars("SELECT COUNT(*) FROM `runRanges` WHERE `runMin` = 7000")[0], 0,
                         "create_assignment committed the caller's pending run range")

        provider.session.rollback()        # the caller discards the change; then the call works
        assignment = provider.create_assignment(rows, TEST_TABLE, EXISTING_RUN_RANGE[0], EXISTING_RUN_RANGE[1],
                                                "default", "T16 after discarding")
        self.assertEqual(assignment.constant_set.data_table, rows)

    # ------------------------------------------------------------------------------------------
    #   T18: two writers of the same bytes
    # ------------------------------------------------------------------------------------------
    def test_insert_race(self):
        """T18 (§5.1 step d, §2.3): two sessions storing the same bytes at once get one set, unique index present"""
        self._fresh_v6()
        self._assert_unique_index()
        from ccdb.model import vault_digest   # new in schema 6 (§4.1)
        table_id = self._table_id("test_table")

        for round_no in range(3):
            rows = [["{0}.101".format(round_no), "{0}.102".format(round_no), "{0}.103".format(round_no)],
                    ["{0}.104".format(round_no), "{0}.105".format(round_no), "{0}.106".format(round_no)]]
            vault = list_to_blob(list(gen_flatten_data(rows)))
            start = threading.Barrier(2, timeout=30)
            after_lookup = threading.Barrier(2, timeout=10)  # both have looked for candidates (step b) before either inserts
            broken = []

            def insert(provider, label, rows=rows, start=start, after_lookup=after_lookup, broken=broken):
                _on_first(provider.engine, "after_cursor_execute", SELECT_SETS, _wait_quietly(after_lookup, broken))
                start.wait()
                assignment = provider.create_assignment(rows, TEST_TABLE, EXISTING_RUN_RANGE[0],
                                                        EXISTING_RUN_RANGE[1], "default", label)
                return assignment.id

            workers = [_Worker("writer {0}".format(n), self._worker_body(
                lambda provider, n=n: insert(provider, "T18 insert race writer {0}".format(n)))) for n in (1, 2)]
            for worker in workers:
                worker.start()
            self._join(*workers)
            for worker in workers:
                self._assert_succeeded(worker)
            self.assertEqual(broken, [], "the two sessions did not both look up candidates before inserting, "
                                         "round {0}".format(round_no))

            set_ids = {self._set_of(worker.result) for worker in workers}
            self.assertEqual(len(set_ids), 1, "two sessions stored the same bytes as two sets {0}; the loser of the "
                                              "unique index reuses the winner's set (§5.1 d)".format(sorted(set_ids)))
            equal = [set_id for set_id, stored in self._sets_of_table(table_id) if stored == vault]
            self.assertEqual(equal, list(set_ids))
            stored = self._rows("SELECT sha256, size FROM `constantSets` WHERE id = :id", id=equal[0])[0]
            self.assertEqual(stored, vault_digest(vault))
        self._assert_no_orphans()

    def test_deadlock_restarts_create_assignment(self):
        """T18 (§5.1 step 3): create_assignment chosen as deadlock victim (MySQL 1213) restarts and succeeds"""
        self._fresh_v6()
        engines = dict(self._rows("SELECT TABLE_NAME, ENGINE FROM information_schema.TABLES "
                                  "WHERE TABLE_SCHEMA = DATABASE() "
                                  "AND TABLE_NAME IN ('assignments', 'constantSets', 'typeTables')"))
        self.assertEqual(engines, {"assignments": "InnoDB", "constantSets": "InnoDB", "typeTables": "InnoDB"},
                         "every table becomes InnoDB (§1, §3); row locks and deadlocks need it")
        table_id = self._table_id("test_table")
        seed_vault = list_to_blob(list(gen_flatten_data(SEED_SET_4_ROWS)))
        candidate = [set_id for set_id, stored in self._sets_of_table(table_id) if stored == seed_vault][0]

        with self.engine.begin() as connection:
            connection.execute(text("CREATE TABLE `{0}` (id INT NOT NULL AUTO_INCREMENT PRIMARY KEY, n INT NOT NULL) "
                                    "ENGINE = InnoDB".format(WEIGHT_TABLE)))
        self.addCleanup(self._drop_weight_table)

        deadlocks = []
        table_locked = threading.Event()

        def create(provider):
            _on_first(provider.engine, "after_cursor_execute", SHARE_LOCK_TYPE_TABLE, table_locked.set)
            event.listen(provider.engine, "handle_error",
                         lambda context: deadlocks.append(_mysql_code(context.original_exception)))
            assignment = provider.create_assignment(SEED_SET_4_ROWS, TEST_TABLE, EXISTING_RUN_RANGE[0],
                                                    EXISTING_RUN_RANGE[1], "default", "T18 deadlock victim")
            return assignment.id

        # The blocking session: heavier (many undo records), holds the candidate set, then asks for the
        # table row that create_assignment holds in share mode since step 0 -> a deadlock cycle. InnoDB
        # rolls back the lighter transaction (probed on MySQL 8.3 and MariaDB 10.5)
        blocker = self.engine.connect()
        creator = _Worker("create_assignment", self._worker_body(create))
        try:
            blocker.execute(text("INSERT INTO `{0}` (n) VALUES {1}".format(
                WEIGHT_TABLE, ", ".join("({0})".format(n) for n in range(2000)))))
            blocker.execute(text("SELECT id FROM `constantSets` WHERE id = :id FOR UPDATE"), {"id": candidate}).fetchall()
            creator.start()
            self._wait_for(table_locked, creator, "the share lock of its typeTables row (§5.1 step 0)")
            try:
                blocker.execute(text("SELECT id FROM `typeTables` WHERE id = :id FOR UPDATE"), {"id": table_id}).fetchall()
            except OperationalError as ex:
                if _mysql_code(ex) == DEADLOCK:
                    self.fail("the blocking session became the deadlock victim instead of create_assignment; "
                              "the scenario needs more weight in {0}".format(WEIGHT_TABLE))
                raise
        finally:
            blocker.rollback()
            blocker.close()
        self._join(creator)
        self._assert_succeeded(creator)
        self.assertIn(DEADLOCK, deadlocks, "create_assignment never met the deadlock, so nothing was restarted")
        self.assertEqual(self._set_of(creator.result), candidate, "equal bytes reuse the existing set (§5.1 c)")
        self._assert_no_orphans()

    def _drop_weight_table(self):
        with self.engine.begin() as connection:
            connection.execute(text("DROP TABLE IF EXISTS `{0}`".format(WEIGHT_TABLE)))

    # ------------------------------------------------------------------------------------------
    #   T18: writers racing db dedup
    # ------------------------------------------------------------------------------------------
    def test_dedup_race_create_assignment_reuse(self):
        """T18 (§5.1 step c, §7 step 5): create_assignment reusing an unused set while db dedup deletes unused sets leaves no orphan"""
        self._fresh_v6()
        setup = self._provider()
        path = self._make_table(setup, "t18_reuse")
        rows = [["1.5", "2.5"]]
        unused = self._unused_set(setup, path, rows)
        setup.disconnect()
        vault = self._vault(unused)
        table_id = self._table_id("t18_reuse")

        reached, dedup_done = threading.Event(), threading.Event()

        def create(provider):
            _on_first(provider.engine, "before_cursor_execute", INSERT_ASSIGNMENT, _pause(reached, dedup_done))
            assignment = provider.create_assignment(rows, path, EXISTING_RUN_RANGE[0], EXISTING_RUN_RANGE[1],
                                                    "default", "T18 reuse races dedup")
            return assignment.id

        creator = _Worker("create_assignment", self._worker_body(create))
        deduper = _Worker("db dedup", lambda: self._cli(DEDUP), done=dedup_done)
        creator.start()
        self._wait_for(reached, creator, "its INSERT INTO assignments")
        deduper.start()
        self._join(creator, deduper)
        self._assert_succeeded(creator)
        self._assert_succeeded(deduper, cli=True)

        self._assert_no_orphans()
        self.assertEqual(self._vault(self._set_of(creator.result)), vault)
        self.assertEqual([set_id for set_id, stored in self._sets_of_table(table_id) if stored == vault],
                         [self._set_of(creator.result)])

    def test_dedup_race_copy_assignment(self):
        """T18 (§5.2 copy_assignment, §7 step 4): ccdb cp of an assignment whose set db dedup merges leaves no orphan"""
        self._upgraded_with_duplicates()
        vault = self._vault(6)
        reached, dedup_done = threading.Event(), threading.Event()

        def copy(provider):
            _on_first(provider.engine, "before_cursor_execute", INSERT_ASSIGNMENT, _pause(reached, dedup_done))
            source = provider.get_assignment_by_id(6)
            return provider.copy_assignment(source, new_variation="test", comment="T18 cp races dedup").id

        copier = _Worker("copy_assignment", self._worker_body(copy))
        deduper = _Worker("db dedup", lambda: self._cli(DEDUP), done=dedup_done)
        copier.start()
        self._wait_for(reached, copier, "its INSERT INTO assignments")
        deduper.start()
        self._join(copier, deduper)
        self._assert_succeeded(copier)
        self._assert_succeeded(deduper, cli=True)

        self._assert_no_orphans()
        for assignment_id in (6, copier.result):
            self.assertEqual(self._vault(self._set_of(assignment_id)), vault)

        # whatever the race left, the next dedup merges it and creates the unique index (§2.3, §7); the
        # index swap checks first, so a run that finds the unique index present succeeds (§14.1)
        self._cli_ok(DEDUP)
        self._assert_unique_index()
        self.assertEqual(self._index("ix_constantSets_table_sha256"), [])
        self.assertEqual(self._rows("SELECT `constantTypeId`, sha256, COUNT(*) FROM `constantSets` "
                                    "GROUP BY `constantTypeId`, sha256 HAVING COUNT(*) > 1"), [])
        self.assertEqual({self._set_of(6), self._set_of(copier.result)}, {4}, "the survivor is the smallest id (§7)")
        self._assert_no_orphans()

    def test_dedup_race_rm_t(self):
        """T18 (§5.2 delete_type_table, §7): rm -t of a table with unused sets while db dedup deletes them; both succeed, nothing is left"""
        self._fresh_v6()
        setup = self._provider()
        path = self._make_table(setup, "t18_rm_t")
        for n in range(3):
            self._unused_set(setup, path, [["{0}.25".format(n), "{0}.75".format(n)]])
        setup.disconnect()
        table_id = self._table_id("t18_rm_t")

        reached, dedup_done = threading.Event(), threading.Event()

        def remove(provider):
            _on_first(provider.engine, "before_cursor_execute", DELETE_TYPE_TABLE, _pause(reached, dedup_done))
            provider.delete_type_table(provider.get_type_table(path))
            return True

        remover = _Worker("rm -t", self._worker_body(remove))
        deduper = _Worker("db dedup", lambda: self._cli(DEDUP), done=dedup_done)
        remover.start()
        self._wait_for(reached, remover, "its DELETE FROM typeTables")
        deduper.start()
        self._join(remover, deduper)
        self._assert_succeeded(remover)
        self._assert_succeeded(deduper, cli=True)

        self.assertEqual(self._scalars("SELECT COUNT(*) FROM `typeTables` WHERE id = :id", id=table_id), [0])
        self.assertEqual(self._sets_of_table(table_id), [], "rm -t deletes the table's unused sets with it (Q39)")
        self._assert_no_orphans()

    # ------------------------------------------------------------------------------------------
    #   T18: create_assignment racing rm -t
    # ------------------------------------------------------------------------------------------
    def _race_create_and_rm_t(self, table_name, create_first):
        self._fresh_v6()
        setup = self._provider()
        path = self._make_table(setup, table_name)
        rows = [["3.5", "4.5"]]
        unused = self._unused_set(setup, path, rows)
        setup.disconnect()
        vault = self._vault(unused)
        table_id = self._table_id(table_name)

        reached = threading.Event()
        creator_done, remover_done = threading.Event(), threading.Event()

        def create(provider):
            if create_first:
                _on_first(provider.engine, "before_cursor_execute", INSERT_ASSIGNMENT, _pause(reached, remover_done))
            assignment = provider.create_assignment(rows, path, EXISTING_RUN_RANGE[0], EXISTING_RUN_RANGE[1],
                                                    "default", "T18 create races rm -t")
            return assignment.id

        def remove(provider):
            if not create_first:
                _on_first(provider.engine, "after_cursor_execute", UPDATE_LOCK_TYPE_TABLE, _pause(reached, creator_done))
            provider.delete_type_table(provider.get_type_table(path))
            return True

        creator = _Worker("create_assignment", self._worker_body(create), done=creator_done)
        remover = _Worker("rm -t", self._worker_body(remove), done=remover_done)
        first, second = (creator, remover) if create_first else (remover, creator)
        first.start()
        self._wait_for(reached, first, "its INSERT INTO assignments" if create_first
                       else "its FOR UPDATE lock of the typeTables row (§5.2)")
        second.start()
        self._join(creator, remover)

        self._assert_one_side_won(creator, remover)
        self._assert_no_orphans()
        if creator.error is None:
            self.assertEqual(self._scalars("SELECT COUNT(*) FROM `typeTables` WHERE id = :id", id=table_id), [1])
            self.assertEqual(self._vault(self._set_of(creator.result)), vault)
        else:
            self.assertEqual(self._scalars("SELECT COUNT(*) FROM `typeTables` WHERE id = :id", id=table_id), [0])
            self.assertEqual(self._sets_of_table(table_id), [], "rm -t deletes the table's unused sets with it (Q39)")

    def test_create_assignment_race_rm_t_create_first(self):
        """T18 (§5.1 step 0, §5.2): rm -t while create_assignment holds the table's share lock and reuses its unused set leaves no orphan"""
        self._race_create_and_rm_t("t18_create_first", create_first=True)

    def test_create_assignment_race_rm_t_rm_t_first(self):
        """T18 (§5.1 step 0, §5.2): create_assignment while rm -t holds the table's FOR UPDATE lock fails cleanly and writes nothing"""
        self._race_create_and_rm_t("t18_rm_t_first", create_first=False)


if __name__ == "__main__":
    unittest.main()
