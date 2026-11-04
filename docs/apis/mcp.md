# MCP server

The MCP server gives AI agents read access to a CCDB database through the
[Model Context Protocol](https://modelcontextprotocol.io): an agent can browse the tables, read constants for a run,
a variation, a time or a tag, compare two versions of a table and search the change log. Every tool only reads; no
tool, resource or argument writes to the database.

## Run the server

Install the `mcp` extra (Python 3.10 or newer) and start the server on a database:

```bash
pip install 'ccdb[mcp]'
ccdb -c mysql://ccdb_user@hallddb.jlab.org/ccdb mcp                  # stdio
ccdb -c mysql://ccdb_user@hallddb.jlab.org/ccdb mcp --http 8001      # streamable HTTP at http://127.0.0.1:8001/mcp
```

- **stdio** suits an agent on your machine: the agent starts the command itself.
- **Streamable HTTP** suits a shared instance; `--host 0.0.0.0` listens on every interface.

A client configuration for stdio, in the form most desktop agents use:

```json
{
  "mcpServers": {
    "ccdb": {
      "command": "ccdb",
      "args": ["-c", "mysql://ccdb_user@hallddb.jlab.org/ccdb", "mcp"]
    }
  }
}
```

## Tools

The tools answer with the same values as the [HTTP API](apis/http.md); times are UTC.

| tool | answers |
|---|---|
| `instance_info` | the CCDB version, the schema version and the instance properties |
| `health` | whether the database answers |
| `readiness(stale_years)` | the [readiness profile](concepts/ai-readiness.md#the-readiness-profile) of the instance, as `ccdb db readiness --json` |
| `list_directories(include_deprecated)` | every directory |
| `list_tables(pattern, include_deprecated)` | the tables whose name matches a pattern with `*` and `?` |
| `table_info(path)` | columns with types, units and comments, properties, variations with data, the assignment count and the newest assignment |
| `table_schema(path)` | a JSON Schema of the rows of the table |
| `list_variations(include_deprecated)` | every variation with its ancestry |
| `list_tags` | every tag with its variation, time and [properties](concepts/tags.md#tag-properties) |
| `resolve_request(request, tag)` | the assignment a request string resolves to: run range, variation, time, author, comment, SHA-256 of the data |
| `get_constants(request or assignment_id, tag, offset, limit)` | a page of rows of the constants, with the columns and the SHA-256 |
| `list_versions(path, page, per_page, sort, order, variation, run)` | a page of the table's assignments, as `ccdb vers` |
| `compare_assignments(a, b, changed_only)` | two assignments of one table compared cell by cell |
| `search_log(search, page, per_page)` | a page of the change log: who changed what, and when |

Deprecated directories, tables and variations are hidden from the lists unless `include_deprecated` is true.

The server also lists the concepts pages of this documentation as resources (`ccdb://docs/concepts/tags`) when it runs
from a CCDB checkout.

## A recorded session

The question an agent gets: *What changed in `/epic/HCal/adc_calib` between run periods 1–999 and 1000–1999, and who
changed it?* The steps below are the tool calls an agent makes, on the [demo tables](get-started/demo.md), and the
part of each answer the next step uses. `scripts/mcp/transcript.py` reproduces them with the MCP SDK's client.

**1. Check what the instance documents**

```
readiness()
```

```json
{
 "metadata": {
  "columns": 113,
  "columns_with_units": 65,
  "tables": 17,
  "tables_with_description": 17,
  "versions": 49,
  "versions_with_comment": 49,
  "tables_with_contact": 0,
  "tables_with_source_url": 14,
  "tables_with_doc_url": 0
 },
 "instance": {
  "license": true,
  "citation": false,
  "contact": true,
  "experiment": true,
  "url": true
 }
}
```

**2. Find the table**

```
list_tables(pattern="adc_calib")
```

```json
[
 "/epic/B0ECal/adc_calib",
 "/epic/EcalBarrel/adc_calib",
 "/epic/EcalEndcapN/adc_calib",
 "/epic/EcalEndcapP/adc_calib",
 "/epic/HCal/adc_calib"
]
```

**3. Read what it holds**

```
table_info(path="/epic/HCal/adc_calib")
```

```json
{
 "comment": "Hadron calorimeters ADC constants, one row per detector",
 "variations": [
  "default",
  "mc"
 ],
 "assignments": 3,
 "columns": [
  "detector",
  "capADC [counts]",
  "dyRangeADC [MeV]",
  "pedMeanADC [ADC]",
  "pedSigmaADC [ADC]",
  "resolutionTDC [ps]",
  "thresholdValue [ADC]",
  "sampFrac"
 ]
}
```

**4. List the versions of the default variation**

```
list_versions(path="/epic/HCal/adc_calib", variation="default", sort="run_min", order="asc")
```

```json
[
 {
  "id": 18,
  "run_min": 1,
  "run_max": 999,
  "created": "2026-01-15T09:12:00.000000Z",
  "author": "test_user",
  "comment": "period 1: runs 1-999"
 },
 {
  "id": 19,
  "run_min": 1000,
  "run_max": 1999,
  "created": "2026-01-15T09:13:00.000000Z",
  "author": "test_user",
  "comment": "period 2: runs 1000-1999"
 }
]
```

**5. Compare a run of each period**

```
compare_assignments(a="/epic/HCal/adc_calib:500:default", b="/epic/HCal/adc_calib:1500:default")
```

```json
{
 "changed_cells": 4,
 "changed_rows": [
  0,
  1,
  2,
  3
 ],
 "rows": [
  {
   "row": 0,
   "cells": [
    {
     "a": "0.033",
     "b": "0.03333",
     "changed": true
    }
   ]
  },
  {
   "row": 1,
   "cells": [
    {
     "a": "0.0095",
     "b": "0.009595",
     "changed": true
    }
   ]
  },
  {
   "row": 2,
   "cells": [
    {
     "a": "0.0257",
     "b": "0.025957",
     "changed": true
    }
   ]
  },
  {
   "row": 3,
   "cells": [
    {
     "a": "0.037",
     "b": "0.03737",
     "changed": true
    }
   ]
  }
 ]
}
```

**6. Who changed it**

```
search_log(search="/epic/HCal/adc_calib")
```

```json
[
 {
  "created": "2026-01-15T09:14:00.000000Z",
  "author": "test_user",
  "action": "create",
  "description": "Created assignment '/epic/HCal/adc_calib:0:mc:2026-01-15_09-14-00' (shared data)"
 },
 {
  "created": "2026-01-15T09:13:00.000000Z",
  "author": "test_user",
  "action": "create",
  "description": "Created assignment '/epic/HCal/adc_calib:1000:default:2026-01-15_09-13-00'"
 },
 {
  "created": "2026-01-15T09:12:00.000000Z",
  "author": "test_user",
  "action": "create",
  "description": "Created assignment '/epic/HCal/adc_calib:1:default:2026-01-15_09-12-00'"
 }
]
```


The answer: the sampling fractions of the four hadron calorimeters are 1 % higher from run 1000 on, in assignment 19,
which `test_user` added together with the first period's.
