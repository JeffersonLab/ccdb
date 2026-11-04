# AI readiness

A calibration database is ready for AI use when a program, an agent or a model pipeline can find its
constants, understand them without a human, trust where they came from, and measure all of that with
numbers that come out the same every time. CCDB 2.5 covers each of these in a feature of its own, and
`ccdb db readiness` measures how far an instance has come.

The requirements follow the assessment framework of the GlueX AI-readiness study (Panta, Sawatzky,
Morean, Romanov, Higinbotham, 2026, [arXiv:2609.34987](https://arxiv.org/abs/2609.34987)): seven categories of criteria, and the rule that a readiness claim is **reproducible**
(the same inputs give the same numbers), **comparable** (across instances and across time) and
**defensible** (every number traces to a query or a recorded rule). [FAIR data](concepts/fair.md) maps the
FAIR principles; this page maps readiness.

## What covers what

| requirement | CCDB 2.5 |
|---|---|
| Identity of the data | Every version has a permanent id and the SHA-256 of its data; a [tag](concepts/tags.md) names a whole calibration and, with its properties, the software, container and data of the pass; `ccdb export tag` makes a tag a file with a hash and a DataCite record, ready for a DOI ([Publishing a tag](concepts/tags.md#publishing-a-tag)) |
| Understandable without a human | Typed columns with [UCUM](cli.md#column-units) units and comments, properties from a checked [vocabulary](cli.md#properties), a JSON Schema per table, a [data card](concepts/fair.md#data-cards) in HTML, JSON and schema.org JSON-LD |
| Provenance of every value | Author, UTC time and comment on every version; the change log of every operation; the hash of every data set |
| Provenance of every use | The C++ and Python libraries record, when a program asks, which versions it resolved; the JANA2 service writes the record as a file with `ccdb:provenance`; `ccdb provenance` checks it against the database ([JANA2 service](apis/jana.md#what-a-job-used)) |
| Access by programs and agents | The [HTTP API](apis/http.md) with its OpenAPI document, run bundles, the read-only [MCP server](apis/mcp.md), [Parquet and data frames](apis/analysis.md) |
| Checks on the values | A JSON Schema per table for types; [Parquet and data frames](apis/analysis.md) for checks with tabular tools |
| Nothing lost | [Deprecation](concepts/deprecation.md) instead of deletion; tagged history protected from `rm` |
| Governance | Reads need no password; writes need an account and refuse `anonymous`; the instance carries `license`, `citation` and `contact` |
| Measured | `ccdb db readiness`, below |

## The readiness profile

`ccdb db readiness` computes one profile of the connected instance. Every number is one SQL count over
the whole database; nothing is sampled. Two profiles of the same data made on the same UTC day differ only
in `generated`, so profiles of two snapshots or two instances compare line by line.

```bash
ccdb -c mysql://ccdb_user@hallddb.jlab.org/ccdb db readiness            # a table
ccdb -c mysql://ccdb_user@hallddb.jlab.org/ccdb db readiness --json     # the same, as JSON
```

The same profile is served at `/api/v1/readiness` by the [HTTP API](apis/http.md), by the MCP tool
`readiness`, and on the page `/readiness` of the web GUI.

### Fields

| group | field | what it counts |
|---|---|---|
| `config` | `stale_years`, `stale_before`, `generated`, `ccdb_version`, `schema_version` | the inputs of this profile; `--stale-years N` sets the window, 5 by default, and `stale_before` is the start of the UTC day of `generated` that many years back |
| `metadata` | `columns_with_units` / `columns` | columns whose units are set |
| | `tables_with_description` / `tables` | tables with a non-empty comment |
| | `versions_with_comment` / `versions` | assignments with a non-empty comment |
| | `tables_with_contact`, `tables_with_source_url`, `tables_with_doc_url` | tables with that property |
| `units` | `columns_with_ucum_units` | columns whose unit string is valid [UCUM](cli.md#column-units) |
| `history` | `open_ended_run_ranges` | assignments whose run range starts at a run above 0 and has no upper bound: later runs receive these constants without anyone deciding so |
| | `versions_for_all_runs` | assignments whose run range covers every run, 0 to infinity |
| | `versions_by_anonymous` | assignments authored by `anonymous` |
| | `stale_tables` | tables with assignments, none created since `stale_before` |
| | `empty_tables` | tables with no assignment at all |
| | `deprecated_tables`, `deprecated_variations`, `deprecated_directories` | retired objects, still readable |
| | `tags` | tags |
| `data` | `constant_sets`, `shared_sets`, `unused_sets`, `bytes` | distinct data sets; sets used by more than one assignment; sets no assignment uses; stored bytes |
| `instance` | `license`, `citation`, `contact`, `experiment`, `url` | `true` when the instance property is set |

### Reading a profile

A profile is a description. Which numbers matter depends on what the instance is for: a database that
serves one experiment's reconstruction may have many open-ended run ranges by policy, and a test
database has no license. The profile makes each of these a known number instead of a guess.

To follow an instance over time, keep the JSON of each run; `diff` shows what changed. To compare two
instances, run the command on both with the same `--stale-years`.

### Example

The profile of the Hall D production database (a copy of 31 October 2026, upgraded to schema 6), shortened.
It took 7 seconds:

```json
{
 "config": {"stale_years": 5, "stale_before": "2021-11-03T00:00:00Z", "generated": "2026-11-03T22:49:06Z",
            "ccdb_version": "2.5.0", "schema_version": 6},
 "metadata": {"columns": 7700, "columns_with_units": 0, "tables": 688, "tables_with_description": 318,
              "versions": 821394, "versions_with_comment": 290787,
              "tables_with_contact": 0, "tables_with_source_url": 0, "tables_with_doc_url": 0},
 "units": {"columns_with_ucum_units": 0},
 "history": {"open_ended_run_ranges": 41350, "versions_for_all_runs": 1212, "versions_by_anonymous": 4675,
             "stale_tables": 390, "empty_tables": 9, "deprecated_tables": 0, "tags": 1},
 "data": {"constant_sets": 585786, "shared_sets": 66146, "unused_sets": 0, "bytes": 2870802276},
 "instance": {"license": false, "citation": false, "contact": false, "experiment": false, "url": false}
}
```

Each line names one thing a collaboration can change with the tools CCDB has: units in `mktbl` for new
tables and `set_column_units` for old ones, `prop set` for descriptions and the instance license, a
comment on every `add`, `deprecate` for the tables nobody writes to. The next profile shows whether it happened.
