## CCDB

The **Calibration Constants Database (CCDB)** stores and serves the calibration constants that
reconstruction of a detector's data needs. Each sub-detector has its own tables, its constants change
with run number at boundaries of its own, and the best constants for a given run change again as
calibration improves. CCDB keeps track of all of it.

![CCDB tasks](images/ccdb_tasks.svg)

## Features

CCDB has been in production at GlueX, Jefferson Lab, since 2012. 

- GlueX [CCDB Website](https://halldweb.jlab.org/ccdb/) as a live (readonly) WebGUI example
- The [Quick start](#quick-start)


### Data model

- **[Structured, typed constants](concepts/concepts.md#table-types).** Every constant set is a table
  with named, typed columns (`int`, `double`, `string`, `bool`) and a fixed shape, stored at a path such
  as `/ecal/gains`. The database knows the shape, so it can display, validate and compare values, and
  reading code addresses `data["z"]` by name.

- **[History](concepts/conceptual-design.md).** Every version is kept, retrievable by date. 
  History is a first axis of the data model: a request with a date returns the constants as they were on that date. A campaign that fixes its branch and date gets the same constants in every job and get full repeatability.

- **[No-delete principle](cli.md#commands-overview).** CCDB is designed as a
  calibration logbook: a new assignment supersedes the old one and the old one stays; tables and
  branches that fall out of use are deprecated, which hides them from listings but keeps them for older software versions compatibility.

- **[Branching](deployment/new-experiment.md#variations).** Variations with inheritance.  Branches

  such as `mc` or a calibrator's work branch hold their own constants and inherit everything else from
  the parent, up to `default`. Production reads `default`; work in a branch changes nothing there.

- **[Full searchable logs](cli.md#commands-overview).** Author, time and comment are
  recorded on every object change. The log is searchable with CLI and the web GUI.

- **[Tags (named snapshots)](concepts/tags.md).** A tag fixes full set of constants for particular variation and data. Co a production campaign may have fixed reproducible

- **[Meta documentation and units](cli.md).** Columns carry units (`gain=double:MeV`);
  the instance and every table, directory and branch may carry free properties such as purpose, procedure,
  license and citation (`ccdb prop`). Everything may have comments. 

- **[Smart storage](concepts/constant-sets.md).** Under the hood, every unique data set is stored only once.
  Internally, when user adds the same data or copy data, only new labels are added. Which, on practice, allows to significanly recude the DB size and increase the performance. 

- **[Validity ranges](concepts/concepts.md#constant-sets-and-assignments).** 
  Constants are assigned to run ranges. Other validity ranges are possible. 

### Online DB, local copies, farm scale, CVMFS

- **[Central database with native clients](deployment/new-experiment.md#serving-constants-to-jobs).**
  MySQL or MariaDB holds the master copy; the C++ and Python APIs read it directly, with
  connect, read and write [timeouts](apis/cpp.md#timeouts-and-reconnect) and automatic reconnect.

- **[SQLite snapshots](deployment/new-experiment.md#serving-constants-to-jobs).** The whole database
  exports to one file that can be stored on CVMFS, shared file systems, containers and laptops/offline use. 
  Shallow SQLite snapshots allows to store only contant relevant campaign (a tag, technically) instead of full DB. A farm may use such snapshot with no database server in the loop.

- **[Shallow copies](https://github.com/JeffersonLab/ccdb/tree/v2-main/scripts/shallow_copy).**
  Instead of copying full central DB data, shallow copies can be configured in validity ranges/

- **[HTTP API with immutable URLs](apis/http.md).** Constant sets and per-run bundles are served over HTTP with
  cache-friendly immutable addresses, so the jobs of a campaign read from ordinary HTTP caches. 
  The [C++ client](apis/cpp.md#http-api) downloads a run bundle, checks its hash and opens it as a local SQLite file. This may significantly increase performance compared to live online DB connections

- **[Same program, any source](deployment/new-experiment.md#serving-constants-to-jobs).** Switching
  between the central database, a snapshot, a shallow copy and the HTTP API is **just** a change of the
  connection string.

### AI and agent ready

- **[MCP server (read-only)](apis/mcp.md).** Agents browse the tree, read constants, compare versions 
  and search the log through the Model Context Protocol, with the concepts pages shipped as a resource. 
  Writes are not exposed.
- **[OpenAPI document](apis/http.md).** Every HTTP endpoint and its typed JSON are described in an OpenAPI document, ready for generated clients and tool definitions.

- **[Self-describing tables](concepts/fair.md#data-cards).** Each table carries column descriptions and units, a JSON Schema and a generated data card, so a program or an agent understands a constant set without a human in the loop.

- **[FAIR metadata](concepts/fair.md).** License, citation and instance metadata are served on every data
  card once the instance properties are set, every card carries schema.org metadata for data catalogs, and
  every change is announced in an Atom feed.

- **[Measured readiness](concepts/ai-readiness.md).** `ccdb db readiness` computes one profile of an
  instance: units, descriptions and comments, open-ended run ranges, stale tables, anonymous versions, shared
  data sets, license and citation, each a count over the whole database. The API, the MCP server and the GUI
  serve the same profile.

- **[Provenance](apis/jana.md#what-a-job-used).** On request, the libraries record which version
  each request resolved to, with the hash of its data; the JANA2 service writes the record as a file with one
  parameter, and `ccdb provenance` checks it against any copy of the database and names the tags that give it.

- **[Tags are ready for a DOI](concepts/tags.md#publishing-a-tag).** A tag carries the software,
  container and data of the pass it names; `ccdb export tag` writes its constants as one file with a hash and
  a DataCite record for a repository deposit.

### Framework integrations

- **[JANA2 service](apis/jana.md).** A `CCDB_service` hands JANA2 factories a calibration object per
  run with typed getters; branch and date, or a tag, come from parameters.

- **[DD4hep conditions](apis/dd4hep.md).** A conditions loader maps a CCDB table to DD4hep conditions with a run
  interval of validity, alignment deltas being the worked example, plus geometry constants from the
  database at parse time.

- **[Model weights and external files (resources)](apis/jana.md).** A resources table records URL, SHA-256, size and metadata of files such as ONNX models; the file lives on a web server, on CVMFS or on a shared file system, and the client fetches it once, verifies the hash and keeps it in a local cache.

- **[Parquet export and DataFrames](apis/analysis.md).** Every version of a table, or the constants one run
  reads, export to Parquet, one file per table with types and units, for DuckDB, polars and pandas;
  `to_dataframe` gives a request's constants as a typed frame.

### Runs, time and streaming readout

- **[Run as the unit of validity](concepts/streaming-readout.md).** A run is an interval during which
  the detector configuration did not change. In a streaming experiment the run registry maps a time
  frame to its run, and CCDB resolves run, branch and date to constants; validity by time range is on
  the [roadmap](concepts/streaming-readout.md#roadmap).

- **[CCDB with RCDB](concepts/streaming-readout.md#ccdb-and-rcdb).** RCDB, the Run Conditions Database,
  keeps run start and end times and per-run conditions; CCDB keeps the constants. Both have Python and
  C++ APIs and a web interface and have run together at GlueX for over a decade.

### Tools and deployment

- **[Web GUI with version comparison](deployment/webgui.md).** The GUI browses the tree, lists a
  table's versions, shows any two side by side with changed cells marked and downloads the difference
  as a unified diff.

- **[Command line shell](cli.md).** The `ccdb` shell works on the tree with `ls`, `cd`, `vers`, `cat`
  and `add`; one `pip install ccdb`.

- **[Deployment guide](deployment/new-experiment.md).** Accounts, layout, policies,
  run-range rules, serving constants to jobs and backups. Full guide for new experiments. 
  Based on each with the choice that has worked at GlueX since 2012, and a checklist.

- **[Published load test](deployment/scaling.md).** Five ways of serving constants, measured on a database
  with the table shapes of Hall D's at 1 000 and 20 000 jobs starting within five minutes: how many jobs get
  their constants, how long a job waits, how often the database is asked.

## A simple example

Take a simple example of calibration data, say "target position," which is defined by three
coordinates x, y, z, each represented by a floating point number.

Using C++ as an example language, if a user asks for "target position":

```cpp
auto data = calibration->GetCalib("/target/position");
```

the calibration database provides the appropriate data in the current context so it can be used
like:

```cpp
if (data["z"] > 30) ...
```

"The **current context**" is the key phrase here, since the values of target position could be
different for different runs, values may be updated with time (e.g. if more precise calibration is
performed), and a user may want to use a personal version of constants.

![Target position sample](images/target_position_sample.png)

The picture above illustrates features of CCDB that involve control of the context:

- The data can be addressed by filesystem-like paths (`target/position`)
- The returned data depends on a run number.
- A history mechanism: by default CCDB honors the last assignment of data to a particular run, but
  one can always recover values stored in the past.
- Variations (equivalent to "branches" in version control systems): users have the ability to
  create and work with alternative versions of the data, varying the run assignments and/or the data
  itself.

## Quick start

The `ccdb` command and the Python API are distributed on [PyPI](https://pypi.org/project/ccdb/):

```bash
python -m pip install --upgrade ccdb
```

After installation you have:

- the `ccdb` Python library,
- the `ccdb` command, to work with CCDB in the terminal (also runnable as `python -m ccdb`).

CCDB 2.5 works with database schema 6 and refuses a schema 5 database. The Hall D database stays on
schema 5 until its administrators [upgrade it](deployment/upgrade-2.5.md); to read it before then, install the
previous release: `python -m pip install "ccdb<2.5"`.

Try it against the HallD read-only database, for example:

```bash
export CCDB_CONNECTION="mysql://ccdb_user@hallddb.jlab.org/ccdb"
ccdb -i              # start the interactive shell
```

Continue with:

- [Installation](get-started/installation.md) — all installation options (pip/uv, source, C++ with CMake, MySQL)
- [Demo](get-started/demo.md) — a database, the API behind its cache and the web GUI in one command
- [Upgrading from 2.4](deployment/upgrade-2.5.md) — schema 6, with a dry run and a rollback
- [Command line interface](cli.md) — the `ccdb` tool
- [Concepts illustrated](concepts/concepts.md) — namepaths, table types, assignments, requests
