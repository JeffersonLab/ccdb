"""`ccdb db dedup` on an upgraded schema 5 database: design note schema6.md §7 and §2.3, matrix row T23.

The history is built on the frozen schema 5 base (schema_v5_base.py) with schema 5 columns only, upgraded by
`ccdb db upgrade`, then deduplicated through the CLI in-process. SQLite runs always; MySQL and MariaDB run on the
database of CCDB_TEST_MYSQL_CONNECTION when it is set (see unit_test_upgrade_v6 for the variables).

§14.1 contracts used here: `dedup --dedup-i-am-sure` refuses the whole run before any change while a sha256 is not lowercase hex
and points to `db rehash --rehash-i-am-sure`; `rehash --rehash-i-am-sure` exits 0 when it repaired every mismatch; without PROCESS
`dedup --dedup-i-am-sure` needs --no-transaction-check, while `dedup` without it runs no preflight beyond the version.
"""
import os
import re
import sqlite3
import tempfile
import threading
import time
import unittest

from sqlalchemy import event
from sqlalchemy.engine import Engine

# Have to import it this way as tests may be considered a package or not depending on context
try:
    from . import unit_test_upgrade_v6 as v6
except ImportError:
    import unit_test_upgrade_v6 as v6


TABLE1 = 1          # /test/test_vars/test_table: 2 rows x 3 columns
TABLE2 = 2          # /test/test_vars/test_table2: 1 row x 3 columns
SHARED = "7|7|7|8|8|8"

# (id, constantTypeId, vault): three identical sets, the middle one unused; a 1.0 / 1.00 pair; an unused singleton;
# in table 2 an identical pair whose oldest set is unused
HISTORY_SETS = [
    (101, TABLE1, SHARED),
    (102, TABLE1, SHARED),
    (103, TABLE1, SHARED),
    (104, TABLE1, "1.0|2|3|4|5|6"),
    (105, TABLE1, "1.00|2|3|4|5|6"),
    (106, TABLE1, "9|9|9|9|9|9"),
    (201, TABLE2, "5|5|5"),
    (202, TABLE2, "5|5|5"),
]

# (id, constantSetId, created): 1103 and 1104 share set 103 the way `ccdb cp` makes them share
HISTORY_ASSIGNMENTS = [
    (1101, 101, "2020-02-01 00:00:01"),
    (1103, 103, "2020-02-01 00:00:03"),
    (1104, 103, "2020-02-01 00:00:04"),
    (1105, 104, "2020-02-01 00:00:05"),
    (1106, 105, "2020-02-01 00:00:06"),
    (1202, 202, "2020-02-01 00:00:07"),
]

EXPECTED_SET_OF = {1101: 101, 1103: 101, 1104: 101, 1105: 104, 1106: 105, 1202: 201,
                   1: 1, 2: 2, 3: 3, 4: 4, 5: 5}
EXPECTED_SETS = [1, 2, 3, 4, 5, 101, 104, 105, 201]

UNIQUE_INDEX = "uq_constantSets_table_sha256"
INTERIM_INDEX = "ix_constantSets_table_sha256"
LOG_DESCRIPTION = re.compile(r"^Merged \d+ constant sets? into \d+, removed \d+ unused sets?")


def snapshot(db):
    return {
        "sets": db.query("SELECT `id`, `constantTypeId`, `vault`, `sha256`, `size`, `modified` "
                         "FROM `constantSets` ORDER BY `id`"),
        "assignments": db.query("SELECT `id`, `constantSetId`, `created`, `modified` FROM `assignments` ORDER BY `id`"),
        "logs": db.max_log_id(),
        "indexes": db.indexes("constantSets"),
    }


def resolved_vaults(db):
    """What every assignment resolves to: (assignment id, vault), orphans left out"""
    return db.query("SELECT a.`id`, s.`vault` FROM `assignments` a JOIN `constantSets` s ON s.`id` = a.`constantSetId` "
                    "ORDER BY a.`id`")


