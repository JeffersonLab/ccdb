# FAIR data

Calibration constants decide what every reconstructed event means, so they deserve the care any research
data gets. The [FAIR principles](https://www.go-fair.org/fair-principles/) say what that care is: data that
can be **F**ound, **A**ccessed, **I**nteroperated with and **R**eused. CCDB was built as a logbook of
constants, where nothing is deleted and every change has an author, a time and a reason, and that design
covers most of FAIR by itself. The table maps each principle to what CCDB does today and what is planned.

| principle | today | roadmap |
|---|---|---|
| **F1** a globally unique, persistent identifier | Every version of every table has a permanent id, and a request with a time names constants for good: `/path:run:variation:time`, or `/api/v1/assignments/<id>` of the [HTTP API](apis/http.md). The data of each version has a SHA-256 ([constant sets](concepts/constant-sets.md)), so identical data has an identical name. [Tags](concepts/tags.md) name a whole calibration campaign. `ccdb export tag` writes a tag as a file with its SHA-256 and a DataCite record, ready for a DOI ([Publishing a tag](concepts/tags.md#publishing-a-tag)). |  |
| **F2** rich metadata | Tables have typed columns with units and comments, properties from a [standard vocabulary](cli.md#properties) such as description, contact and source code (`ccdb prop`), and a [data card](#data-cards) that gathers them. A tag names the software, container and data of a pass. |  |
| **F3** metadata names the data's identifier | The data card names the table, its versions and their ids; every row of a [Parquet export](apis/analysis.md) carries its version's id and hash. | |
| **F4** registered or indexed in a searchable resource | The web GUI and the API search tables by name and the change log by text; the [MCP server](apis/mcp.md) lets AI agents search and read; the [Atom feed](#change-feed) announces every change; every data card is also a schema.org `Dataset` in JSON-LD, for search engines and data catalogs. |  |
| **A1** retrievable by identifier over a standard protocol | HTTP and JSON with an OpenAPI description ([HTTP API](apis/http.md)), SQL (MySQL, MariaDB, SQLite), and run bundles: one SQLite file with the constants of one run. | |
| **A1.1** open, free, universal protocol | HTTP, SQL and SQLite are open and free; CCDB itself is LGPL-3.0-or-later. | |
| **A1.2** authentication and authorization where necessary | Reading needs no password; writing needs a database account ([deployment](deployment/new-experiment.md)). | |
| **A2** metadata stays when the data is retired | Nothing is deleted: retired tables, variations and directories are [deprecated](concepts/deprecation.md) and stay readable, and the change log keeps every operation. | |
| **I1** a formal, shared language | JSON with a JSON Schema per table (`/api/v1/tables/<path>/schema`), Parquet and Arrow with typed columns, pandas and polars [data frames](apis/analysis.md#data-frames). | |
| **I2** FAIR vocabularies | Column units are checked against [UCUM](cli.md#column-units), the Unified Code for Units of Measure, when a table is made; property names come from a [vocabulary](cli.md#properties) that `prop set` checks. |  |
| **I3** qualified references to other data | Table properties link the code that reads the constants (`source_url`); tags reference a variation and a moment; [resources tables](apis/jana.md) reference files by URL and hash. | Links to the run conditions database for each run range. |
| **R1** many accurate, relevant attributes | Every version has its author, creation time to the microsecond, comment and run range; every column its type, units and comment. | |
| **R1.1** a clear data usage license | The instance properties `license` and `citation` (`ccdb prop set --instance`) appear on every data card. | |
| **R1.2** detailed provenance | Author, time and reason of every version, the change log of every operation in the GUI, the API, the Atom feed and the MCP server, and the hash of every data set. A job records which versions it resolved ([What a job used](apis/jana.md#what-a-job-used)), and `ccdb provenance` checks the record against a database. |  |
| **R1.3** domain-relevant community standards | Parquet, Arrow, JSON Schema, OpenAPI and Atom; a [JANA2 service](apis/jana.md) and [DD4hep plugins](apis/dd4hep.md) for the frameworks of nuclear and particle physics. | |

## Data cards

A data card is one page per table with everything a reader needs to use its constants and to cite them:
the description and properties, the columns with types, units and comments, the number of versions and the
runs they cover per variation, the authors, the last change, the tags under which the table has constants,
and the instance's license and citation. The web GUI shows it at `/tables/<path>/card` (the Card button on a
table's versions page); the HTTP API serves it as JSON at `/api/v1/tables/<path>/card`.

```bash
curl https://ccdb.example.org/api/v1/tables/epic/HCal/adc_calib/card
curl https://ccdb.example.org/api/v1/tables/epic/HCal/adc_calib/card?format=jsonld
```

The `jsonld` form is a schema.org `Dataset`: `name` and `identifier` (the table path), `description`, `url`,
`creator` (the authors of its versions), `dateModified`, `license`, `citation`, `keywords`, and one
`variableMeasured` per column with its units. The GUI's card page embeds the same record in a
`<script type="application/ld+json">` element, so a search engine or a data catalog that reads the GUI finds it.

## Change feed

`/api/v1/logs.atom` is the change log as an Atom feed: the newest 50 operations (`per_page` up to 200), one
entry each, with author, time and a link to the record. `search=` narrows it as for `/api/v1/logs`, so a
feed reader can follow one table or one person:

```
https://ccdb.example.org/api/v1/logs.atom?search=/epic/HCal/adc_calib
```
