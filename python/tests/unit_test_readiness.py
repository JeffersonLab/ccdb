"""The readiness profile (ccdb.readiness, `ccdb db readiness`): every number against a plain SQL count, determinism,
and the staleness window.

Runs on the SQLite test database that ccdb.testing recreates (CCDB_TEST_SQLITE_CONNECTION), and on MySQL when
CCDB_TEST_MYSQL_CONNECTION is set. The reference counts below are the definitions in docs/concepts/ai-readiness.md
written as SQL, independent of the module's SQLAlchemy queries.
"""
import datetime
import json
import os
import unittest

from sqlalchemy import text

from ccdb import testing as helper
from ccdb.model import TypeTableColumn
from ccdb.provider import AlchemyProvider
from ccdb.readiness import profile, stale_cutoff, format_text

GENERATED = datetime.datetime(2026, 11, 3, 18, 40, 12)
INFINITE = 2147483647

# field -> SQL that counts it; :cutoff is the staleness cutoff
REFERENCE_SQL = {
    ("metadata", "columns"): "SELECT COUNT(*) FROM columns",
    ("metadata", "columns_with_units"): "SELECT COUNT(*) FROM columns WHERE units IS NOT NULL AND TRIM(units) <> ''",
    ("metadata", "tables"): "SELECT COUNT(*) FROM typeTables",
    ("metadata", "tables_with_description"): "SELECT COUNT(*) FROM typeTables WHERE comment IS NOT NULL AND TRIM(comment) <> ''",
    ("metadata", "versions"): "SELECT COUNT(*) FROM assignments",
    ("metadata", "versions_with_comment"): "SELECT COUNT(*) FROM assignments WHERE comment IS NOT NULL AND TRIM(comment) <> ''",
    ("metadata", "tables_with_contact"): "SELECT COUNT(DISTINCT ownerId) FROM properties WHERE ownerType = 'table' AND name = 'contact' AND TRIM(value) <> ''",
    ("history", "open_ended_run_ranges"): "SELECT COUNT(*) FROM assignments a JOIN runRanges r ON r.id = a.runRangeId WHERE r.runMax = 2147483647 AND r.runMin > 0",
    ("history", "versions_for_all_runs"): "SELECT COUNT(*) FROM assignments a JOIN runRanges r ON r.id = a.runRangeId WHERE r.runMax = 2147483647 AND r.runMin <= 0",
    ("history", "versions_by_anonymous"): "SELECT COUNT(*) FROM assignments a JOIN users u ON u.id = a.authorId WHERE u.name = 'anonymous'",
    ("history", "empty_tables"): "SELECT COUNT(*) FROM typeTables t WHERE NOT EXISTS (SELECT 1 FROM constantSets s JOIN assignments a ON a.constantSetId = s.id WHERE s.constantTypeId = t.id)",
    ("history", "stale_tables"): "SELECT COUNT(*) FROM (SELECT s.constantTypeId, MAX(a.created) AS newest FROM assignments a JOIN constantSets s ON s.id = a.constantSetId GROUP BY s.constantTypeId) x WHERE x.newest < :cutoff",
    ("history", "deprecated_tables"): "SELECT COUNT(*) FROM typeTables WHERE isDeprecated = 1",
    ("history", "tags"): "SELECT COUNT(*) FROM tags",
    ("data", "constant_sets"): "SELECT COUNT(*) FROM constantSets",
    ("data", "shared_sets"): "SELECT COUNT(*) FROM (SELECT constantSetId FROM assignments GROUP BY constantSetId HAVING COUNT(*) > 1) x",
    ("data", "unused_sets"): "SELECT COUNT(*) FROM constantSets s WHERE NOT EXISTS (SELECT 1 FROM assignments a WHERE a.constantSetId = s.id)",
    ("data", "bytes"): "SELECT COALESCE(SUM(size), 0) FROM constantSets",
}