class DedupCases(object):
    """T23 for one backend: the class provides self.db"""

    def build_history(self):
        db = self.db
        db.build_v5()
        db.insert_sets(HISTORY_SETS)
        db.insert_assignments(HISTORY_ASSIGNMENTS)
        run = v6.run_ccdb(db.url, v6.UPGRADE + db.no_tx_check)
        self.assertTrue(run.ok, run.text())
        self.assertEqual(db.version(), 6)

    def dedup(self, flags=""):
        """--no-transaction-check only with --dedup-i-am-sure: §14.1, the report runs no open-transaction check"""
        no_tx_check = self.db.no_tx_check if "--dedup-i-am-sure" in flags else ""
        return v6.run_ccdb(self.db.url, "db dedup" + flags + no_tx_check)

    def test_dedup(self):
        """T23 (§7): repoints to the oldest, removes unused sets, keeps 1.0/1.00, logs once, unique index, idempotent"""
        db = self.db
        self.build_history()
        indexes = db.indexes("constantSets")
        self.assertIn(INTERIM_INDEX, indexes, "§2.3: an upgraded database with duplicates has the interim index")
        self.assertFalse(indexes[INTERIM_INDEX])
        self.assertNotIn(UNIQUE_INDEX, indexes)

        # a sha256 that is not 64 lowercase hex characters stops dedup until rehashed: §14.1, the whole run refuses
        # before any change, table 2 included, and points to `db rehash --rehash-i-am-sure`
        db.execute("UPDATE `constantSets` SET `sha256` = '' WHERE `id` = 104")
        before = snapshot(db)
        run = self.dedup(" --dedup-i-am-sure")
        self.assertFalse(run.ok, run.text())
        self.assertEqual(snapshot(db), before, "a non-hex sha256 refuses the whole run before any change")
        self.assertIn("rehash --rehash-i-am-sure", run.said(), "the refusal points to `db rehash --rehash-i-am-sure`")
        run = v6.run_ccdb(db.url, "db rehash --rehash-i-am-sure")
        self.assertTrue(run.ok, "§14.1: rehash --rehash-i-am-sure exits 0 when it repaired every mismatch\n" + run.text())
        sha256, size, vault = db.query("SELECT `sha256`, `size`, `vault` FROM `constantSets` WHERE `id` = 104")[0]
        self.assertEqual((sha256, size), v6.digest(vault))

        # without --dedup-i-am-sure: a report per table, nothing changed; on MySQL as ccdb_user, who lacks PROCESS, without
        # --no-transaction-check (§14.1)
        before = snapshot(db)
        resolved_before = resolved_vaults(db)
        run = self.dedup()
        self.assertTrue(run.ok, run.text())
        self.assertIn("test_table", run.output)
        self.assertEqual(snapshot(db), before)

        # --apply is not a flag: only --dedup-i-am-sure changes data (§10)
        run = v6.run_ccdb(db.url, "db dedup --apply" + db.no_tx_check, allow_parse_error=True)
        self.assertFalse(run.ok, run.text())
        self.assertEqual(snapshot(db), before)

        run = self.dedup(" --dedup-i-am-sure")
        self.assertTrue(run.ok, run.text())
        after = snapshot(db)
        self.assertEqual([row[0] for row in after["sets"]], EXPECTED_SETS)
        self.assertEqual({row[0]: row[1] for row in after["assignments"]}, EXPECTED_SET_OF)
        # repointing keeps every assignment id, created and modified time, and every surviving set's modified time
        self.assertEqual([(row[0], row[2], row[3]) for row in after["assignments"]],
                         [(row[0], row[2], row[3]) for row in before["assignments"]])
        survivors = {row[0]: row for row in before["sets"]}
        for row in after["sets"]:
            self.assertEqual(row, survivors[row[0]])
        self.assertEqual(resolved_vaults(db), resolved_before, "every assignment resolves to the same bytes")

        # §7 step 6: one record per changed table; the note does not forbid others (an index swap record, say)
        records = [record for record in db.logs_after(before["logs"]) if record[1].startswith("|typeTables")]
        self.assertEqual(sorted(record[1] for record in records), ["|typeTables1|", "|typeTables2|"],
                         "one log record per changed table")
        for _, _, action, description in records:
            self.assertEqual(action, "update")
            self.assertRegex(description, LOG_DESCRIPTION)

        indexes = db.indexes("constantSets")
        self.assertTrue(indexes.get(UNIQUE_INDEX), "no duplicate left: the unique index exists")
        self.assertNotIn(INTERIM_INDEX, indexes)

        settled = snapshot(db)
        run = self.dedup(" --dedup-i-am-sure")
        self.assertTrue(run.ok, run.text())
        self.assertEqual(snapshot(db), settled, "a second --dedup-i-am-sure run changes nothing")


