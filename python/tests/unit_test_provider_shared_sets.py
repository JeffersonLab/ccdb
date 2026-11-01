"""Shared constant sets on schema 6: the write path of create_assignment and the commands around it.

Pins rows T14, T15, T16 (SQLite part), T17, T18 (SQLite part) and T19 of the test matrix in
space-ccdb-2.5/notes/schema6.md (section 14), with the behavior of sections 5.1 to 5.4.

Every test builds its own SQLite files in a temporary directory: a fresh database comes from
ccdb.sql.sqlite_schema.create_sqlite_database, which creates schema 6 once the schema files change;
the one upgraded database starts from the frozen schema 5 base (schema_v5_base.py) and goes through
`ccdb db upgrade`. Names that schema 6 adds (DataCollisionError, SessionHasPendingChangesError,
ccdb.model.vault_digest) are imported or patched inside the tests, so each test reports its own missing
feature. Exception classes, the collision log line, the step f flush and the exit codes follow the
contracts of section 14.1.
"""
import contextlib
import hashlib
import io
import os
import re
import sqlite3
import tempfile
import threading
import unittest
from unittest import mock

from sqlalchemy import create_engine, event, text

import ccdb
import ccdb.cmd.themes
from ccdb.cmd.cli_manager import CliManager, CCDB_EXCEPTIONS_THROW
from ccdb.model import Assignment, ConstantSet, LogRecord, RunRange
from ccdb.sql.sqlite_schema import create_sqlite_database

# Have to import it this way as tests may be considered a package or not depending on context
try:
    from . import schema_v5_base
except ImportError:
    import schema_v5_base


TABLE = "/test/test_vars/test_table"        # seed table 1: 2 rows, columns x y z (double)
TESTS_DIR = os.path.dirname(os.path.realpath(__file__))
SEED_SET_4_VAULT = "2.2|2.3|2.4|2.5|2.6|2.7"  # seed set 4 of table 1, used by assignment 4; equals test_table.txt
EXISTING_RUN_RANGE = (0, 1000)                # seed run range 4
VERS_HEADER = ("(ID)     (created)              (user)           (variation)     "
               "(run range)      (comments)")


class InjectedFailure(Exception):
    """Raised by a test hook to make one step of create_assignment fail"""


def sha256_hex(vault):
    """The identity of a set's data as section 1 defines it: hex SHA-256 of the UTF-8 bytes"""
    return hashlib.sha256(vault.encode("utf-8")).hexdigest()


def rows_of(vault, columns=3):
    """Rows of strings for create_assignment, so the stored vault is exactly the given text"""
    cells = vault.split("|")
    return [cells[i:i + columns] for i in range(0, len(cells), columns)]


