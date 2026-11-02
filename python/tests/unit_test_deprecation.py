"""Deprecation of directories, type tables and variations: the provider methods, ls, info and deprecate.

A deprecated object stays fully usable; only listings that ask for it (include_deprecated=False) and ls leave
it out. Runs on the SQLite test database that ccdb.testing recreates for each test.
"""
import logging
import sys
import unittest
from io import StringIO

import ccdb.cmd.themes
from ccdb import AlchemyProvider
from ccdb import testing as helper
from ccdb.cmd.cli_manager import CliManager, CCDB_EXCEPTIONS_THROW
from ccdb.model import LogRecord


TABLE = "/test/test_vars/test_table"
TABLE_DIR = "/test/test_vars"
TABLE_NAME = "test_table"
DIR = "/test/test_vars"
VARIATION = "test"
COMMENT = "Use /test/test_vars/test_table2"

logger = logging.getLogger("ccdb")


class DeprecationTestBase(unittest.TestCase):

    def setUp(self):
        helper.recreate_test_sqlite_db()
        self.addCleanup(helper.clean_test_sqlite_db)

        self.provider = AlchemyProvider()
        self.provider.connect(helper.sqlite_test_connection_str)
        self.provider.authentication.current_user_name = "test_user"
        self.provider.logging_enabled = True
        self.addCleanup(self.provider.disconnect)

    def log_count(self):
        return self.provider.session.query(LogRecord).count()

    def last_log(self):
        return self.provider.session.query(LogRecord).order_by(LogRecord.id.desc()).first()


class ProviderDeprecationTests(DeprecationTestBase):

    def test_deprecate_sets_fields_and_logs(self):
        """deprecate fills the four fields and writes one log record, for each kind of object"""
        objects = [self.provider.get_type_table(TABLE),
                   self.provider.get_directory(DIR),
                   self.provider.get_variation(VARIATION)]
        for obj in objects:
            with self.subTest(obj=type(obj).__name__):
                before = self.log_count()
                self.provider.deprecate(obj, COMMENT)
                self.assertEqual(self.log_count(), before + 1)

                self.provider.session.expire_all()
                self.assertTrue(obj.is_deprecated)
                self.assertEqual(obj.deprecation_comment, COMMENT)
                self.assertIsNotNone(obj.deprecated_time)
                self.assertEqual(obj.deprecated_by_user_id, self.provider.get_current_user().id)

                record = self.last_log()
                self.assertIn("Deprecated", record.description)
                self.assertIn("|" + obj.__tablename__ + str(obj.id) + "|", record.affected_ids)
                self.assertEqual(record.comment, COMMENT)

    def test_comment_is_required(self):
        table = self.provider.get_type_table(TABLE)
        before = self.log_count()
        for comment in (None, "", "   "):
            with self.subTest(comment=comment):
                with self.assertRaises(ValueError):
                    self.provider.deprecate(table, comment)
        self.provider.session.expire_all()
        self.assertFalse(table.is_deprecated)
        self.assertEqual(self.log_count(), before)

    def test_undeprecate_clears_fields_and_logs(self):
        objects = [self.provider.get_type_table(TABLE),
                   self.provider.get_directory(DIR),
                   self.provider.get_variation(VARIATION)]
        for obj in objects:
            with self.subTest(obj=type(obj).__name__):
                self.provider.deprecate(obj, COMMENT)
                before = self.log_count()
                self.provider.undeprecate(obj)
                self.assertEqual(self.log_count(), before + 1)
                self.assertIn("Undeprecated", self.last_log().description)

                self.provider.session.expire_all()
                self.assertFalse(obj.is_deprecated)
                self.assertIsNone(obj.deprecated_by_user_id)
                self.assertIsNone(obj.deprecated_time)
                self.assertIsNone(obj.deprecation_comment)

    def test_listings_return_everything_by_default(self):
        table = self.provider.get_type_table(TABLE)
        directory = self.provider.get_directory(DIR)
        variation = self.provider.get_variation(VARIATION)
        for obj in (table, directory, variation):
            self.provider.deprecate(obj, COMMENT)

        self.assertIn(table.id, [t.id for t in self.provider.get_type_tables(TABLE_DIR)])
        self.assertIn(table.id, [t.id for t in self.provider.search_type_tables("*")])
        self.assertIn(directory.id, [d.id for d in self.provider.get_directories("/test")])
        self.assertIn(directory.id, [d.id for d in self.provider.search_directories("*", "/test")])
        self.assertIn(variation.name, [v.name for v in self.provider.get_variations()])

    def test_listings_hide_deprecated_on_request(self):
        table = self.provider.get_type_table(TABLE)
        directory = self.provider.get_directory(DIR)
        variation = self.provider.get_variation(VARIATION)
        for obj in (table, directory, variation):
            self.provider.deprecate(obj, COMMENT)

        tables = self.provider.get_type_tables(TABLE_DIR, include_deprecated=False)
        self.assertNotIn(table.id, [t.id for t in tables])
        self.assertTrue(tables, "the other tables of the directory stay listed")
        self.assertNotIn(table.id, [t.id for t in self.provider.search_type_tables("*", include_deprecated=False)])
        self.assertNotIn(directory.id,
                         [d.id for d in self.provider.get_directories("/test", include_deprecated=False)])
        self.assertNotIn(directory.id,
                         [d.id for d in self.provider.search_directories("*", "/test", include_deprecated=False)])
        variations = [v.name for v in self.provider.get_variations(include_deprecated=False)]
        self.assertNotIn(variation.name, variations)
        self.assertIn("default", variations)

    def test_direct_access_works(self):
        """Getting a deprecated object by name and requesting its data are unchanged"""
        table = self.provider.get_type_table(TABLE)
        self.provider.deprecate(table, COMMENT)
        self.provider.deprecate(self.provider.get_directory(DIR), COMMENT)
        self.provider.deprecate(self.provider.get_variation(VARIATION), COMMENT)

        self.assertEqual(self.provider.get_type_table(TABLE).id, table.id)
        self.assertEqual(self.provider.get_directory(DIR).path, DIR)
        self.assertEqual(self.provider.get_variation(VARIATION).name, VARIATION)
        assignment = self.provider.get_assignment(TABLE, 100, "default")
        self.assertIsNotNone(assignment)
        self.assertTrue(assignment.constant_set.data_table)


