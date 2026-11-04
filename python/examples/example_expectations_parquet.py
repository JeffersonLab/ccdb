"""Checks of CCDB constants with Great Expectations: export a table to Parquet, then validate the file.

    pip install 'ccdb[export]' 'great_expectations>=1,<2'
    CCDB_CONNECTION=sqlite:///ccdb.sqlite python example_expectations_parquet.py

The suite checks what the schema can't: the columns are the ones expected, the values lie in a physical range,
and every version holds the table's full set of rows. docs/apis/analysis.md shows this file; CI runs it
(python-examples.yml) on the standard test database (`ccdb db init`).
"""
import os
import subprocess
import sys
import tempfile

# Great Expectations sends usage analytics unless told not to; constants checks need no network
os.environ.setdefault("GX_ANALYTICS_ENABLED", "false")

import great_expectations as gx  # noqa: E402 (after the variable it reads at import)
import pandas  # noqa: E402

TABLE = "/test/test_vars/test_table"     # rows x, y, z (double), 2 rows per version
ROWS_PER_VERSION = 2

with tempfile.TemporaryDirectory() as directory:
    # one Parquet file with every version of the table; each row names its version (assignment_id, sha256, ...)
    subprocess.run(["ccdb", "export", "parquet", TABLE, "-o", directory], check=True)
    frame = pandas.read_parquet(os.path.join(directory, "test.test_vars.test_table.parquet"))

versions = frame["assignment_id"].nunique()
context = gx.get_context(mode="ephemeral")
context.variables.progress_bars = {"globally": False}
batch = (context.data_sources.add_pandas("ccdb")
         .add_dataframe_asset("test_table")
         .add_batch_definition_whole_dataframe("every version")
         .get_batch(batch_parameters={"dataframe": frame}))

suite = gx.ExpectationSuite(name="test_table")
suite.add_expectation(gx.expectations.ExpectTableColumnsToMatchSet(
    column_set=["assignment_id", "run_min", "run_max", "variation", "created", "author", "comment", "sha256", "row",
                "x", "y", "z"]))
for column in ("x", "y", "z"):
    suite.add_expectation(gx.expectations.ExpectColumnValuesToBeOfType(column=column, type_="float64"))
    suite.add_expectation(gx.expectations.ExpectColumnValuesToBeBetween(column=column, min_value=0, max_value=100))
# every version holds the full table: rows 0..1, each once, and no version is short
suite.add_expectation(gx.expectations.ExpectColumnValuesToBeBetween(column="row", min_value=0, max_value=ROWS_PER_VERSION - 1))
suite.add_expectation(gx.expectations.ExpectCompoundColumnsToBeUnique(column_list=["assignment_id", "row"]))
suite.add_expectation(gx.expectations.ExpectTableRowCountToEqual(value=versions * ROWS_PER_VERSION))

result = batch.validate(suite)
for each in result.results:
    print("{0:<5} {1}".format("ok" if each.success else "FAIL", each.expectation_config.type))
print("{0} versions, {1} rows: {2}".format(versions, len(frame), "every expectation met" if result.success else "FAILED"))
sys.exit(0 if result.success else 1)
