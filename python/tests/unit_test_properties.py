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

    # properties are deleted with their object
    def owner_rows(self, owner_type, owner_id):
        return self.provider.session.query(Property).filter(Property.owner_type == owner_type,
                                                            Property.owner_id == owner_id).count()

    def failing_commit(self):
        """A session commit that writes the pending changes and then fails, as a lost connection would"""
        session = self.provider.session
        real_flush = session.flush

        def commit():
            real_flush()
            raise RuntimeError("commit failed")
        return mock.patch.object(session, "commit", side_effect=commit)

    def make_table_with_properties(self):
        table = self.provider.create_type_table("prop_table", "/test/test_vars", 1, [("a", "double"), ("b", "int")])
        column_ids = [column.id for column in table.columns]
        self.provider.set_property("table", table.id, "contact", "Jane Doe")
        self.provider.set_property("table", table.id, "license", "MIT")
        for column_id in column_ids:
            self.provider.set_property("column", column_id, "description", "a column")
        return table, column_ids

    def test_delete_table_deletes_its_properties_and_of_its_columns(self):
        table, column_ids = self.make_table_with_properties()
        table_id = table.id
        self.provider.set_property("table", self.provider.get_type_table(TABLE).id, "contact", "Somebody Else")

        self.provider.delete_type_table(table)

        self.assertEqual(self.owner_rows("table", table_id), 0)
        for column_id in column_ids:
            self.assertEqual(self.owner_rows("column", column_id), 0)
        self.assertEqual(self.owner_rows("table", self.provider.get_type_table(TABLE).id), 1)  # others stay
        record = self.provider.get_log_records(limit=1)[0]
        self.assertEqual(record.action, "delete")
        self.assertIn("with 4 properties", record.description)

    def test_delete_directory_deletes_its_properties(self):
        directory = self.provider.create_directory("prop_dir", "/test")
        directory_id = directory.id
        self.provider.set_property("directory", directory_id, "contact", "Jane Doe")

        self.provider.delete_directory(directory)

        self.assertEqual(self.owner_rows("directory", directory_id), 0)
        self.assertIn("with 1 property", self.provider.get_log_records(limit=1)[0].description)

    def test_delete_variation_deletes_its_properties(self):
        variation = self.provider.create_variation("prop_var", "for properties", "default")
        variation_id = variation.id
        self.provider.set_property("variation", variation_id, "contact", "Jane Doe")
        self.provider.set_property("variation", variation_id, "purpose", "tests")

        self.provider.delete_variation(variation)

        self.assertEqual(self.owner_rows("variation", variation_id), 0)
        self.assertIn("with 2 properties", self.provider.get_log_records(limit=1)[0].description)

    def test_delete_without_properties_logs_as_before(self):
        directory = self.provider.create_directory("plain_dir", "/test")
        self.provider.delete_directory(directory)
        self.assertEqual(self.provider.get_log_records(limit=1)[0].description, "Deleted directory '/test/plain_dir'")

    def test_failed_table_delete_keeps_the_table_and_its_properties(self):
        table, column_ids = self.make_table_with_properties()
        table_id = table.id

        with mock.patch.object(self.provider, "create_log_record", side_effect=RuntimeError("log failed")):
            self.assertRaises(RuntimeError, self.provider.delete_type_table, table)

        self.assertEqual(self.provider.get_type_table("/test/test_vars/prop_table").id, table_id)
        self.assertEqual(self.owner_rows("table", table_id), 2)
        for column_id in column_ids:
            self.assertEqual(self.owner_rows("column", column_id), 1)

    def test_failed_directory_delete_keeps_the_directory_and_its_properties(self):
        directory = self.provider.create_directory("prop_dir", "/test")
        directory_id = directory.id
        self.provider.set_property("directory", directory_id, "contact", "Jane Doe")

        with self.failing_commit():
            self.assertRaises(RuntimeError, self.provider.delete_directory, directory)

        self.provider._load_dirs()
        self.assertEqual(self.provider.get_directory("/test/prop_dir").id, directory_id)
        self.assertEqual(self.owner_rows("directory", directory_id), 1)

    def test_failed_variation_delete_keeps_the_variation_and_its_properties(self):
        variation = self.provider.create_variation("prop_var", "for properties", "default")
        variation_id = variation.id
        self.provider.set_property("variation", variation_id, "contact", "Jane Doe")

        with self.failing_commit():
            self.assertRaises(RuntimeError, self.provider.delete_variation, variation)

        self.assertEqual(self.provider.get_variation("prop_var").id, variation_id)
        self.assertEqual(self.owner_rows("variation", variation_id), 1)

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

    # tags
    def test_cli_tag_set_get_ls_and_show(self):
        self.provider.create_tag("pass1", "default", comment="for properties")
        self.run_cli("prop set @pass1 software eicrecon-1.42.0")
        self.run_cli("prop set @pass1 doi 10.5281/zenodo.1234567")
        self.assertEqual(self.run_cli("prop get @pass1 software").strip(), "eicrecon-1.42.0")
        self.assertEqual(self.run_cli("prop ls @pass1").strip().splitlines(),
                         ["doi = 10.5281/zenodo.1234567", "software = eicrecon-1.42.0"])
        tag = self.provider.get_tag("pass1")
        self.assertEqual(self.provider.get_property("tag", tag.id, "doi").value, "10.5281/zenodo.1234567")
        self.assertIn("software   :  eicrecon-1.42.0", self.run_cli("tag pass1"))
        self.assertIn("doi        :  10.5281/zenodo.1234567", self.run_cli("info @pass1"))
        self.assertIn("    software = eicrecon-1.42.0", self.run_cli("tag -l"))
        self.assertNotIn("software =", self.run_cli("tag"))

    def test_cli_tag_errors(self):
        self.provider.create_tag("pass1", "default", comment="for properties")
        self.assertRaises(ObjectIsNotFoundInDbError, self.run_cli, "prop set @no_such_tag doi x")
        self.assertRaises(ValueError, self.run_cli, "prop set -v @pass1 doi x")

    def test_delete_tag_deletes_its_properties(self):
        tag = self.provider.create_tag("pass1", "default", comment="for properties")
        tag_id = tag.id
        self.provider.set_property("tag", tag_id, "software", "eicrecon-1.42.0")
        self.provider.delete_tag("pass1")
        self.assertEqual(self.owner_rows("tag", tag_id), 0)
        self.assertIn("with 1 property", self.provider.get_log_records(limit=1)[0].description)

    # vocabulary
    def test_a_name_outside_the_vocabulary_warns_and_is_set(self):
        text = self.run_cli("prop set {0} owner_group FCAL".format(TABLE))
        self.assertIn("'owner_group' is not a standard property name for a table", text)
        self.assertEqual(self.run_cli("prop get {0} owner_group".format(TABLE)).strip(), "FCAL")
        self.assertNotIn("not a standard", self.run_cli("prop set {0} contact Jane".format(TABLE)))
        self.assertNotIn("not a standard", self.run_cli("prop set {0} x y --free".format(TABLE)))

    def test_the_instance_extends_the_vocabulary(self):
        self.run_cli("prop set --instance property_names owner_group, run_period")
        self.assertNotIn("not a standard", self.run_cli("prop set {0} owner_group FCAL".format(TABLE)))
        self.assertNotIn("not a standard", self.run_cli("prop set -v default run_period 2026"))
        self.assertIn("not a standard", self.run_cli("prop set {0} other x".format(TABLE)))

    def test_info_without_properties_has_no_block(self):
        self.assertNotIn("Properties:", self.run_cli("info " + TABLE))


if __name__ == "__main__":
    unittest.main()
