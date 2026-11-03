"""The usage record of AlchemyProvider (usage_record_enabled, resolved_assignments): off by default; while on,
get_assignment keeps every distinct resolution once, with the stored SHA-256 of the data.

Runs on the SQLite test database that ccdb.testing recreates (CCDB_TEST_SQLITE_CONNECTION).
"""
import datetime
import json
import unittest

from ccdb import testing as helper
from ccdb.model import Assignment
from ccdb.provider import AlchemyProvider

TABLE = "/test/test_vars/test_table"       # seed table; run 100 of default resolves to assignment 4


class UsageRecordTest(unittest.TestCase):

    def setUp(self):
        helper.recreate_test_sqlite_db()
        self.provider = AlchemyProvider()
        self.provider.connect(helper.sqlite_test_connection_str)
        self.provider.authentication.current_user_name = "test_user"

    def tearDown(self):
        self.provider.disconnect()
        helper.clean_test_sqlite_db()

    def test_off_by_default(self):
        self.assertFalse(self.provider.usage_record_enabled)
        self.provider.get_assignment_by_request(TABLE + ":100")
        self.assertEqual(self.provider.resolved_assignments, [])

    def test_each_resolution_once_with_the_stored_hash(self):
        db = self.provider
        db.usage_record_enabled = True
        for _ in range(3):                                  # a table read per event: one entry
            first = db.get_assignment_by_request(TABLE + ":100")
        db.get_assignment(TABLE, 100, "default")            # the same resolution through the other call
        db.create_tag("pass1", "default", comment="usage record test")
        db.get_assignment_by_request(TABLE + ":100@pass1")
        db.get_assignment_by_request(TABLE + ":100:default:2100")
        record = db.resolved_assignments
        self.assertEqual(len(record), 3, record)
        stored = db.session.get(Assignment, first.id).constant_set.sha256
        self.assertEqual(record[0], {"request": TABLE + ":100:default", "path": TABLE, "run": 100, "variation": "default",
                                     "time": "", "tag": "", "assignment_id": first.id, "sha256": stored})
        self.assertEqual((record[1]["tag"], record[1]["variation"], record[1]["request"]), ("pass1", "", TABLE + ":100@pass1"))
        self.assertTrue(record[2]["time"].startswith("21") and record[2]["time"].endswith("Z"), record[2]["time"])
        self.assertEqual(record[2]["assignment_id"], first.id)
        self.assertEqual(json.loads(json.dumps(record)), record, "the record is plain JSON")

    def test_off_again_keeps_and_clear_forgets(self):
        db = self.provider
        db.usage_record_enabled = True
        db.get_assignment_by_request(TABLE + ":100")
        db.usage_record_enabled = False
        db.get_assignment_by_request(TABLE + ":100:default:2100")
        self.assertEqual(len(db.resolved_assignments), 1)
        db.clear_resolved_assignments()
        self.assertEqual(db.resolved_assignments, [])
        db.usage_record_enabled = True
        db.get_assignment_by_request(TABLE + ":100")
        self.assertEqual(len(db.resolved_assignments), 1)

    def test_time_is_utc(self):
        db = self.provider
        db.usage_record_enabled = True
        local = datetime.datetime(2100, 1, 1, 12, 0, 0)
        db.get_assignment(TABLE, 100, "default", local)
        expected = local.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        self.assertEqual(db.resolved_assignments[0]["time"], expected)


if __name__ == "__main__":
    unittest.main()
