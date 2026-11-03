"""`ccdb export parquet` (ccdb/cmd/commands/export.py) on the demo tables: the file read back with pyarrow equals what the
provider returns, row by row, with the assignment columns, the column types and the units; -r, -v and --tag select
the assignments as cat and vers do; the DuckDB and polars recipes of docs/apis/analysis.md run where installed.
Skipped without the export extra (pyarrow)."""
import datetime
import importlib.util
import os
import tempfile
import unittest

import ccdb
import ccdb.cmd.themes
from ccdb import AlchemyProvider, testing
from ccdb.cmd.cli_manager import CliManager, CCDB_EXCEPTIONS_THROW
from ccdb.frames import assignment_metadata, typed_columns


try:
    import pyarrow.parquet
except ImportError:  # the export extra is not installed
    pyarrow = None

TABLE = "/epic/EcalBarrel/adc_calib"
TOF = "/epic/TOFBarrel/lgad_calibration"


def _load_generator():
    path = os.path.join(ccdb.get_ccdb_home_path(), "scripts", "demo", "make_epic_tables.py")
    spec = importlib.util.spec_from_file_location("ccdb_scripts_demo_make_epic_tables", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@unittest.skipIf(pyarrow is None, "the export extra (pyarrow) is not installed")
class ExportParquetTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.restore = testing.pin_time_zone("UTC")
        cls.directory = tempfile.TemporaryDirectory()
        cls.connection = "sqlite:///" + os.path.join(cls.directory.name, "demo.sqlite")
        _load_generator().build(cls.connection)
        cls.provider = AlchemyProvider()
        cls.provider.connect(cls.connection)

    @classmethod
    def tearDownClass(cls):
        cls.provider.disconnect()
        cls.directory.cleanup()
        cls.restore()

    def export(self, arguments):
        output = tempfile.mkdtemp(dir=self.directory.name)
        cli = CliManager()
        cli.exception_handling = CCDB_EXCEPTIONS_THROW
        cli.theme = ccdb.cmd.themes.NoColorTheme()
        cli.connection_string = self.connection
        cli.user_name = "python_tests"
        cli.register_utilities()
        with testing.captured_output():
            cli.process_command_line("export parquet {0} -o {1}".format(arguments, output))
        cli.provider.disconnect()
        return output

    def read(self, output, table=TABLE):
        return pyarrow.parquet.read_table(os.path.join(output, table.strip("/").replace("/", ".") + ".parquet"))

    def expected_rows(self, assignments):
        rows = []
        for assignment in assignments:
            meta = assignment_metadata(assignment)
            columns = typed_columns(assignment)
            for index in range(len(columns[0][2])):
                rows.append(dict({"assignment_id": meta["id"], "run_min": meta["run_min"], "run_max": meta["run_max"],
                                  "variation": meta["variation"], "created": meta["created"], "author": meta["author"],
                                  "comment": meta["comment"], "sha256": meta["sha256"], "row": index},
                                 **{name: values[index] for name, _, values in columns}))
        return rows

    def test_every_version(self):
        table = self.read(self.export(TABLE))
        assignments = self.provider.get_assignments(TABLE, -1, "")
        self.assertEqual(len(assignments), 3)                       # two periods of default, one of mc
        self.assertEqual(table.to_pylist(), self.expected_rows(assignments))
        self.assertEqual(table.num_rows, 6)

    def test_schema_types_units_and_metadata(self):
        schema = self.read(self.export(TABLE)).schema
        self.assertEqual(schema.field("created").type, pyarrow.timestamp("us", tz="UTC"))
        self.assertEqual(schema.field("subsystem").type, pyarrow.string())
        self.assertEqual(schema.field("capADC").type, pyarrow.int64())
        self.assertEqual(schema.field("sampFrac").type, pyarrow.float64())
        self.assertEqual(schema.field("capADC").metadata[b"units"], b"counts")
        self.assertEqual(schema.field("dyRangeADC").metadata[b"units"], b"MeV")
        self.assertEqual(schema.field("sampFrac").metadata[b"units"], b"")
        self.assertEqual(schema.metadata[b"ccdb.table"], TABLE.encode())
        self.assertEqual(schema.names[:9], ["assignment_id", "run_min", "run_max", "variation", "created", "author",
                                            "comment", "sha256", "row"])

    def test_created_is_the_utc_instant(self):
        table = self.read(self.export(TABLE))
        for row in table.to_pylist():
            created = row["created"]
            self.assertEqual(created.utcoffset(), datetime.timedelta(0))
            stored = self.provider.get_assignment_by_id(row["assignment_id"])
            self.assertEqual(created, assignment_metadata(stored)["created"])

    def test_run_resolves_as_cat(self):
        table = self.read(self.export(TABLE + " -r 1500"))
        expected = self.provider.get_assignment(TABLE, 1500, "default")
        self.assertEqual(table.to_pylist(), self.expected_rows([expected]))

    def test_variation_without_run(self):
        table = self.read(self.export(TABLE + " -v mc"))
        self.assertEqual(set(table.column("variation").to_pylist()), {"mc"})
        self.assertEqual(table.num_rows, 2)

    def test_tag(self):
        table = self.read(self.export(TOF + " -r 1500 --tag campaign_demo"), TOF)
        self.assertEqual(table.column("tIntercept").to_pylist(), [0.04314])
        newest = self.read(self.export(TOF + " -r 1500"), TOF)
        self.assertEqual(newest.column("tIntercept").to_pylist(), [0.05114])

    def test_duckdb_recipe(self):
        try:
            import duckdb
        except ImportError:
            self.skipTest("duckdb is not installed")
        output = self.export(TABLE)
        path = os.path.join(output, "epic.EcalBarrel.adc_calib.parquet")
        # docs/apis/analysis.md: what run 1500 reads, newest default assignment covering it
        rows = duckdb.sql("SELECT subsystem, sampFrac FROM '{0}' WHERE variation = 'default' AND run_min <= 1500 "
                          "AND run_max >= 1500 AND assignment_id = (SELECT max(assignment_id) FROM '{0}' "
                          "WHERE variation = 'default' AND run_min <= 1500 AND run_max >= 1500) ORDER BY row".format(path)).fetchall()
        expected = self.provider.get_assignment(TABLE, 1500, "default").constant_set.data_table
        self.assertEqual(rows, [(row[0], float(row[7])) for row in expected])

    def test_polars_recipe(self):
        try:
            import polars
        except ImportError:
            self.skipTest("polars is not installed")
        output = self.export(TABLE)
        frame = polars.read_parquet(os.path.join(output, "epic.EcalBarrel.adc_calib.parquet"))
        by_period = frame.filter(polars.col("variation") == "default").group_by("run_min").agg(polars.col("sampFrac").mean())
        self.assertEqual(sorted(by_period["run_min"].to_list()), [1, 1000])


if __name__ == "__main__":
    unittest.main()
