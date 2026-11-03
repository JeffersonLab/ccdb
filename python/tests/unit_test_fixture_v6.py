"""The schema 6 cases of the web GUI fixture (scripts/webgui/make_fixture.py), with their literal values.

The fixture is built into a temporary file (about two seconds) and read with plain SQL, no ORM in between. The
literals below are the ones make_fixture.py lists in add_schema6_cases; the C++ fixture test is to read the
same fixture and expect the same values, so both languages are checked against one source. The file hash is not
asserted: it depends on the SQLite version that writes the file, and CI runs older SQLite releases than a
developer machine.
"""
import collections
import hashlib
import importlib.util
import os
import sqlite3
import tempfile
import unittest

import ccdb
from ccdb import testing


SHARED_VAULT = "0|1.25|100.5|1|1.5|101.0|2|0.75|99.5"
SHARED_SHA256 = "c4c90edd40236d79a696db3f2999ae5c8fe02a21de3b88d058dae1a370a5f907"
ONE_SHA256 = "d0ff5974b6aa52cf562bea5921840c032a860a91a3512f7fe8f768f6bbe005f6"            # "1.0"
ONE_AGAIN_SHA256 = "cf9dcf6da8a82be1335c398a4005def7ee3a53d4698c59dbc6b2b14e72d1263c"      # "1.00"

SHARED_TABLE_ID = 1010          # /schema6/shared
NUMERIC_TABLE_ID = 1011         # /schema6/numeric
RETIRED_DIRECTORY_ID = 42       # /schema6/retired
RETIRED_TABLE_ID = 1012         # /schema6/retired_table
RETIRED_VARIATION_ID = 8        # retired