class CliDeprecationTests(DeprecationTestBase):

    def setUp(self):
        super().setUp()
        self.cli = CliManager()
        self.cli.exception_handling = CCDB_EXCEPTIONS_THROW
        self.cli.force_exceptions = True
        self.cli.theme = ccdb.cmd.themes.NoColorTheme()
        self.cli.connection_string = helper.sqlite_test_connection_str
        self.cli.context.user_name = "test_user"
        self.cli.register_utilities()
        self.addCleanup(self.cli.provider.disconnect)

        # ls and deprecate write through logging, cat and info through print
        self.output = StringIO()
        saved_stdout = sys.stdout
        sys.stdout = self.output
        self.addCleanup(setattr, sys, "stdout", saved_stdout)
        handler = logging.StreamHandler(self.output)
        logger.addHandler(handler)
        self.addCleanup(logger.removeHandler, handler)
        saved_level = logger.level
        logger.setLevel(logging.INFO)
        self.addCleanup(logger.setLevel, saved_level)

    def run_cli(self, command_line):
        self.output.seek(0)
        self.output.truncate()
        self.cli.process_command_line(command_line)
        return self.output.getvalue()

    def cli_table(self):
        provider = self.cli.provider
        provider.session.expire_all()
        return provider.get_type_table(TABLE)

    def test_deprecate_table_by_name_without_flag(self):
        self.run_cli('deprecate {} -c "{}"'.format(TABLE, COMMENT))
        table = self.cli_table()
        self.assertTrue(table.is_deprecated)
        self.assertEqual(table.deprecation_comment, COMMENT)

    def test_name_without_flag_falls_back_to_directory(self):
        self.run_cli('deprecate {} -c "{}"'.format(DIR, COMMENT))
        provider = self.cli.provider
        provider.session.expire_all()
        self.assertTrue(provider.get_directory(DIR).is_deprecated)

    def test_variation_flag(self):
        self.run_cli('deprecate {} -v -c "{}"'.format(VARIATION, COMMENT))
        provider = self.cli.provider
        provider.session.expire_all()
        self.assertTrue(provider.get_variation(VARIATION).is_deprecated)

    def test_cli_comment_is_required(self):
        with self.assertRaises(ValueError):
            self.run_cli('deprecate {}'.format(TABLE))
        self.assertFalse(self.cli_table().is_deprecated)

    def test_undo(self):
        self.run_cli('deprecate {} -t -c "{}"'.format(TABLE, COMMENT))
        self.run_cli('deprecate --undo {} -t'.format(TABLE))
        table = self.cli_table()
        self.assertFalse(table.is_deprecated)
        self.assertIsNone(table.deprecation_comment)
        self.assertIsNone(table.deprecated_time)

    def test_ls_hides_and_ls_a_shows(self):
        self.assertIn(TABLE_NAME, self.run_cli("ls " + TABLE_DIR))
        self.run_cli('deprecate {} -c "{}"'.format(TABLE, COMMENT))

        listed = self.run_cli("ls " + TABLE_DIR).split()
        self.assertNotIn(TABLE_NAME, listed)

        listed_all = self.run_cli("ls -a " + TABLE_DIR)
        self.assertIn(TABLE_NAME + " (deprecated)", listed_all)
        self.assertNotIn(COMMENT, listed_all)

        extended = self.run_cli("ls -a -l " + TABLE_DIR)
        self.assertIn(TABLE_NAME + " (deprecated)", extended)
        self.assertIn(COMMENT, extended)
        self.assertIn(self.cli_table().deprecated_time.strftime("%Y-%m-%d"), extended)

    def test_ls_hides_deprecated_directory(self):
        self.run_cli('deprecate {} -d -c "{}"'.format(DIR, COMMENT))
        self.assertNotIn("test_vars", self.run_cli("ls /test").split())
        self.assertIn("test_vars (deprecated)", self.run_cli("ls -a /test"))
        self.assertNotIn("test_vars", self.run_cli("ls -x"))
        self.assertIn("test_vars (deprecated)", self.run_cli("ls -x -a"))
        self.assertNotIn(DIR, self.run_cli("ls -d"))
        self.assertIn(DIR + " (deprecated)", self.run_cli("ls -d -a"))

    def test_ls_hides_deprecated_variation(self):
        self.run_cli('deprecate {} -v -c "{}"'.format(VARIATION, COMMENT))
        self.assertNotIn(VARIATION, self.run_cli("ls -v").split())
        self.assertIn(VARIATION + " (deprecated)", self.run_cli("ls -v -a"))

    def test_cat_vers_info_work_on_deprecated_table(self):
        before_cat = self.run_cli("cat " + TABLE)
        before_vers = self.run_cli("vers " + TABLE)
        self.run_cli('deprecate {} -c "{}"'.format(TABLE, COMMENT))

        self.assertEqual(self.run_cli("cat " + TABLE), before_cat)
        self.assertEqual(self.run_cli("vers " + TABLE), before_vers)

        info = self.run_cli("info " + TABLE)
        self.assertIn("Deprecated", info)
        self.assertIn(COMMENT, info)
        self.assertIn(self.cli_table().deprecated_time.strftime("%Y-%m-%d"), info)

    def test_info_has_no_deprecation_line_for_a_current_table(self):
        self.assertNotIn("Deprecated", self.run_cli("info " + TABLE))

    def test_info_on_deprecated_directory_and_variation(self):
        self.run_cli('deprecate {} -d -c "{}"'.format(DIR, COMMENT))
        self.run_cli('deprecate {} -v -c "{}"'.format(VARIATION, COMMENT))
        self.assertIn(COMMENT, self.run_cli("info -d " + DIR))
        self.assertIn(COMMENT, self.run_cli("info -v " + VARIATION))


if __name__ == '__main__':
    unittest.main()
