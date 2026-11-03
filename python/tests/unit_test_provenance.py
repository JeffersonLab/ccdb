"""`ccdb provenance FILE.json [--tag]`: a record of resolved constants checked against the database.

The record is made by the Python usage record (AlchemyProvider.resolved_assignments), saved in both file forms the
command reads. Runs on the SQLite test database that ccdb.testing recreates (CCDB_TEST_SQLITE_CONNECTION).
"""
import json
import logging
import os
import sys
import tempfile
import unittest
from io import StringIO

import ccdb.cmd.themes
from ccdb import testing as helper
from ccdb.cmd.cli_manager import CliManager, CCDB_EXCEPTIONS_THROW

TABLE = "/test/test_vars/test_table"
TABLE2 = "/test/test_vars/test_table2"

logger = logging.getLogger("ccdb")


class ProvenanceTest(unittest.TestCase):

    def setUp(self):
        helper.recreate_test_sqlite_db()
        self.cli = CliManager()
        self.cli.exception_handling = CCDB_EXCEPTIONS_THROW
        self.cli.force_exceptions = True
        self.cli.theme = ccdb.cmd.themes.NoColorTheme()
        self.cli.connection_string = helper.sqlite_test_connection_str
        self.cli.context.user_name = "test_user"
        self.cli.register_utilities()
        self.assertTrue(self.cli.check_connection(self.cli.context.commands["provenance"]))
        self.directory = tempfile.TemporaryDirectory()

        self.output = StringIO()
        self.saved_stdout = sys.stdout
        sys.stdout = self.output
        self.handler = logging.StreamHandler(self.output)
        logger.addHandler(self.handler)

        db = self.cli.context.provider
        db.usage_record_enabled = True
        db.get_assignment_by_request(TABLE + ":100:test")       # falls back to default
        db.get_assignment_by_request(TABLE2 + ":100:test")
        self.entries = [dict(each) for each in db.resolved_assignments]
        db.usage_record_enabled = False

    def tearDown(self):
        logger.removeHandler(self.handler)
        sys.stdout = self.saved_stdout
        self.cli.context.provider.disconnect()
        self.directory.cleanup()
        helper.clean_test_sqlite_db()

    def write(self, content):
        path = os.path.join(self.directory.name, "record.json")
        with open(path, "w", encoding="utf-8") as file:
            json.dump(content, file)
        return path

    def run_check(self, *args):
        self.output.seek(0)
        self.output.truncate()
        ok = self.cli.context.commands["provenance"].execute(list(args))
        return ok, self.output.getvalue()

    def test_a_true_record_matches(self):
        ok, text = self.run_check(self.write({"ccdb_version": "2.5.0", "resolved": self.entries}))
        self.assertTrue(ok, text)
        self.assertIn("2 of 2 entries match the database", text)
        self.assertEqual(text.count("same"), 2)

    def test_the_bare_list_form(self):
        ok, text = self.run_check(self.write(self.entries))
        self.assertTrue(ok, text)

    def test_other_data_or_a_missing_assignment_fail(self):
        changed = [dict(self.entries[0], sha256="0" * 64), dict(self.entries[1], assignment_id=999999)]
        ok, text = self.run_check(self.write({"resolved": changed}))
        self.assertFalse(ok)
        self.assertIn("HASH", text)
        self.assertIn("MISSING", text)
        self.assertIn("0 of 2 entries match", text)

    def test_tags_that_give_the_record(self):
        self.cli.context.provider.create_tag("pass1", "test", comment="provenance test")
        ok, text = self.run_check(self.write(self.entries), "--tag")
        self.assertTrue(ok, text)
        self.assertIn("tags that give every entry: pass1", text)


if __name__ == "__main__":
    unittest.main()