def _load_make_fixture():
    """scripts/webgui/make_fixture.py by its path: the scripts directory is not a package"""
    path = os.path.join(ccdb.get_ccdb_home_path(), "scripts", "webgui", "make_fixture.py")
    spec = importlib.util.spec_from_file_location("ccdb_scripts_webgui_make_fixture", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module



def setUpModule():
    # the data holds literal UTC times that the tests compare with shown (local) times
    global _restore_time_zone
    _restore_time_zone = testing.pin_time_zone("UTC")


def tearDownModule():
    _restore_time_zone()

class FixtureV6Test(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        fixture_path = os.path.join(cls.temp_dir.name, "ccdb_fixture.sqlite")
        _load_make_fixture().make(fixture_path)
        cls.connection = sqlite3.connect(fixture_path)

    @classmethod
    def tearDownClass(cls):
        cls.connection.close()
        cls.temp_dir.cleanup()

    def rows(self, sql, *params):
        return self.connection.execute(sql, params).fetchall()

    def assignment(self, assignment_id):
        """(table id, first run, last run, set id, vault, sha256, size) of one assignment"""
        return self.rows("SELECT s.constantTypeId, r.runMin, r.runMax, s.id, s.vault, s.sha256, s.size "
                         "FROM assignments a JOIN constantSets s ON s.id = a.constantSetId JOIN runRanges r ON r.id = a.runRangeId "
                         "WHERE a.id = ?", assignment_id)[0]

    def sharer_counts(self):
        """set id -> number of assignments, counted the way vers -l counts them"""
        return dict(self.rows("SELECT constantSetId, COUNT(*) FROM assignments GROUP BY constantSetId"))

    def test_d32_cases(self):
        self.assertEqual(self.rows("SELECT schemaVersion FROM schemaVersions"), [(6,)])

        with self.subTest("two assignments of one table share one constant set"):
            self.assertEqual(self.assignment(3614), (SHARED_TABLE_ID, 0, 999, 3614, SHARED_VAULT, SHARED_SHA256, 36))
            self.assertEqual(self.assignment(3615), (SHARED_TABLE_ID, 1000, 1999, 3614, SHARED_VAULT, SHARED_SHA256, 36))
            self.assertEqual(self.sharer_counts()[3614], 2)

        with self.subTest("1.0 and 1.00 are two sets with two hashes"):
            self.assertEqual(self.assignment(3616), (NUMERIC_TABLE_ID, 0, 999, 3615, "1.0", ONE_SHA256, 3))
            self.assertEqual(self.assignment(3617), (NUMERIC_TABLE_ID, 1000, 1999, 3616, "1.00", ONE_AGAIN_SHA256, 4))
            self.assertEqual((self.sharer_counts()[3615], self.sharer_counts()[3616]), (1, 1))

        with self.subTest("every set: hash and size of its UTF-8 bytes, used, unique in its table"):
            sets = self.rows("SELECT id, constantTypeId, vault, sha256, size FROM constantSets")
            wrong = [set_id for set_id, _, vault, sha256, size in sets
                     if (sha256, size) != (hashlib.sha256(vault.encode("utf-8")).hexdigest(), len(vault.encode("utf-8")))]
            self.assertEqual(wrong, [])
            unused = set(set_id for set_id, *_ in sets) - set(self.sharer_counts())
            self.assertEqual(unused, set())
            pairs = collections.Counter((table_id, sha256) for _, table_id, _, sha256, _ in sets)
            self.assertEqual([pair for pair, count in pairs.items() if count > 1], [])

        with self.subTest("one deprecated directory, table and variation, all four columns set"):
            for table, object_id in (("directories", RETIRED_DIRECTORY_ID), ("typeTables", RETIRED_TABLE_ID), ("variations", RETIRED_VARIATION_ID)):
                is_deprecated, user_id, when, comment = self.rows(
                    "SELECT isDeprecated, deprecatedByUserId, deprecatedTime, deprecationComment FROM {0} WHERE id = ?".format(table), object_id)[0]
                self.assertEqual(is_deprecated, 1, table)
                self.assertIsNotNone(user_id, table)
                self.assertIsNotNone(when, table)
                self.assertTrue(comment, table)
            deprecated = {table: self.rows("SELECT id FROM {0} WHERE isDeprecated = 1".format(table)) for table in ("directories", "typeTables", "variations")}
            self.assertEqual(deprecated, {"directories": [(RETIRED_DIRECTORY_ID,)], "typeTables": [(RETIRED_TABLE_ID,)], "variations": [(RETIRED_VARIATION_ID,)]})

        with self.subTest("two tags: at the newest assignment and in the past"):
            # Timestamps are compared to the second: SQLAlchemy stores them with a microseconds part on SQLite
            tags = self.rows("SELECT name, variationId, substr(snapshotTime, 1, 19) FROM tags ORDER BY id")
            self.assertEqual(tags, [("fixture_newest", 1, "2020-01-06 10:17:00"), ("fixture_past", 1, "2020-01-02 12:00:00")])
            newest_created = self.rows("SELECT substr(MAX(created), 1, 19) FROM assignments")[0][0]
            self.assertEqual(newest_created, "2020-01-06 10:17:00")
            self.assertEqual(self.rows("SELECT substr(created, 1, 19) FROM assignments WHERE id = 3618"), [(newest_created,)])

        with self.subTest("units on two columns of one table"):
            units = self.rows("SELECT typeId, name, units FROM columns WHERE units IS NOT NULL ORDER BY id")
            self.assertEqual(units, [(SHARED_TABLE_ID, "gain", "MeV/count"), (SHARED_TABLE_ID, "pedestal", "count")])

        with self.subTest("an instance property and a table property"):
            properties = self.rows("SELECT ownerType, ownerId, name FROM properties ORDER BY id")
            self.assertEqual(properties, [("instance", 0, "experiment"), ("table", SHARED_TABLE_ID, "procedure")])

        with self.subTest("one log record per new assignment; the reuse is marked as shared data"):
            logs = self.rows("SELECT id, action, affectedIds, description FROM logs WHERE id >= 2418 ORDER BY id")
            self.assertEqual([(log_id, action, affected) for log_id, action, affected, _ in logs],
                             [(2418, "create", "|assignments3614|constantSets3614|"),
                              (2419, "create", "|assignments3615|constantSets3614|"),
                              (2420, "create", "|assignments3616|constantSets3615|"),
                              (2421, "create", "|assignments3617|constantSets3616|"),
                              (2422, "create", "|assignments3618|constantSets3617|")])
            shared_data = [log_id for log_id, _, _, description in logs if description.endswith(" (shared data)")]
            self.assertEqual(shared_data, [2419])
            self.assertEqual(logs[1][3], "Created assignment '/schema6/shared:1000:default:2020-01-06_10-11-00' (shared data)")


if __name__ == "__main__":
    unittest.main()