class SQLiteDedupTest(DedupCases, unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db = v6.SqliteDb(self.tmp_dir.name)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_dedup_sqlite_in_place(self):
        """T23 (§6.4, §7): SQLite dedup changes the file in place, one BEGIN IMMEDIATE per table, while a writer waits"""
        db = self.db
        db.build_v5()
        db.insert_sets([(101, TABLE1, SHARED), (103, TABLE1, SHARED)])
        db.insert_assignments([(1101, 101, "2020-02-01 00:00:01"), (1103, 103, "2020-02-01 00:00:03")])
        run = v6.run_ccdb(db.url, v6.UPGRADE)
        self.assertTrue(run.ok, run.text())
        listing = sorted(os.listdir(self.tmp_dir.name))
        inode = os.stat(db.path).st_ino

        hold = 0.5
        writer = {}

        def write():
            connection = sqlite3.connect(db.path, timeout=30, isolation_level=None)
            try:
                started = time.monotonic()
                connection.execute("BEGIN IMMEDIATE")
                connection.execute("INSERT INTO runRanges (created, modified, name, runMin, runMax, comment) "
                                   "VALUES ('2020-01-01 00:00:00', '2020-01-01 00:00:00', 't23_writer', 77, 78, 'T23')")
                connection.execute("COMMIT")
                writer["waited"] = time.monotonic() - started
            except Exception as ex:
                writer["error"] = ex
            finally:
                connection.close()

        thread = threading.Thread(target=write, daemon=True)
        first_write = re.compile(r"^\s*(UPDATE|DELETE|INSERT)\b.*\b(assignments|constantSets)\b", re.IGNORECASE | re.DOTALL)
        fired = []

        def on_statement(conn, cursor, statement, parameters, context, executemany):
            if not fired and first_write.match(statement):
                fired.append(statement)
                thread.start()
                time.sleep(hold)        # dedup holds its table transaction while the writer tries to begin

        event.listen(Engine, "before_cursor_execute", on_statement)
        try:
            run = v6.run_ccdb(db.url, "db dedup --dedup-i-am-sure")
        finally:
            event.remove(Engine, "before_cursor_execute", on_statement)
        self.assertTrue(run.ok, run.text())
        self.assertTrue(fired, "dedup sent no write to assignments or constantSets through SQLAlchemy")
        thread.join(30)
        self.assertNotIn("error", writer, writer.get("error"))
        self.assertGreaterEqual(writer.get("waited", 0), hold * 0.6, "the writer waited for the dedup transaction")

        self.assertEqual(os.stat(db.path).st_ino, inode, "dedup runs in place: no copy, no rename")
        self.assertEqual(sorted(os.listdir(self.tmp_dir.name)), listing)
        self.assertEqual(db.query("SELECT `constantSetId` FROM `assignments` WHERE `id` = 1103"), [(101,)])
        self.assertEqual(db.query("SELECT COUNT(*) FROM `constantSets` WHERE `id` = 103"), [(0,)])
        self.assertEqual(db.query("SELECT COUNT(*) FROM `runRanges` WHERE `name` = 't23_writer'"), [(1,)],
                         "the writer's row is not lost")


class MySQLDedupTest(DedupCases, unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.db = v6.MysqlDb(v6.mysql_url_or_skip())

    @classmethod
    def tearDownClass(cls):
        v6.restore_mysql_test_db(cls.db.url)


if __name__ == "__main__":
    unittest.main()
