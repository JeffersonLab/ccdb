"""UCUM units (ccdb.ucum): the check, the warning of `mktbl`, AlchemyProvider.set_column_units and the readiness count.

Runs on the SQLite test database that ccdb.testing recreates (CCDB_TEST_SQLITE_CONNECTION) where it needs one.
"""
import logging
import sys
import unittest
from io import StringIO

import ccdb.cmd.themes
from ccdb import testing as helper
from ccdb.cmd.cli_manager import CliManager, CCDB_EXCEPTIONS_THROW
from ccdb.errors import AnonymousUserForbiddenError, ObjectIsNotFoundInDbError
from ccdb.model import LogRecord
from ccdb.readiness import profile
from ccdb.ucum import is_ucum

# Units of calibration tables in detector physics, as UCUM writes them
UCUM = ["MeV", "GeV", "keV", "eV", "ns", "ps", "us", "ms", "s", "mm", "cm", "um", "m", "rad", "mrad", "deg", "T", "kG",
        "V", "mV", "kV", "pC", "fC", "nA", "Hz", "MHz", "cm2", "mm2", "cm-1", "1/s", "/s", "s-1", "GeV/[c]", "MeV/[c]2",
        "{ADC}", "{counts}", "{channel}", "1", "%", "Cel", "K", "ns/cm", "cm/ns", "MeV/cm", "g/cm3", "10*3", "10*-6",
        "10^3", "{ADC}/MeV", "MeV/{ADC}", "[c]", "mol", "kg", "g.cm-2", "(MeV/[c]).cm"]
# What people type that UCUM can't read
NOT_UCUM = ["Mev", "nsec", "sec", "GeV/c", "counts", "ADC", "", " MeV", "MeV ", "meters", "cm^2", "MeV/", "/", "{ADC",
            "deg C", "KeV", "(MeV/[c])2", None]

logger = logging.getLogger("ccdb")


class UcumTest(unittest.TestCase):

    def test_units_physics_tables_use(self):
        for units in UCUM:
            with self.subTest(units=units):
                self.assertTrue(is_ucum(units))

    def test_spellings_ucum_refuses(self):
        for units in NOT_UCUM:
            with self.subTest(units=units):
                self.assertFalse(is_ucum(units))


class UnitsInTheDatabaseTest(unittest.TestCase):

    def setUp(self):
        helper.recreate_test_sqlite_db()
        self.cli = CliManager()
        self.cli.exception_handling = CCDB_EXCEPTIONS_THROW
        self.cli.force_exceptions = True
        self.cli.theme = ccdb.cmd.themes.NoColorTheme()
        self.cli.connection_string = helper.sqlite_test_connection_str
        self.cli.context.user_name = "test_user"
        self.cli.register_utilities()
        self.assertTrue(self.cli.check_connection(self.cli.context.commands["mktbl"]))
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
        self.output.seek(0)
        self.output.truncate()
        self.cli.process_command_line(command_line)
        return self.output.getvalue()

    def test_mktbl_warns_and_stores_as_written(self):
        text = self.run_cli('mktbl /test/units_table -r 1 a=double:Mev b=double:ns c=int:{ADC} #units test')
        self.assertIn("Units 'Mev' of column 'a' are not UCUM", text)
        self.assertNotIn("column 'b'", text)
        self.assertNotIn("column 'c'", text)
        table = self.provider.get_type_table("/test/units_table")
        self.assertEqual([column.units for column in table.columns], ["Mev", "ns", "{ADC}"])

    def test_set_column_units_logs_the_change(self):
        before = self.provider.session.query(LogRecord).count()
        column = self.provider.set_column_units("/test/test_vars/test_table", "x", "MeV")
        self.assertEqual(column.units, "MeV")
        self.assertEqual(self.provider.session.query(LogRecord).count(), before + 1)
        record = self.provider.get_log_records(limit=1)[0]
        self.assertIn("Changed units of column 'x' of table '/test/test_vars/test_table' from '' to 'MeV'", record.description)
        self.provider.set_column_units("/test/test_vars/test_table", "x", None)
        self.assertIsNone(self.provider.get_type_table("/test/test_vars/test_table").columns[0].units)

    def test_set_column_units_errors(self):
        with self.assertRaises(ObjectIsNotFoundInDbError):
            self.provider.set_column_units("/test/test_vars/test_table", "no_such_column", "MeV")
        with self.assertRaises(ValueError):
            self.provider.set_column_units("/test/test_vars/test_table", "x", "m" * 65)
        self.provider.authentication.current_user_name = "anonymous"
        with self.assertRaises(AnonymousUserForbiddenError):
            self.provider.set_column_units("/test/test_vars/test_table", "x", "MeV")

    def test_the_profile_counts_ucum_units(self):
        self.provider.set_column_units("/test/test_vars/test_table", "x", "MeV")
        self.provider.set_column_units("/test/test_vars/test_table", "y", "Mev")
        self.provider.set_column_units("/test/test_vars/test_table", "z", "{ADC}")
        numbers = profile(self.provider)
        self.assertEqual(numbers["metadata"]["columns_with_units"], 3)
        self.assertEqual(numbers["units"]["columns_with_ucum_units"], 2)


if __name__ == "__main__":
    unittest.main()
