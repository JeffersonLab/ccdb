# Analysis: Parquet and data frames

Calibration constants are data too: their history shows how a detector drifted, and a fit over run periods
needs them in a table. CCDB gives them to analysis tools in two ways.

## Parquet files

`ccdb export parquet` writes one [Parquet](https://parquet.apache.org) file per table, readable by pandas,
polars, DuckDB, Spark, ROOT's RDataFrame and anything else that reads Arrow. It needs the `export` extra:

```bash
pip install 'ccdb[export]'
ccdb -c sqlite:///ccdb.sqlite export parquet /epic/HCal/adc_calib -o exports                  # every version
ccdb -c sqlite:///ccdb.sqlite export parquet /epic/HCal/adc_calib -r 1500 -o exports          # what run 1500 reads
ccdb -c sqlite:///ccdb.sqlite export parquet /epic/HCal/adc_calib --tag pass1 -o exports      # what the tag reads
```

Each row of the file is one row of one assignment's data. The first columns name the assignment:

| column | meaning |
|---|---|
| `assignment_id` | the assignment's id; `/api/v1/assignments/<id>` of the [HTTP API](apis/http.md) names it for good |
| `run_min`, `run_max` | its run range |
| `variation` | its variation |
| `created` | when it was added, a UTC timestamp with microseconds (see [Time](concepts/time.md)) |
| `author`, `comment` | who added it and why |
| `sha256` | the hash of its data (see [Constant sets](concepts/constant-sets.md)) |
| `row` | the row's index within the assignment |

The data columns follow with the table's types (int and long as int64, uint and ulong as uint64, double as
float64, bool, string). Each data column carries its units, comment and CCDB type as field metadata; the file
carries the table path, its comment and the export request as schema metadata.

Without `-r`, the file holds every version: of one variation with `-v`, of all variations without it, created
at or before `-t` when it is given. With `-r`, it holds the one assignment the run reads, resolved as
`ccdb cat` resolves it, with the fallback to parent variations.

### DuckDB

```sql
-- what run 1500 reads in the default variation: the newest assignment that covers it
SELECT subsystem, sampFrac FROM 'exports/epic.EcalBarrel.adc_calib.parquet'
WHERE variation = 'default' AND run_min <= 1500 AND run_max >= 1500
  AND assignment_id = (SELECT max(assignment_id) FROM 'exports/epic.EcalBarrel.adc_calib.parquet'
                       WHERE variation = 'default' AND run_min <= 1500 AND run_max >= 1500)
ORDER BY row;
```

### polars

```python
import polars as pl

frame = pl.read_parquet("exports/epic.EcalBarrel.adc_calib.parquet")
# the mean sampling fraction of each run period of the default variation
frame.filter(pl.col("variation") == "default").group_by("run_min").agg(pl.col("sampFrac").mean())
```

The tests run both recipes on the demo tables wherever DuckDB and polars are installed.

## Data frames

`ccdb.frames.to_dataframe` gives the constants a request names as a pandas data frame (the `frames` extra), or
a polars one:

```python
from ccdb import AlchemyProvider
from ccdb.frames import to_dataframe

provider = AlchemyProvider()
provider.connect("sqlite:///ccdb.sqlite")
frame = to_dataframe(provider, "/epic/EcalBarrel/adc_calib:1500")        # a request string, as for ccdb cat
frame.attrs["units"]["dyRangeADC"]                                         # 'MeV'
frame.attrs["assignment"]["id"], frame.attrs["assignment"]["created"]      # which constants these are
frame = to_dataframe(provider, "/epic/TOFBarrel/lgad_calibration:1500@campaign_demo")
frame = to_dataframe(provider, "/epic/EcalBarrel/adc_calib:1500", library="polars")
```

The columns take the table's types. A pandas frame carries the units, the column comments, the table path and
the assignment (id, run range, variation, UTC creation time, author, comment, sha256) in `frame.attrs`; polars
frames have no attributes, so `ccdb.frames.column_units(table)` gives the units there.

## Checks with Great Expectations

A Parquet export is a flat table, so the tabular data-quality tools run on it unchanged. The example
`python/examples/example_expectations_parquet.py` exports a table of the standard test database, declares a
[Great Expectations](https://greatexpectations.io) suite and prints the result; CI runs it on every push.
Great Expectations is no dependency of CCDB: install it with `pip install 'ccdb[export]' 'great_expectations>=1,<2'`.

<!-- example_expectations_parquet.py: begin -->
```python
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
```
<!-- example_expectations_parquet.py: end -->

```
ok    expect_table_columns_to_match_set
ok    expect_compound_columns_to_be_unique
ok    expect_table_row_count_to_equal
...
4 versions, 8 rows: every expectation met
```

The suite checks what the schema can't: the physical range of the values and that every version holds the
full table. Keep it with the table: a calibrator runs it on a new version before `ccdb add`, and a check over
the history (`export parquet` without `-r`, then the suite) lists which versions break a range. Keep the
thresholds in the suite, so the check is reproducible: its configuration is recorded with it.
