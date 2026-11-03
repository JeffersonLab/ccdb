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
