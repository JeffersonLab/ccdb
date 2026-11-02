"""Properties of the instance and of objects: the provider methods, 'ccdb prop' and the properties block of 'ccdb info'.

Runs on the SQLite test database that ccdb.testing recreates for every test (CCDB_TEST_SQLITE_CONNECTION).
"""
import logging
import sys
import unittest
from io import StringIO
from unittest import mock

import ccdb.cmd.themes
from ccdb import testing as helper
from ccdb.cmd.cli_manager import CliManager, CCDB_EXCEPTIONS_THROW
from ccdb.errors import AnonymousUserForbiddenError, ObjectIsNotFoundInDbError
from ccdb.model import LogRecord, Property


TABLE = "/test/test_vars/test_table"        # seed table: 2 rows, columns x y z (double)

logger = logging.getLogger("ccdb")


class PropertiesTests(unittest.TestCase):

    def setUp(self):
        helper.recreate_test_sqlite_db()

        self.cli = CliManager()
        self.cli.exception_handling = CCDB_EXCEPTIONS_THROW
        self.cli.force_exceptions = True
        self.cli.theme = ccdb.cmd.themes.NoColorTheme()
        self.cli.connection_string = helper.sqlite_test_connection_str
        self.cli.context.user_name = "test_user"
        self.cli.log_sqlite = True      # the log records are part of what a property change promises
        self.cli.register_utilities()
        # the provider tests call the provider before any command has connected it
        self.assertTrue(self.cli.check_connection(self.cli.context.commands["prop"]))

        self.output = StringIO()
        self.saved_stdout = sys.stdout
        sys.stdout = self.output
        self.handler = logging.StreamHandler(self.output)
        logger.addHandler(self.handler)
        logger.setLevel(logging.INFO)

    def tearDown(self):
        logger.removeHandler(self.handler)
        sys.stdout = self.saved_stdout
        self.cli.context.provider.disconnect()
        helper.clean_test_sqlite_db()

    @property
    def provider(self):
        return self.cli.context.provider

    def run_cli(self, command_line):
        """Runs one command and returns what it printed"""
        self.output.seek(0)
        self.output.truncate()
        self.cli.process_command_line(command_line)
        return self.output.getvalue()

    def log_count(self):
        return self.provider.session.query(LogRecord).count()

    def property_rows(self, owner_type, owner_id, name):
        return self.provider.session.query(Property).filter(Property.owner_type == owner_type,
                                                            Property.owner_id == owner_id,
                                                            Property.name == name).count()

    # provider
    def test_provider_instance_set_get_ls(self):
        self.provider.set_property("instance", 0, "experiment", "GlueX")
        self.provider.set_property("instance", 0, "contact", "someone@example.org")

        self.assertEqual(self.provider.get_property("instance", 0, "experiment").value, "GlueX")
        self.assertIsNone(self.provider.get_property("instance", 0, "license"))
        self.assertEqual([p.name for p in self.provider.get_properties("instance", 0)], ["contact", "experiment"])

    def test_provider_update_keeps_one_row_and_logs_each_change(self):
        table = self.provider.get_type_table(TABLE)
        before = self.log_count()

        first = self.provider.set_property("table", table.id, "description", "first")
        second = self.provider.set_property("table", table.id, "description", "second")

        self.assertEqual(first.id, second.id)
        self.assertEqual(self.property_rows("table", table.id, "description"), 1)
        self.assertEqual(self.provider.get_property("table", table.id, "description").value, "second")
        self.assertEqual(self.log_count(), before + 2)

        records = self.provider.get_log_records(limit=2)
        self.assertEqual([r.action for r in records], ["update", "create"])
        self.assertIn("|properties{0}|".format(second.id), records[0].affected_ids)
        self.assertIn("|typeTables{0}|".format(table.id), records[0].affected_ids)
        self.assertEqual(records[0].comment, "second")

    def test_provider_same_name_other_owner_is_another_row(self):
        table = self.provider.get_type_table(TABLE)
        self.provider.set_property("table", table.id, "license", "CC-BY-4.0")
        self.provider.set_property("instance", 0, "license", "MIT")
        self.assertEqual(self.provider.get_property("table", table.id, "license").value, "CC-BY-4.0")
        self.assertEqual(self.provider.get_property("instance", 0, "license").value, "MIT")

    def test_provider_delete_logs(self):
        self.provider.set_property("instance", 0, "url", "https://example.org")
        before = self.log_count()

        self.provider.delete_property("instance", 0, "url")

        self.assertIsNone(self.provider.get_property("instance", 0, "url"))
        self.assertEqual(self.log_count(), before + 1)
        self.assertEqual(self.provider.get_log_records(limit=1)[0].action, "delete")
        self.assertRaises(ObjectIsNotFoundInDbError, self.provider.delete_property, "instance", 0, "url")

    def test_provider_rejects_unknown_owner_type(self):
        self.assertRaises(ValueError, self.provider.set_property, "assignment", 1, "description", "x")
        self.assertRaises(ValueError, self.provider.get_properties, "", 0)

    def test_provider_failed_log_record_rolls_back_the_property(self):
        with mock.patch.object(self.provider, "create_log_record", side_effect=RuntimeError("log failed")):
            self.assertRaises(RuntimeError, self.provider.set_property, "instance", 0, "experiment", "GlueX")
        self.assertIsNone(self.provider.get_property("instance", 0, "experiment"))

    def test_provider_anonymous_user_is_refused(self):
        self.provider.set_property("instance", 0, "experiment", "GlueX")
        self.provider.authentication.current_user_name = "anonymous"
        self.assertRaises(AnonymousUserForbiddenError, self.provider.set_property, "instance", 0, "url", "x")
        self.assertRaises(AnonymousUserForbiddenError, self.provider.delete_property, "instance", 0, "experiment")

    def test_provider_root_directory_is_refused(self):
        self.assertRaises(ValueError, self.provider.set_property, "directory", 0, "description", "x")

    # prop command
    def test_cli_instance_set_get_ls(self):
        before = self.log_count()
        self.run_cli("prop set --instance experiment GlueX")
        self.run_cli("prop set --instance description Hall D calibration constants")

        self.assertEqual(self.run_cli("prop get --instance experiment").strip(), "GlueX")
        listing = self.run_cli("prop ls --instance")
        self.assertIn("description = Hall D calibration constants", listing)
        self.assertIn("experiment = GlueX", listing)
        self.assertEqual(self.log_count(), before + 2)

    def test_cli_table_set_get_ls_and_update(self):
        table_id = self.provider.get_type_table(TABLE).id
        before = self.log_count()
        self.run_cli("prop set {0} doc_url https://example.org/one".format(TABLE))
        self.run_cli("prop set -t {0} doc_url https://example.org/two".format(TABLE))

        self.assertEqual(self.run_cli("prop get {0} doc_url".format(TABLE)).strip(), "https://example.org/two")
        self.assertIn("doc_url = https://example.org/two", self.run_cli("prop ls " + TABLE))
        self.assertEqual(self.property_rows("table", table_id, "doc_url"), 1)
        self.assertEqual(self.log_count(), before + 2)

    def test_cli_relative_table_name(self):
        self.run_cli("cd /test/test_vars")
        self.run_cli("prop set test_table keywords calibration, test")
        self.assertEqual(self.run_cli("prop get {0} keywords".format(TABLE)).strip(), "calibration, test")

    def test_cli_directory_and_variation(self):
        self.run_cli("prop set -d /test contact Jane Doe")
        self.run_cli("prop set -v default description The default variation")
        self.run_cli("prop set /test/test_vars/test_table contact Somebody Else")

        self.assertEqual(self.run_cli("prop get -d /test contact").strip(), "Jane Doe")
        self.assertEqual(self.run_cli("prop ls default -v").strip(), "description = The default variation")
        directory = self.provider.get_directory("/test")
        self.assertEqual(self.provider.get_property("directory", directory.id, "contact").value, "Jane Doe")

    def test_cli_rm(self):
        self.run_cli("prop set --instance citation Some paper")
        self.run_cli("prop rm --instance citation")
        self.assertEqual(self.run_cli("prop ls --instance").strip(), "")

    def test_cli_errors(self):
        self.assertRaises(ObjectIsNotFoundInDbError, self.run_cli, "prop get --instance experiment")
        self.assertRaises(ValueError, self.run_cli, "prop set --instance experiment")
        self.assertRaises(Exception, self.run_cli, "prop set --instance -d /test contact x")

    # info
    def test_info_shows_properties(self):
        self.run_cli("prop set {0} source_url https://example.org/src".format(TABLE))
        self.run_cli("prop set -d /test description The test directory")
        self.run_cli("prop set -v default keywords base")

        table_info = self.run_cli("info " + TABLE)
        self.assertIn("Properties:", table_info)
        self.assertIn("source_url :  https://example.org/src", table_info)
        self.assertIn("description :  The test directory", self.run_cli("info -d /test"))
        self.assertIn("keywords :  base", self.run_cli("info -v default"))

    def test_info_without_properties_has_no_block(self):
        self.assertNotIn("Properties:", self.run_cli("info " + TABLE))


if __name__ == "__main__":
    unittest.main()