class SharedSetsTestBase(unittest.TestCase):
    """Temporary SQLite files, providers and CLI managers on them, and raw reads through sqlite3"""

    def setUp(self):
        self._tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp_dir.cleanup)
        self._db_number = 0

    # databases
    def new_db_path(self, name="shared_sets"):
        self._db_number += 1
        return os.path.join(self._tmp_dir.name, "{}_{}.sqlite".format(name, self._db_number))

    def new_fresh_db(self):
        path = self.new_db_path("fresh")
        create_sqlite_database(path)
        return path

    def new_provider(self, path, logging_enabled=False):
        provider = ccdb.AlchemyProvider()
        provider.connect("sqlite:///" + path)
        provider.authentication.current_user_name = "test_user"
        provider.logging_enabled = logging_enabled
        self.addCleanup(provider.disconnect)
        return provider

    def fresh(self, logging_enabled=False):
        path = self.new_fresh_db()
        return path, self.new_provider(path, logging_enabled)

    # raw reads, which see only committed data
    @staticmethod
    def query(path, sql, params=()):
        connection = sqlite3.connect(path)
        try:
            return connection.execute(sql, params).fetchall()
        finally:
            connection.close()

    def row_counts(self, path):
        names = [row[0] for row in self.query(path, "SELECT name FROM sqlite_master WHERE type = 'table'")]
        return {name: self.query(path, 'SELECT COUNT(*) FROM "{}"'.format(name))[0][0] for name in names}

    def set_ids_of_table(self, path, table_id):
        return [row[0] for row in self.query(
            path, 'SELECT id FROM "constantSets" WHERE "constantTypeId" = ? ORDER BY id', (table_id,))]

    def set_exists(self, path, set_id):
        return bool(self.query(path, 'SELECT id FROM "constantSets" WHERE id = ?', (set_id,)))

    def set_id_of_assignment(self, path, assignment_id):
        rows = self.query(path, 'SELECT "constantSetId" FROM assignments WHERE id = ?', (assignment_id,))
        return rows[0][0] if rows else None

    def add_mapper_hook(self, cls, event_name, fn):
        event.listen(cls, event_name, fn)
        self.addCleanup(event.remove, cls, event_name, fn)

    # CLI, driven in-process as integ_test_cli_manager does
    def new_cli(self, path, log_sqlite=False):
        cli = CliManager()
        cli.exception_handling = CCDB_EXCEPTIONS_THROW
        cli.force_exceptions = True
        cli.theme = ccdb.cmd.themes.NoColorTheme()
        cli.connection_string = "sqlite:///" + path
        cli.context.user_name = "test_user"
        cli.log_sqlite = log_sqlite
        cli.register_utilities()
        self.addCleanup(cli.provider.disconnect)
        return cli

    @staticmethod
    def run_cli(cli, command_line):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            cli.process_command_line(command_line)
        return output.getvalue()

    def assert_cli_succeeds(self, cli, command_line):
        """Runs a command and checks it would exit 0: the ccdb entry point exits 1 when a command returns None or False"""
        with contextlib.redirect_stdout(io.StringIO()):
            result = cli.process_command_line(command_line)
        self.assertFalse(result is None or result is False,
                         "'{}' would exit 1 (section 14.1: 0 on success)".format(command_line))


