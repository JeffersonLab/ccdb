"""The time model's part of the schema 6 upgrade and rollback (docs/concepts/time.md, notes/time-model.md §4).

SQLite: `db upgrade --sqlite-time-zone ZONE` rewrites every time from the writers' wall time to UTC text with six
fraction digits; without a zone, or with an unknown one, it refuses and changes nothing; the dry run counts the
values in a repeated or a skipped hour; `db rollback-v6 --sqlite-time-zone ZONE` writes wall time back.
MySQL and MariaDB: assignments.created and tags.snapshotTime get microseconds, the stored instants unchanged; the
rollback cuts the fraction instead of rounding it into the next second. The MySQL tests run on
CCDB_TEST_MYSQL_CONNECTION and are skipped without it.
"""
import datetime
import re
import tempfile
import time
import unittest

from ccdb import testing
from ccdb.provider import AlchemyProvider

try:
    from . import unit_test_upgrade_v6 as v6
except ImportError:
    import unit_test_upgrade_v6 as v6

ZONE = "America/New_York"
UTC_TEXT = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{6}$")

# id, wall time written in New York, the UTC text the upgrade must store, the wall text the rollback writes back
WALL_TIMES = [
    (101, "2024-06-01 12:00:00", "2024-06-01 16:00:00.000000", "2024-06-01 12:00:00.000000"),          # EDT
    (102, "2024-01-15 08:00:00.250000", "2024-01-15 13:00:00.250000", "2024-01-15 08:00:00.250000"),   # EST
    (103, "2024-11-03 01:30:00", "2024-11-03 05:30:00.000000", "2024-11-03 01:30:00.000000"),          # repeated: first
    (104, "2024-03-10 02:30:00", "2024-03-10 07:30:00.000000", "2024-03-10 03:30:00.000000"),          # skipped: forward
]


@unittest.skipUnless(hasattr(time, "tzset"), "time.tzset is not available")
class SqliteTimeUpgradeTest(unittest.TestCase):

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.db = v6.SqliteDb(directory.name)
        self.db.build_v5()
        set_id = self.db.scalar("SELECT MIN(`id`) FROM `constantSets`")
        self.db.insert_assignments([(assignment_id, set_id, wall) for assignment_id, wall, _, _ in WALL_TIMES])

    def created(self, assignment_id):
        return self.db.scalar("SELECT `created` FROM `assignments` WHERE `id` = :id", {"id": assignment_id})

    def upgrade(self, zone=ZONE):
        run = v6.run_ccdb(self.db.url, "db upgrade --upgrade-i-am-sure --sqlite-time-zone " + zone)
        self.assertTrue(run.ok, run.text())

    def test_upgrade_stores_utc_with_six_digits(self):
        self.upgrade()
        for assignment_id, wall, utc, _ in WALL_TIMES:
            self.assertEqual(self.created(assignment_id), utc, wall)
        # every time column of every table, not only assignments.created
        for table, column in [("assignments", "created"), ("assignments", "modified"), ("directories", "created"),
                              ("typeTables", "modified"), ("variations", "created"), ("users", "created"),
                              ("logs", "created"), ("constantSets", "created")]:
            for (value,) in self.db.query('SELECT "%s" FROM "%s" WHERE "%s" IS NOT NULL' % (column, table, column)):
                self.assertRegex(value, UTC_TEXT, "%s.%s" % (table, column))

    def test_python_reads_the_wall_time_back(self):
        self.upgrade()
        restore = testing.pin_time_zone(ZONE)
        self.addCleanup(restore)
        provider = AlchemyProvider()
        provider.connect(self.db.url)
        self.addCleanup(provider.disconnect)
        self.assertEqual(provider.get_assignment_by_id(101).created, datetime.datetime(2024, 6, 1, 12, 0))
        self.assertEqual(provider.get_assignment_by_id(102).created, datetime.datetime(2024, 1, 15, 8, 0, 0, 250000))

    def test_upgrade_needs_a_known_zone(self):
        before = v6.file_sha256(self.db.path)
        for command in ("db upgrade --upgrade-i-am-sure", "db upgrade --upgrade-i-am-sure --sqlite-time-zone Mars/Base",
                        "db upgrade --dry-run"):
            run = v6.run_ccdb(self.db.url, command)
            self.assertFalse(run.ok, run.text())
            self.assertIn("--sqlite-time-zone", run.said())
            self.assertEqual(v6.file_sha256(self.db.path), before)
            self.assertEqual(self.db.version(), 5)

    def test_dry_run_counts_the_repeated_and_the_skipped_hour(self):
        run = v6.run_ccdb(self.db.url, "db upgrade --dry-run --sqlite-time-zone " + ZONE)
        self.assertTrue(run.ok, run.text())
        line = next(line for line in run.said().splitlines() if "assignments.created" in line)
        self.assertIn("1 in a repeated hour", line)
        self.assertIn("1 in a skipped hour", line)
        self.assertEqual(self.db.version(), 5)

    def test_rollback_writes_wall_time_back(self):
        self.upgrade()
        run = v6.run_ccdb(self.db.url, "db rollback-v6 --rollback-i-am-sure --sqlite-time-zone " + ZONE)
        self.assertTrue(run.ok, run.text())
        self.assertEqual(self.db.version(), 5)
        for assignment_id, _, _, wall_back in WALL_TIMES:
            self.assertEqual(self.created(assignment_id), wall_back)

    def test_rollback_needs_a_zone(self):
        self.upgrade()
        run = v6.run_ccdb(self.db.url, "db rollback-v6 --rollback-i-am-sure")
        self.assertFalse(run.ok, run.text())
        self.assertIn("--sqlite-time-zone", run.said())
        self.assertEqual(self.db.version(), 6)


class MysqlTimeUpgradeTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.url = v6.mysql_url_or_skip()

    @classmethod
    def tearDownClass(cls):
        v6.restore_mysql_test_db(cls.url)

    def setUp(self):
        self.db = v6.MysqlDb(self.url)
        self.db.build_v5()

    def precision(self, table, column):
        return self.db.scalar("SELECT DATETIME_PRECISION FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() "
                              "AND TABLE_NAME = :t AND COLUMN_NAME = :c", {"t": table, "c": column})

    def test_upgrade_gives_microseconds_and_keeps_every_instant(self):
        before = self.db.query("SELECT `id`, UNIX_TIMESTAMP(`created`) FROM `assignments` ORDER BY `id`")
        run = v6.run_ccdb(self.url, v6.UPGRADE + self.db.no_tx_check)
        self.assertTrue(run.ok, run.text())
        self.assertEqual(self.precision("assignments", "created"), 6)
        self.assertEqual(self.precision("tags", "snapshotTime"), 6)
        after = self.db.query("SELECT `id`, UNIX_TIMESTAMP(`created`) FROM `assignments` ORDER BY `id`")
        self.assertEqual([(i, float(t)) for i, t in after], [(i, float(t)) for i, t in before])

    def test_rollback_cuts_the_fraction(self):
        run = v6.run_ccdb(self.url, v6.UPGRADE + self.db.no_tx_check)
        self.assertTrue(run.ok, run.text())
        set_id = self.db.scalar("SELECT MIN(`id`) FROM `constantSets`")
        self.db.insert_assignments([(201, set_id, "2024-06-01 12:00:00.600000")])
        run = v6.run_ccdb(self.url, v6.ROLLBACK + self.db.no_tx_check)
        self.assertTrue(run.ok, run.text())
        self.assertEqual(self.precision("assignments", "created"), 0)
        self.assertEqual(str(self.db.scalar("SELECT `created` FROM `assignments` WHERE `id` = 201")), "2024-06-01 12:00:00")


if __name__ == '__main__':
    unittest.main()
