"""Column units: the mktbl 'name=type:units' syntax, the provider, 'info' and the dump header"""

import os
import shutil
import tempfile
import unittest

import ccdb.cmd.themes
from ccdb import testing as helper
from ccdb.cmd.cli_manager import CliManager, CCDB_EXCEPTIONS_THROW
from ccdb.table_file import read_ccdb_text_file, parse_units_meta


class ColumnUnitsTests(unittest.TestCase):

    def setUp(self):
        helper.recreate_test_sqlite_db()
        self.context = CliManager()
        self.context.exception_handling = CCDB_EXCEPTIONS_THROW
        self.context.theme = ccdb.cmd.themes.NoColorTheme()
        self.context.connection_string = helper.sqlite_test_connection_str
        self.context.user_name = "python_tests"
        self.context.register_utilities()
        self.context.provider.authentication.current_user_name = "test_user"
        self.provider = self.context.provider
        self.provider.connect(helper.sqlite_test_connection_str)
        self.tmp_dir = tempfile.mkdtemp()

    def tearDown(self):
        self.provider.disconnect()
        shutil.rmtree(self.tmp_dir, ignore_errors=True)
        helper.clean_test_sqlite_db()

    def run_cmd(self, command_line):
        with helper.captured_output() as (out, err):
            self.context.process_command_line(command_line)
        return out.getvalue()

    def columns_of(self, path):
        table = self.provider.get_type_table(path)
        return [(c.name, c.type, c.units) for c in table.columns]

    def write_file(self, name, text):
        path = os.path.join(self.tmp_dir, name)
        with open(path, "w") as f:
            f.write(text)
        return path

    def test_mktbl_with_units(self):
        self.run_cmd("mktbl /test/units_t -r 1 gain=double:MeV time=:ns n=int 'width=double:counts per s' #units")
        self.assertEqual(self.columns_of("/test/units_t"),
                         [("gain", "double", "MeV"),
                          ("time", "double", "ns"),
                          ("n", "int", None),
                          ("width", "double", "counts per s")])

    def test_mktbl_quantity_with_units(self):
        """Every column a quantity creates gets the units"""
        self.run_cmd("mktbl /test/units_q -r 1 3ch=double:mV")
        self.assertEqual(self.columns_of("/test/units_q"),
                         [("ch0", "double", "mV"), ("ch1", "double", "mV"), ("ch2", "double", "mV")])

    def test_mktbl_old_syntax(self):
        """'name' and 'name=type' are still valid and leave the columns without units"""
        self.run_cmd("mktbl /test/old_t -r 2 x y=int s=string 2val=double #old style")
        self.assertEqual(self.columns_of("/test/old_t"),
                         [("x", "double", None), ("y", "int", None), ("s", "string", None),
                          ("val0", "double", None), ("val1", "double", None)])

    def test_mktbl_bad_type_with_units(self):
        with self.assertRaises(ValueError):
            self.run_cmd("mktbl /test/bad_t -r 1 gain=float:MeV")

    def test_provider_pairs_and_triples(self):
        """(name, type) pairs and (name, type, units) triples mix in one call"""
        self.provider.create_type_table("mixed_t", "/test", 1,
                                        [("a", "double"), ("b", "int", "cm"), ("c", "double", "")], "mixed")
        self.assertEqual(self.columns_of("/test/mixed_t"),
                         [("a", "double", None), ("b", "int", "cm"), ("c", "double", None)])

    def test_provider_too_long_units(self):
        with self.assertRaises(ValueError):
            self.provider.create_type_table("long_t", "/test", 1, [("a", "double", "x" * 65)], "long")

    def test_info_shows_units(self):
        self.run_cmd("mktbl /test/units_t -r 1 gain=double:MeV n=int")
        text = self.run_cmd("info /test/units_t")
        lines = text.splitlines()
        gain_line = [ln for ln in lines if ln.rstrip().endswith("gain [MeV]")]
        n_line = [ln for ln in lines if ln.rstrip().endswith(": n")]
        self.assertEqual(len(gain_line), 1, text)
        self.assertEqual(len(n_line), 1, text)
        self.assertIn("double", gain_line[0])

    def test_dump_header_shows_units(self):
        self.run_cmd("mktbl /test/units_t -r 2 gain=double:MeV n=int 'width=double:counts per s'")
        data_file = self.write_file("in.txt", "#calibration of the day\n1.5 3 0.1\n2.5 4 0.2\n")
        self.run_cmd("add /test/units_t -r 0- " + data_file)

        dumped = self.run_cmd("dump /test/units_t")
        lines = [ln.strip() for ln in dumped.strip().splitlines()]
        self.assertEqual(lines[0], "#calibration of the day")
        self.assertEqual(lines[1], "#meta units: gain=MeV 'width=counts per s'")
        self.assertEqual([ln.split() for ln in lines[2:]], [["1.5", "3", "0.1"], ["2.5", "4", "0.2"]])

        # the text reader keeps the line out of the comments and the data, and the units come back
        dump_file = self.write_file("dump.txt", dumped)
        dom = read_ccdb_text_file(dump_file)
        self.assertEqual(dom.comment_lines, ["calibration of the day"])
        self.assertEqual(len(dom.rows), 2)
        self.assertEqual(parse_units_meta(dom.metas["units"]), {"gain": "MeV", "width": "counts per s"})

        # adding the dump back does not grow the assignment comment with the units line
        self.run_cmd("add /test/units_t -r 0- " + dump_file)
        dumped_again = self.run_cmd("dump /test/units_t")
        self.assertEqual(dumped_again, dumped)

    def test_dump_without_units_has_no_meta_line(self):
        """A table without units dumps exactly as before units existed"""
        self.run_cmd("mktbl /test/plain_t -r 2 x y=int")
        data_file = self.write_file("plain.txt", "#plain\n1.5 3\n2.5 4\n")
        self.run_cmd("add /test/plain_t -r 0- " + data_file)
        dumped = self.run_cmd("dump /test/plain_t")
        self.assertNotIn("#meta", dumped)
        lines = [ln.strip() for ln in dumped.strip().splitlines()]
        self.assertEqual(lines[0], "#plain")
        self.assertEqual([ln.split() for ln in lines[1:]], [["1.5", "3"], ["2.5", "4"]])

    def test_info_of_dumped_file(self):
        """'info -f' on a dump with a units line lists it among the meta data"""
        path = self.write_file("meta.txt", "#c\n#meta units: gain=MeV\n1 2\n")
        # dict iteration used to unpack the key string itself, so any '#meta' line raised here
        self.run_cmd("info -f " + path)

    def test_units_with_line_breaks_are_refused(self):
        """A line break in units would split the #meta units line of a dump"""
        for units in ("Me\nV", "Me\rV"):
            with self.assertRaises(ValueError):
                self.provider.create_type_table("t_units_break", "/test", 1, [("x", "double", units)], "c")


if __name__ == '__main__':
    unittest.main()
