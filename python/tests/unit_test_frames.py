"""ccdb.frames.to_dataframe on the demo tables: typed columns, units and the assignment in the frame's attributes, a
tag request, and the polars frame where polars is installed. Skipped without pandas (the frames extra)."""
import importlib.util
import os
import tempfile
import unittest

import ccdb
from ccdb import AlchemyProvider, testing
from ccdb.frames import to_dataframe

try:
    import pandas
except ImportError:  # the frames extra is not installed
    pandas = None


def _load_generator():
    path = os.path.join(ccdb.get_ccdb_home_path(), "scripts", "demo", "make_epic_tables.py")
    spec = importlib.util.spec_from_file_location("ccdb_scripts_demo_make_epic_tables", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@unittest.skipIf(pandas is None, "the frames extra (pandas) is not installed")
class FramesTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.restore = testing.pin_time_zone("UTC")
        cls.directory = tempfile.TemporaryDirectory()
        connection = "sqlite:///" + os.path.join(cls.directory.name, "demo.sqlite")
        _load_generator().build(connection)
        cls.provider = AlchemyProvider()
        cls.provider.connect(connection)

    @classmethod
    def tearDownClass(cls):
        cls.provider.disconnect()
        cls.directory.cleanup()
        cls.restore()

    def test_types_values_and_attributes(self):
        frame = to_dataframe(self.provider, "/epic/EcalBarrel/adc_calib:1500")
        self.assertEqual(list(frame.columns), ["subsystem", "capADC", "dyRangeADC", "pedMeanADC", "pedSigmaADC",
                                               "resolutionTDC", "thresholdValue", "sampFrac"])
        self.assertEqual(str(frame["capADC"].dtype), "int64")
        self.assertEqual(str(frame["sampFrac"].dtype), "float64")
        self.assertEqual(frame["subsystem"].tolist(), ["ScFi", "Imaging"])
        assignment = self.provider.get_assignment("/epic/EcalBarrel/adc_calib", 1500, "default")
        self.assertEqual(frame["sampFrac"].tolist(), [float(row[7]) for row in assignment.constant_set.data_table])
        self.assertEqual(frame.attrs["units"]["dyRangeADC"], "MeV")
        self.assertEqual(frame.attrs["units"]["sampFrac"], "")
        self.assertEqual(frame.attrs["table"], "/epic/EcalBarrel/adc_calib")
        self.assertEqual(frame.attrs["assignment"]["id"], assignment.id)
        self.assertEqual((frame.attrs["assignment"]["run_min"], frame.attrs["assignment"]["run_max"]), (1000, 1999))

    def test_tag_request(self):
        tagged = to_dataframe(self.provider, "/epic/TOFBarrel/lgad_calibration:1500@campaign_demo")
        newest = to_dataframe(self.provider, "/epic/TOFBarrel/lgad_calibration:1500")
        self.assertEqual(tagged["tIntercept"].tolist(), [0.04314])
        self.assertEqual(newest["tIntercept"].tolist(), [0.05114])

    def test_mc_variation(self):
        frame = to_dataframe(self.provider, "/epic/EcalBarrel/adc_calib:1500:mc")
        self.assertEqual(frame.attrs["assignment"]["variation"], "mc")

    def test_polars(self):
        try:
            import polars
        except ImportError:
            self.skipTest("polars is not installed")
        frame = to_dataframe(self.provider, "/epic/EcalBarrel/adc_calib:1500", library="polars")
        self.assertEqual(frame.schema["capADC"], polars.Int64)
        self.assertEqual(frame["subsystem"].to_list(), ["ScFi", "Imaging"])

    def test_unknown_library(self):
        with self.assertRaises(ValueError):
            to_dataframe(self.provider, "/epic/EcalBarrel/adc_calib:1500", library="arrow")


if __name__ == "__main__":
    unittest.main()