class SharedSetsTest(SharedSetsTestBase):

    def test_reuse_rules(self):
        """T14, sections 5.1 and 2.3: reuse of equal bytes, distinct sets otherwise, smallest id, row lengths."""
        vault = "0.11|0.12|0.13|0.14|0.15|0.16"

        with self.subTest("same bytes twice: one set, two assignments"):
            path, provider = self.fresh()
            before = self.row_counts(path)
            first = provider.create_assignment(rows_of(vault), TABLE, 0, 1000, "default", "first")
            second = provider.create_assignment(rows_of(vault), TABLE, 0, 1000, "test", "second")
            self.assertNotEqual(first.id, second.id)
            self.assertEqual(self.set_id_of_assignment(path, first.id), self.set_id_of_assignment(path, second.id))
            after = self.row_counts(path)
            self.assertEqual(after["assignments"], before["assignments"] + 2)
            self.assertEqual(after["constantSets"], before["constantSets"] + 1)
            stored = self.query(path, 'SELECT vault, sha256, size FROM "constantSets" WHERE id = ?',
                                (first.constant_set_id,))
            self.assertEqual(stored, [(vault, sha256_hex(vault), len(vault.encode("utf-8")))])

        with self.subTest("bytes of a seed set reuse that set"):
            path, provider = self.fresh()
            reuser = provider.create_assignment(rows_of(SEED_SET_4_VAULT), TABLE, 0, 1000, "default", "same as 4")
            self.assertEqual(self.set_id_of_assignment(path, reuser.id), 4)

        with self.subTest("an unused set is a candidate"):
            path, provider = self.fresh()
            first = provider.create_assignment(rows_of(vault), TABLE, 0, 1000, "default", "first")
            set_id = first.constant_set_id
            provider.delete_assignment(first)
            self.assertTrue(self.set_exists(path, set_id))
            # other bytes in between, so a reused rowid cannot pass for a reused set
            provider.create_assignment(rows_of("9.1|9.2|9.3|9.4|9.5|9.6"), TABLE, 0, 1000, "default", "other")
            again = provider.create_assignment(rows_of(vault), TABLE, 0, 1000, "default", "again")
            self.assertEqual(self.set_id_of_assignment(path, again.id), set_id)

        with self.subTest("1.0 and 1.00: two sets, two hashes"):
            path, provider = self.fresh()
            short = provider.create_assignment(rows_of("1.0|2|3|4|5|6"), TABLE, 0, 1000, "default", "1.0")
            longer = provider.create_assignment(rows_of("1.00|2|3|4|5|6"), TABLE, 0, 1000, "default", "1.00")
            short_set = self.set_id_of_assignment(path, short.id)
            long_set = self.set_id_of_assignment(path, longer.id)
            self.assertNotEqual(short_set, long_set)
            hashes = dict(self.query(path, 'SELECT id, sha256 FROM "constantSets" WHERE id IN (?, ?)',
                                     (short_set, long_set)))
            self.assertEqual(hashes, {short_set: sha256_hex("1.0|2|3|4|5|6"),
                                      long_set: sha256_hex("1.00|2|3|4|5|6")})

        with self.subTest("same bytes in another table: two sets, one hash"):
            path, provider = self.fresh()
            twin = provider.create_type_table("twin_table", "/test/test_vars", 2,
                                              [("x", "double"), ("y", "double"), ("z", "double")], "same shape")
            in_table = provider.create_assignment(rows_of(vault), TABLE, 0, 1000, "default", "table 1")
            in_twin = provider.create_assignment(rows_of(vault), twin.path, 0, 1000, "default", "twin")
            table_set = self.set_id_of_assignment(path, in_table.id)
            twin_set = self.set_id_of_assignment(path, in_twin.id)
            self.assertNotEqual(table_set, twin_set)
            self.assertEqual(self.set_ids_of_table(path, twin.id), [twin_set])
            rows = self.query(path, 'SELECT "constantTypeId", sha256 FROM "constantSets" WHERE id IN (?, ?) ORDER BY id',
                              (table_set, twin_set))
            self.assertEqual(rows, [(1, sha256_hex(vault)), (twin.id, sha256_hex(vault))])

        with self.subTest("two equal sets under the interim index: the smallest id is reused"):
            path = self.new_db_path("upgraded")
            engine = create_engine("sqlite:///" + path)
            schema_v5_base.create_v5_sqlite(engine)
            duplicate = "7.1|7.2|7.3|7.4|7.5|7.6"
            with engine.begin() as connection:
                for set_id in (7, 6):   # the larger id first, so neither insertion order nor rowid decides
                    connection.execute(text(
                        'INSERT INTO "constantSets" (id, created, modified, vault, "constantTypeId") '
                        "VALUES (:id, '2013-01-01 00:00:00', '2013-01-01 00:00:00', :vault, 1)"),
                        {"id": set_id, "vault": duplicate})
                for assignment_id, set_id in ((6, 7), (7, 6)):
                    connection.execute(text(
                        "INSERT INTO assignments VALUES (:id, '2013-01-01 00:00:00', '2013-01-01 00:00:00', "
                        "1, 1, NULL, :set_id, 2, 'duplicate')"), {"id": assignment_id, "set_id": set_id})
            engine.dispose()
            cli = self.new_cli(path)
            self.assert_cli_succeeds(cli, "db upgrade --upgrade-i-am-sure")
            cli.provider.disconnect()
            indexes = [row[0] for row in self.query(
                path, "SELECT name FROM sqlite_master WHERE type = 'index' AND tbl_name = 'constantSets'")]
            self.assertIn("ix_constantSets_table_sha256", indexes)
            self.assertNotIn("uq_constantSets_table_sha256", indexes)
            provider = self.new_provider(path)
            reuser = provider.create_assignment(rows_of(duplicate), TABLE, 0, 1000, "default", "third")
            self.assertEqual(self.set_id_of_assignment(path, reuser.id), 6)

        with self.subTest("every row's length is checked and nothing is written"):
            path, provider = self.fresh()
            before = self.row_counts(path)
            for bad_rows in ([["1", "2", "3"], ["4", "5"]], [["1", "2", "3"], ["4", "5", "6", "7"]]):
                # section 14.1: a short or long row raises ValueError, as 2.4's first-row check does
                with self.assertRaises(ValueError):
                    provider.create_assignment(bad_rows, TABLE, 0, 4321, "default", "bad row length")
            self.assertEqual(self.row_counts(path), before)

    def test_collision_writes_nothing(self):
        """T15, section 5.1 step c: a stubbed hash collision raises DataCollisionError and writes nothing."""
        from ccdb.errors import DataCollisionError

        path, provider = self.fresh(logging_enabled=True)
        stored, colliding = "3.1|3.2|3.3|3.4|3.5|3.6", "3.1|3.2|3.3|3.4|3.5|3.7"
        fake_hash = "c0111de5" * 8

        def stub_digest(vault):
            data = vault.encode("utf-8")
            if vault in (stored, colliding):
                return fake_hash, len(data)
            return hashlib.sha256(data).hexdigest(), len(data)

        with contextlib.ExitStack() as stubs:
            stubs.enter_context(mock.patch("ccdb.model.vault_digest", side_effect=stub_digest))
            if hasattr(ccdb.provider, "vault_digest"):     # the provider may bind the name at import
                stubs.enter_context(mock.patch("ccdb.provider.vault_digest", side_effect=stub_digest))
            first = provider.create_assignment(rows_of(stored), TABLE, 0, 1000, "default", "stored")
            self.assertEqual(self.query(path, 'SELECT sha256 FROM "constantSets" WHERE id = ?',
                                        (first.constant_set_id,)), [(fake_hash,)])
            before = self.row_counts(path)
            # section 14.1: the collision "log line" is a Python logging error line and no database record,
            # so with logging on the logs table keeps its count too. Only the level is pinned, not the text.
            with self.assertLogs("ccdb", level="ERROR"), self.assertRaises(DataCollisionError):
                provider.create_assignment(rows_of(colliding), TABLE, 0, 9876, "default", "colliding")
        self.assertEqual(self.row_counts(path), before)
        self.assertEqual(provider.get_assignment_by_id(first.id).constant_set.vault, stored)

    def test_failure_writes_nothing(self):
        """T16, section 5.1 step 3: a failure in step e or f writes nothing, the provider stays usable; pending changes refuse."""
        vault = "4.1|4.2|4.3|4.4|4.5|4.6"
        min_run, max_run = EXISTING_RUN_RANGE

        def fail(mapper, connection, target):
            raise InjectedFailure("injected by the test")

        # section 14.1: the log record is flushed in step f, so its injected failure surfaces before the commit
        for step, failing_class in (("e", Assignment), ("f", LogRecord)):
            with self.subTest("failure in step " + step):
                path, provider = self.fresh(logging_enabled=True)
                before = self.row_counts(path)
                event.listen(failing_class, "before_insert", fail)
                try:
                    with self.assertRaises(InjectedFailure):
                        provider.create_assignment(rows_of(vault), TABLE, min_run, max_run, "default", "fails")
                finally:
                    event.remove(failing_class, "before_insert", fail)
                self.assertEqual(self.row_counts(path), before)

                # usable without a manual rollback; the retry writes exactly one set and one assignment
                assignment = provider.create_assignment(rows_of(vault), TABLE, min_run, max_run, "default", "works")
                self.assertEqual(provider.get_assignment_by_id(assignment.id).constant_set.vault, vault)
                after = self.row_counts(path)
                self.assertEqual(after["assignments"], before["assignments"] + 1)
                self.assertEqual(after["constantSets"], before["constantSets"] + 1)
                self.assertEqual(after["runRanges"], before["runRanges"])

        def make_dirty(provider):
            provider.get_type_table(TABLE).comment = "pending edit"

        def make_new(provider):
            run_range = RunRange()
            run_range.min, run_range.max, run_range.name, run_range.comment = 5, 6, "", "pending"
            provider.session.add(run_range)

        def make_deleted(provider):
            provider.session.delete(provider.get_run_range(0, 2000))

        # section 14.1: create_assignment checks pending changes first, before any validation read (whose
        # autoflush would write them), and raises SessionHasPendingChangesError; the caller's edit stays uncommitted
        for kind, make_pending in (("dirty", make_dirty), ("new", make_new), ("deleted", make_deleted)):
            with self.subTest("pending " + kind + " object makes the call refuse"):
                from ccdb.errors import SessionHasPendingChangesError

                path, provider = self.fresh()
                before = self.row_counts(path)
                make_pending(provider)
                with self.assertRaises(SessionHasPendingChangesError):
                    provider.create_assignment(rows_of(vault), TABLE, min_run, max_run, "default", "refused")
                self.assertEqual(self.row_counts(path), before)
                self.assertEqual(self.query(path, 'SELECT comment FROM "typeTables" WHERE id = 1'), [("Test type",)])
                provider.session.rollback()     # the caller discards its changes, then the call works
                provider.create_assignment(rows_of(vault), TABLE, min_run, max_run, "default", "after discard")
                self.assertEqual(self.row_counts(path)["assignments"], before["assignments"] + 1)

        with self.subTest("a read that changes nothing is not a pending change"):
            # get_assignment_by_id points the table at the cached directory: on a fresh provider TypeTable 1
            # lands in session.dirty with session.is_modified() False. Sections 5.1 step 3.0 and 14.1 refuse
            # pending changes, and this read made none, so the call must not refuse.
            path, provider = self.fresh()
            before = self.row_counts(path)
            provider.get_assignment_by_id(4)
            provider.create_assignment(rows_of(vault), TABLE, min_run, max_run, "default", "after a read")
            self.assertEqual(self.row_counts(path)["assignments"], before["assignments"] + 1)

    def test_rm_a_of_one_sharer_keeps_set(self):
        """T17, section 5.2: rm -a of one of two sharers keeps the set for the other."""
        path, provider = self.fresh()
        newer = provider.create_assignment(rows_of(SEED_SET_4_VAULT), TABLE, 0, 1000, "default", "same as 4")
        self.assertEqual(self.set_id_of_assignment(path, newer.id), 4)

        provider.delete_assignment(provider.get_assignment_by_id(4))     # the older sharer goes
        self.assertTrue(self.set_exists(path, 4))
        self.assertEqual(self.set_id_of_assignment(path, 4), None)
        self.assertEqual(self.set_id_of_assignment(path, newer.id), 4)
        reader = self.new_provider(path)
        self.assertEqual(reader.get_assignment_by_id(newer.id).constant_set.vault, SEED_SET_4_VAULT)

    def test_copy_then_delete_either_sharer(self):
        """T17, section 5.2: after cp, rm -a of the copy or of the source works and the other keeps the data."""
        for deleted in ("copy", "source"):
            with self.subTest("delete the " + deleted):
                path, provider = self.fresh()
                before = self.row_counts(path)
                # the read leaves TypeTable 1 in session.dirty with no net change, as `ccdb cp -a` does;
                # section 5.2 gives copy_assignment no pending-change refusal
                source = provider.get_assignment_by_id(4)
                copy = provider.copy_assignment(source, comment="copy of 4")
                self.assertEqual(self.set_id_of_assignment(path, copy.id), 4)
                self.assertEqual(self.row_counts(path)["constantSets"], before["constantSets"])

                gone, kept = (copy, source) if deleted == "copy" else (source, copy)
                gone_id, kept_id = gone.id, kept.id
                provider.delete_assignment(gone)
                self.assertEqual(self.set_id_of_assignment(path, gone_id), None)
                self.assertEqual(self.set_id_of_assignment(path, kept_id), 4)
                self.assertTrue(self.set_exists(path, 4))
                reader = self.new_provider(path)
                self.assertEqual(reader.get_assignment_by_id(kept_id).constant_set.vault, SEED_SET_4_VAULT)

    def test_rm_t_after_rm_a_of_all(self):
        """T17, section 5.2 (Q39): rm -t refuses while assignments exist; after rm -a of all it deletes the table and its unused sets."""
        path, provider = self.fresh()
        table = provider.create_type_table("doomed_table", "/test/test_vars", 2,
                                           [("x", "double"), ("y", "double"), ("z", "double")], "to be removed")
        table_id, table_path = table.id, table.path
        shared, other = "5.1|5.2|5.3|5.4|5.5|5.6", "5.1|5.2|5.3|5.4|5.5|5.7"
        assignments = [provider.create_assignment(rows_of(shared), table_path, 0, 1000, "default", "a"),
                       provider.create_assignment(rows_of(shared), table_path, 0, 1000, "test", "b"),
                       provider.create_assignment(rows_of(other), table_path, 0, 1000, "default", "c")]
        assignment_ids = [assignment.id for assignment in assignments]
        self.assertEqual(len(self.set_ids_of_table(path, table_id)), 2)
        sets_of_other_tables = self.row_counts(path)["constantSets"] - 2

        with self.assertRaises(ValueError):     # section 14.1: rm -t of a table with assignments, as in 2.4
            provider.delete_type_table(provider.get_type_table(table_path))
        self.assertEqual(len(self.set_ids_of_table(path, table_id)), 2)

        for assignment_id in assignment_ids:
            provider.delete_assignment(provider.get_assignment_by_id(assignment_id))
        self.assertEqual(len(self.set_ids_of_table(path, table_id)), 2)     # rm -a keeps the sets

        provider.delete_type_table(provider.get_type_table(table_path))
        self.assertEqual(self.set_ids_of_table(path, table_id), [])
        self.assertEqual(self.query(path, 'SELECT id FROM "typeTables" WHERE id = ?', (table_id,)), [])
        self.assertEqual(self.query(path, 'SELECT id FROM columns WHERE "typeId" = ?', (table_id,)), [])
        self.assertEqual(self.row_counts(path)["constantSets"], sets_of_other_tables)

    def test_sqlite_writers_wait(self):
        """T18, section 5.1 (SQLite): a second writer waits for the first and then reuses its set."""
        path = self.new_fresh_db()
        before = self.row_counts(path)
        vault = "6.1|6.2|6.3|6.4|6.5|6.6"
        idents = {}
        first_inside, release_first, second_entered = threading.Event(), threading.Event(), threading.Event()
        done = {"first": threading.Event(), "second": threading.Event()}
        results, errors = {}, {}
        second_wrote_while_first_held = []

        def hold_first_writer(mapper, connection, target):
            if threading.get_ident() == idents.get("first"):
                first_inside.set()
                release_first.wait(10)

        def watch_second_writer(mapper, connection, target):
            if threading.get_ident() == idents.get("second"):
                second_wrote_while_first_held.append(not release_first.is_set())

        self.add_mapper_hook(ConstantSet, "before_insert", hold_first_writer)
        self.add_mapper_hook(Assignment, "before_insert", watch_second_writer)

        def writer(name):
            try:
                idents[name] = threading.get_ident()
                provider = ccdb.AlchemyProvider()      # each thread owns its provider and connection
                provider.connect("sqlite:///" + path)
                try:
                    provider.authentication.current_user_name = "test_user"
                    provider.logging_enabled = False
                    if name == "second":
                        second_entered.set()           # the wait window opens only once the call is under way
                    assignment = provider.create_assignment(rows_of(vault), TABLE, 0, 1000, "default", name)
                    results[name] = assignment.id
                finally:
                    provider.disconnect()
            except Exception as ex:
                errors[name] = ex
            finally:
                done[name].set()

        first = threading.Thread(target=writer, args=("first",), daemon=True)
        second = threading.Thread(target=writer, args=("second",), daemon=True)
        first.start()
        try:
            self.assertTrue(first_inside.wait(10), "the first writer never reached the INSERT of its set")
            second.start()
            self.assertTrue(second_entered.wait(10), "the second writer never reached create_assignment: {}".format(errors))
            second_finished_early = done["second"].wait(0.5)
        finally:
            release_first.set()
            first.join(20)
            if second.ident is not None:
                second.join(20)
        self.assertFalse(first.is_alive() or second.is_alive(), "a writer did not finish")
        self.assertEqual(errors, {})
        self.assertFalse(second_finished_early, "the second writer finished while the first held its transaction")
        self.assertEqual(second_wrote_while_first_held, [False],
                         "the second writer inserted its assignment while the first held its transaction")
        self.assertEqual(self.set_id_of_assignment(path, results["first"]),
                         self.set_id_of_assignment(path, results["second"]))
        after = self.row_counts(path)
        self.assertEqual(after["assignments"], before["assignments"] + 2)
        self.assertEqual(after["constantSets"], before["constantSets"] + 1)

    def test_log_record(self):
        """T19, section 5.3: the log record names the set, marks reuse, and is gone after a failure in step f."""
        with self.subTest("provider"):
            path, provider = self.fresh(logging_enabled=True)
            vault = "8.1|8.2|8.3|8.4|8.5|8.6"
            first = provider.create_assignment(rows_of(vault), TABLE, 0, 1000, "default", "first")
            record = provider.get_log_records(limit=1)[0]
            self.assertEqual(record.action, "create")
            self.assertEqual(record.affected_ids, "|assignments{}|constantSets{}|".format(
                first.id, first.constant_set_id))
            self.assertFalse(record.description.endswith(" (shared data)"))

            second = provider.create_assignment(rows_of(vault), TABLE, 0, 1000, "test", "second")
            record = provider.get_log_records(limit=1)[0]
            self.assertEqual(record.affected_ids, "|assignments{}|constantSets{}|".format(
                second.id, first.constant_set_id))
            self.assertTrue(record.description.endswith(" (shared data)"), record.description)

            def fail(mapper, connection, target):
                raise InjectedFailure("injected by the test")

            before = self.row_counts(path)
            event.listen(LogRecord, "before_insert", fail)      # section 14.1: step f flushes the record
            try:
                with self.assertRaises(InjectedFailure):
                    provider.create_assignment(rows_of(vault), TABLE, 0, 1000, "subtest", "third")
            finally:
                event.remove(LogRecord, "before_insert", fail)
            self.assertEqual(self.row_counts(path), before)
            self.assertEqual(self.query(path, "SELECT COUNT(*) FROM logs WHERE comment = 'third'"), [(0,)])

        with self.subTest("cli: add and log"):
            path = self.new_fresh_db()
            cli = self.new_cli(path, log_sqlite=True)
            self.run_cli(cli, "add {} {}".format(TABLE, os.path.join(TESTS_DIR, "test_table.txt")))
            new_id = self.query(path, "SELECT MAX(id) FROM assignments")[0][0]
            self.assertEqual(self.set_id_of_assignment(path, new_id), 4)
            self.assertEqual(self.query(path, 'SELECT "affectedIds" FROM logs ORDER BY id DESC LIMIT 1'),
                             [("|assignments{}|constantSets4|".format(new_id),)])
            output = self.run_cli(cli, "log")
            self.assertIn(" (shared data)", output)

    def test_vers_l(self):
        """T19, section 5.4: default vers output unchanged; vers -l shows the hash prefix and the sharer count."""
        path = self.new_fresh_db()
        cli = self.new_cli(path)
        for _ in range(2):      # two more sharers of seed set 4 (test_table.txt holds its bytes): 3 in all
            self.run_cli(cli, "add {} {}".format(TABLE, os.path.join(TESTS_DIR, "test_table.txt")))
        new_ids = [row[0] for row in self.query(path, "SELECT id FROM assignments WHERE id > 5 ORDER BY id")]
        self.assertEqual(len(new_ids), 2)

        plain = self.run_cli(cli, "vers " + TABLE).splitlines()
        self.assertEqual(plain[0], VERS_HEADER)
        self.assertEqual(len(plain), 1 + 6)      # seed assignments 1, 2, 4, 5 of the table and the two new ones
        for line in plain:
            self.assertIsNone(re.search(r"\b[0-9a-f]{12}\b", line), line)

        # Section 5.4 gives the -l columns only as an example, so no position or adjacency is asserted: the ID
        # leads the line as in the default output, the 12-digit prefix appears not followed or preceded by
        # another hex digit, and the count is a whitespace token after the ID. The counts 3 (set 4) and 1
        # (sets 1, 2, 5) occur in no other token of these lines: dates, times and run ranges are hyphenated,
        # and the comments hold no bare 1 or 3.
        listed = self.run_cli(cli, "vers -l " + TABLE).splitlines()
        rest_by_id = {}
        for line in listed:
            tokens = line.split()
            if tokens and tokens[0].isdigit():
                rest_by_id[int(tokens[0])] = tokens[1:]
        self.assertEqual(sorted(rest_by_id), sorted([1, 2, 4, 5] + new_ids))

        set_vaults = dict(self.query(path, 'SELECT id, vault FROM "constantSets" WHERE "constantTypeId" = 1'))
        expected = {1: (set_vaults[1], "1"), 2: (set_vaults[2], "1"), 4: (SEED_SET_4_VAULT, "3"),
                    5: (set_vaults[5], "1")}
        expected.update({new_id: (SEED_SET_4_VAULT, "3") for new_id in new_ids})
        for assignment_id, (vault, count) in expected.items():
            rest = rest_by_id[assignment_id]
            message = "assignment {}: {}".format(assignment_id, rest)
            prefix = sha256_hex(vault)[:12]
            self.assertRegex(" ".join(rest), "(?<![0-9a-f]){}(?![0-9a-f])".format(prefix), message)
            self.assertIn(count, rest, message)
            self.assertNotIn({"1": "3", "3": "1"}[count], rest, message)
        self.assertEqual(sha256_hex(SEED_SET_4_VAULT)[:12], "55d35b501c1a")    # the note's example

    def test_vers_l_query_shape(self):
        """T19, section 5.4: vers -l counts sharers with one GROUP BY constantSetId query and reads no vault."""
        path = self.new_fresh_db()
        cli = self.new_cli(path)
        cli.provider.connect("sqlite:///" + path)
        cli.provider.authentication.current_user_name = "test_user"
        statements = []

        def collect(conn, cursor, statement, parameters, context, executemany):
            statements.append(statement.lower())

        event.listen(cli.provider.engine, "before_cursor_execute", collect)
        self.addCleanup(event.remove, cli.provider.engine, "before_cursor_execute", collect)
        self.run_cli(cli, "vers -l " + TABLE)
        grouped = [s for s in statements if "group by" in s and "constantsetid" in s]
        self.assertEqual(len(grouped), 1, statements)
        self.assertEqual([s for s in statements if "vault" in s], [])


if __name__ == "__main__":
    unittest.main()
