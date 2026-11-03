"""The ePIC-shaped demo tables (scripts/demo/make_epic_tables.py): deterministic, complete, and showing what the demo
shows: constants that switch at run 1000, a variation for simulation, a tag before a late correction, a resources table,
units and properties."""
import hashlib
import importlib.util
import os
import sqlite3
import tempfile
import unittest

import ccdb
from ccdb import AlchemyProvider, testing


def _load_generator():
    path = os.path.join(ccdb.get_ccdb_home_path(), "scripts", "demo", "make_epic_tables.py")
    spec = importlib.util.spec_from_file_location("ccdb_scripts_demo_make_epic_tables", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


generator = _load_generator()
TOF = "/epic/TOFBarrel/lgad_calibration"


def dump_hash(path):
    with sqlite3.connect(path) as connection:
        return hashlib.sha256("\n".join(connection.iterdump()).encode("utf-8")).hexdigest()


class DemoTablesTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.restore = testing.pin_time_zone("America/New_York")     # the generator runs in UTC whatever the caller's zone
        cls.directory = tempfile.TemporaryDirectory()
        cls.path = os.path.join(cls.directory.name, "demo.sqlite")
        cls.summary = generator.build("sqlite:///" + cls.path)
        cls.restore()
        cls.restore = testing.pin_time_zone("UTC")
        cls.provider = AlchemyProvider()
        cls.provider.connect("sqlite:///" + cls.path)

    @classmethod
    def tearDownClass(cls):
        cls.provider.disconnect()
        cls.restore()
        cls.directory.cleanup()

    def values(self, request):
        return self.provider.get_assignment_by_request(request).constant_set.data_table

    def test_two_builds_hold_the_same_rows(self):
        other = os.path.join(self.directory.name, "again.sqlite")
        restore = testing.pin_time_zone("Asia/Kolkata")
        try:
            generator.build("sqlite:///" + other)
        finally:
            restore()
        self.assertEqual(dump_hash(other), dump_hash(self.path))

    def test_counts(self):
        self.assertEqual(self.summary["tables"], len(generator.TABLES) + 1)
        self.assertEqual(self.summary["assignments"], 3 * len(generator.TABLES) + 2)
        self.provider.get_root_directory()
        self.assertEqual(len(self.provider.search_type_tables("*", "/epic/TOFBarrel")), 1)

    def test_constants_switch_at_run_1000_and_the_tag_keeps_the_old_offset(self):
        first, second = self.values(TOF + ":500")[0], self.values(TOF + ":1500")[0]
        self.assertEqual(first, ["1.175844e-06", "0.0", "0.024319882", "0.04314"])
        self.assertEqual(second[0], "1.18760244e-06")
        self.assertEqual(second[3], "0.05114")                                 # the late correction
        self.assertEqual(self.values(TOF + ":1500@campaign_demo")[0][3], "0.04314")
        self.assertEqual(self.values(TOF + ":1500:mc")[0], first)            # simulation: EICrecon's values

    def test_units_properties_and_the_resources_table(self):
        table = self.provider.get_type_table("/epic/HCal/adc_calib")
        self.assertEqual({column.name: column.units for column in table.columns}["dyRangeADC"], "MeV")
        properties = {each.name: each.value for each in self.provider.get_properties("table", table.id)}
        self.assertTrue(properties["source_url"].startswith(generator.EICRECON))
        self.assertEqual(self.provider.get_property("instance", 0, "experiment").value, "ePIC (demo)")
        url, sha256, size = self.values("/epic/EcalEndcapN/pi_rejection_model:1000")[0]
        self.assertEqual((url, sha256, int(size)), (generator.RESOURCE_PATH, hashlib.sha256(generator.RESOURCE_BYTES).hexdigest(),
                                                    len(generator.RESOURCE_BYTES)))


if __name__ == '__main__':
    unittest.main()