class ReadinessCases(object):
    """The cases; a subclass sets self.provider to a provider connected to a freshly seeded database"""

    def reference(self, generated=GENERATED, stale_years=5):
        cutoff = stale_cutoff(generated, stale_years)
        with self.provider.engine.connect() as connection:
            parameters = {"cutoff": cutoff.strftime("%Y-%m-%d %H:%M:%S")}
            return {field: int(connection.execute(text(sql), parameters if ":cutoff" in sql else {}).scalar())
                    for field, sql in REFERENCE_SQL.items()}

    def enrich(self):
        """Puts one of each kind of metadata into the seed, so no reference count is trivially zero"""
        db = self.provider
        db.set_property("instance", 0, "license", "CC-BY-4.0")
        db.set_property("instance", 0, "citation", "Hall D, CCDB test instance")
        table = db.get_type_table("/test/test_vars/test_table")
        db.set_property("table", table.id, "contact", "calib@example.org")
        column = db.session.query(TypeTableColumn).filter(TypeTableColumn.type_table_id == table.id).first()
        column.units = "MeV"
        db.session.commit()
        # a version from run 100 to infinity, by an account, with a comment
        db.create_assignment([["1", "2", "3"], ["4", "5", "6"]], "/test/test_vars/test_table", 100, INFINITE, "default", "readiness test")

    def test_every_number_equals_its_sql_count(self):
        self.enrich()
        numbers = profile(self.provider, generated=GENERATED)
        reference = self.reference()
        for (group, field), expected in reference.items():
            self.assertEqual(numbers[group][field], expected, "{0}.{1}".format(group, field))
        self.assertEqual(numbers["instance"], {"license": True, "citation": True, "contact": False,
                                               "experiment": False, "url": False})
        self.assertEqual(numbers["units"]["columns_with_ucum_units"], numbers["metadata"]["columns_with_units"],
                         "MeV, the only units of the enriched seed, is UCUM")

    def test_the_enrichment_moves_the_numbers(self):
        """Guards the reference against counting nothing: each change of enrich() shows up"""
        before = profile(self.provider, generated=GENERATED)
        self.enrich()
        after = profile(self.provider, generated=GENERATED)
        self.assertEqual(after["metadata"]["columns_with_units"], before["metadata"]["columns_with_units"] + 1)
        self.assertEqual(after["units"]["columns_with_ucum_units"], before["units"]["columns_with_ucum_units"] + 1)
        self.assertEqual(after["metadata"]["tables_with_contact"], before["metadata"]["tables_with_contact"] + 1)
        self.assertEqual(after["metadata"]["versions"], before["metadata"]["versions"] + 1)
        self.assertEqual(after["metadata"]["versions_with_comment"], before["metadata"]["versions_with_comment"] + 1)
        self.assertEqual(after["history"]["open_ended_run_ranges"], before["history"]["open_ended_run_ranges"] + 1)
        self.assertFalse(before["instance"]["license"])
        self.assertTrue(after["instance"]["license"])

    def test_same_data_same_profile(self):
        self.enrich()
        first = profile(self.provider, generated=GENERATED)
        second = profile(self.provider, generated=GENERATED.replace(hour=23))
        self.assertEqual(first["config"]["generated"], "2026-11-03T18:40:12Z")
        first["config"].pop("generated"), second["config"].pop("generated")
        self.assertEqual(first, second, "two profiles of one UTC day differ only in `generated`")
        self.assertEqual(json.loads(json.dumps(first)), first, "the profile is plain JSON")

    def test_stale_window(self):
        """Tables with data count as stale when their newest assignment is older than the window"""
        self.enrich()     # one table gets an assignment created now
        recent = profile(self.provider, stale_years=0, generated=datetime.datetime(2000, 1, 1))
        self.assertEqual(recent["history"]["stale_tables"], 0, "nothing is older than a cutoff in 2000")
        # a cutoff a month before now: the seed tables (2012-2016) are stale, the table written now is not
        now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        later = now + datetime.timedelta(days=2 * 365 - 30)
        numbers = profile(self.provider, stale_years=2, generated=later)
        self.assertEqual(numbers["history"]["stale_tables"], self.reference(later, 2)[("history", "stale_tables")])
        tables_with_data = numbers["metadata"]["tables"] - numbers["history"]["empty_tables"]
        self.assertEqual(numbers["history"]["stale_tables"], tables_with_data - 1, "all but the table written now")
        self.assertEqual(numbers["config"]["stale_years"], 2)

    def test_text_form_names_every_number(self):
        numbers = profile(self.provider, generated=GENERATED)
        lines = format_text(numbers, "sqlite:///test.sqlite")
        self.assertIn("columns with units", lines)
        self.assertIn("stale tables", lines)
        self.assertIn(str(numbers["metadata"]["versions"]), lines)


class StaleCutoffTest(unittest.TestCase):

    def test_start_of_day_years_back(self):
        self.assertEqual(stale_cutoff(datetime.datetime(2026, 11, 3, 18, 40), 5), datetime.datetime(2021, 11, 3))

    def test_leap_day(self):
        self.assertEqual(stale_cutoff(datetime.datetime(2028, 2, 29, 1, 0), 1), datetime.datetime(2027, 2, 28))

    def test_negative_window_is_refused(self):
        with self.assertRaises(ValueError):
            profile(None, stale_years=-1)


class SQLiteReadinessTest(ReadinessCases, unittest.TestCase):

    def setUp(self):
        helper.recreate_test_sqlite_db()
        self.provider = AlchemyProvider()
        self.provider.connect(helper.sqlite_test_connection_str)
        self.provider.authentication.current_user_name = "test_user"

    def tearDown(self):
        self.provider.disconnect()
        helper.clean_test_sqlite_db()


class MySQLReadinessTest(ReadinessCases, unittest.TestCase):

    def setUp(self):
        url = os.environ.get(helper.ENV_TEST_MYSQL)
        if not url:
            raise unittest.SkipTest("{0} is not set".format(helper.ENV_TEST_MYSQL))
        helper.recreate_mysql_db(url)
        self.provider = AlchemyProvider()
        self.provider.connect(url)
        self.provider.authentication.current_user_name = "test_user"

    def tearDown(self):
        self.provider.disconnect()

    @classmethod
    def tearDownClass(cls):
        """Leaves the shared MySQL test database as `db init` creates it, for the modules that run after"""
        url = os.environ.get(helper.ENV_TEST_MYSQL)
        if url:
            helper.recreate_mysql_db(url)


if __name__ == "__main__":
    unittest.main()
