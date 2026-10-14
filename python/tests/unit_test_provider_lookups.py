"""Tests AlchemyProvider lookups by database id and the eager loading of get_assignments()"""
import os
import tempfile
import unittest

from sqlalchemy import event
from sqlalchemy.engine import Engine

import ccdb
from ccdb.errors import ObjectIsNotFoundInDbError
from ccdb.model import Directory, TypeTable
from ccdb.sql.sqlite_schema import create_sqlite_database


class ProviderLookupsTest(unittest.TestCase):
    """Each test gets a fresh standard SQLite database"""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        db_path = os.path.join(self.tmp_dir.name, "lookups_test.sqlite")
        create_sqlite_database(db_path)
        self.provider = ccdb.AlchemyProvider()
        self.provider.connect("sqlite:///" + db_path)

    def tearDown(self):
        self.provider.disconnect()
        self.provider.engine.dispose()
        self.tmp_dir.cleanup()

    def test_get_type_table_by_id_returns_the_table_with_its_path(self):
        table = self.provider.get_type_table_by_id(1)
        self.assertIsInstance(table, TypeTable)
        self.assertEqual(table.id, 1)
        self.assertEqual(table.name, "test_table")
        self.assertEqual(table.path, "/test/test_vars/test_table")
        self.assertEqual(table.parent_dir.path, "/test/test_vars")

    def test_get_type_table_by_id_unknown_id(self):
        with self.assertRaises(ObjectIsNotFoundInDbError) as raised:
            self.provider.get_type_table_by_id(999999)
        self.assertIn("999999", str(raised.exception))

    def test_get_directory_by_id(self):
        directory = self.provider.get_directory_by_id(1)
        self.assertIsInstance(directory, Directory)
        self.assertEqual(directory.path, "/test")

    def test_get_directory_by_id_unknown_id(self):
        with self.assertRaises(ObjectIsNotFoundInDbError) as raised:
            self.provider.get_directory_by_id(999999)
        self.assertIn("999999", str(raised.exception))

    def test_get_assignment_by_id_has_the_full_request_string(self):
        assignment = self.provider.get_assignment_by_id(4)
        self.assertEqual(assignment.constant_set.type_table.path, "/test/test_vars/test_table")
        self.assertEqual(assignment.request, "/test/test_vars/test_table:0:default:2012-10-30_23-48-42")

    def test_get_assignments_loads_relations_in_one_query(self):
        assignments = self.provider.get_assignments("/test/test_vars/test_table")
        self.assertGreaterEqual(len(assignments), 3)
        statements = []

        def count(*args):
            statements.append(1)

        event.listen(Engine, "before_cursor_execute", count)
        try:
            requests = [(a.run_range.min, a.run_range.max, a.variation.name, a.request) for a in assignments]
        finally:
            event.remove(Engine, "before_cursor_execute", count)
        self.assertEqual(statements, [], "reading run range, variation and request must not query again")
        self.assertTrue(all(r[3].startswith("/test/test_vars/test_table:") for r in requests))


if __name__ == "__main__":
    unittest.main()
