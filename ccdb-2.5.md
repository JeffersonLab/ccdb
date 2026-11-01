# CCDB 2.5 — schema 6 and ePIC integration program plan

To start a run, the user gives you one line: `Read {repo}/web-agents-common.md and {repo}/ccdb-2.5.md first. Run PHASE<N>.`

This file holds what belongs to this program: the goal, the decisions already made, the defaults
for open decisions, the known problems and the phases. The work protocol, the FIX / ASK / PARK /
STOP protocol, the memory layout of `{space}`, the checkpoint discipline and the documentation
and coding rules come from `web-agents-common.md` and are not repeated here. Where that file
speaks of the web GUI, its "Standing rules of the web GUI" bind only the GUI work items of this
program; every other component follows the common "How you code" and "How you document" rules
and the rules of this plan.

Two rules of the common file are overridden here by the user's decisions of 2026-10-31, and
only in the way stated: PHASE0 of this program changes product code (the schema and the core
that uses it), because the user decided that the data blob feature comes first and everything
else waits for it; and the core of the Python package and of the C++ library may be edited in
the phases and files that D1 names. Everywhere else the common rules stand.

## Paths

| name | path | what lives there |
|---|---|---|
| {repo} | /home/romanov/dev/ccdb | CCDB checkout, branch `v2.5` (the release branch of this program, from `v2-main`; merged into `v2-main` at PHASE12; the docs site is served from `v2-main`, so draft pages stay unpublished until then) |
| {space} | {repo}/space-ccdb-2.5 | notes, reports, plots, checkpoints, fixture; outside version control |
| {py} | {repo}/python/ccdb | the Python package: `provider.py`, `model.py`, `path_utils.py`, `cmd/`, `sql/` (fresh schemas and `update_v*.py`), `webgui/`, `testing.py` |
| {web} | {py}/webgui | the Flask GUI; its query helpers return plain data (the data seam) |
| {api} | {py}/api | new in this program: the FastAPI application |
| {mcp} | {py}/mcp | new in this program: the MCP server |
| {cpp} | {repo}/cpp | the C++ library (`src/CCDB`), Catch2 tests (`src/tests`), examples, the old `jana_plugin` |
| {jana2} | {repo}/jana2 | new in this program: the JANA2 service and plugin |
| {dd4hep} | {repo}/dd4hep | new in this program: the DD4hep plugins |
| {scripts} | {repo}/scripts | `webgui/` (the GUI ruler), `shallow_copy/`; new: `api/`, `loadtest/`, `docs/`, `schema/` |
| {docs} | {repo}/docs | docsify site; `_sidebar.md`, `index.html` (mermaid enabled) |
| {ci} | {repo}/.github/workflows | `python-tests.yml`, `mysql-tests.yml`, `cpp-tests.yml`, `cli-smoke.yml`, `lint-pyflakes.yml`, `webgui-tests.yml`, `webgui-browser.yml`, `documentation.yml`, `python-examples.yml`, `publish.yml` |

## Goal

Release CCDB 2.5.0 on database schema 6 as the calibration database an EIC ePIC reconstruction
job, simulation job, analyst and agent can use without MySQL access: a JANA2 service in the
EICRecon style, an HTTP API with an OpenAPI document, a read-only MCP server, a C++ provider that
reads through the API, a DD4hep integration, a published load test, exports for analysis, and a
demo that shows all of it on one machine.

Schema 6 is one migration, run once by `ccdb db upgrade`. It gives every constant set a stored
SHA-256 and lets many assignments of one table share one set, merges the duplicates of the
existing history, moves fresh databases to InnoDB, and adds the storage for deprecation,
snapshot tags, column units, instance and object properties and a reserved validity-time axis.
The data blob feature is the first thing built and the first thing the user reviews; nothing
else of this program starts before that review passes.

Everything that works in 2.4.0 keeps working after the upgrade: the Python and C++ APIs, the
CLI, `ccdb gui`, the WSGI deployment and the MySQL and SQLite providers; code that links
`libccdb` keeps building. A C++ 2.4 binary reads a schema 6 database unchanged. Python 2.5
accepts schema 6 only and Python 2.4 refuses it with a clear message, so an instance upgrades
its database and its Python clients on the same day; the upgrade guide says so.

Context the plan rests on: ePIC asked about CCDB after evaluating another conditions database,
so the program competes. The first question ePIC asks is "does it work in EICRecon", the second
is "does it hold at 100 000 concurrent jobs". The published pages
`{docs}/concepts/streaming-readout.md` and `{docs}/deployment/new-experiment.md` (commit 9fb4262)
state the streaming model and the deployment practice; this program builds what those pages
describe as roadmap, including the schema items they list as future, except validity time, which
is reserved in the schema and not implemented.

### Testing rule of this program

Everything is unit tested and tested. The rule applies to every work item of every phase:

- A work item is checkpointed only with a test that fails without the change and passes with it.
  Python tests are `unit_test_*.py` modules in `{repo}/python/tests`, run by `python -m unittest`;
  a new module joins the module lists of `python-tests.yml` and `mysql-tests.yml` in the same work
  item. C++ tests are Catch2 `test_*.cc` files in `{cpp}/src/tests` with a tag per optional
  component (`[http]`, `[jana2]`), excluded by tag where the component is not built.
- A schema change is tested three ways in the same work item: a fresh `ccdb db init`, the upgrade
  of a schema 5 database, and the C++ suite reading the result. Fresh and upgraded databases must
  have the same tables, columns, indexes and engines, checked by a test that compares the
  information schema (MySQL) and the pragmas (SQLite), not by eye.
- Every new component gets an integration check that runs in CI: a workflow file in `{ci}` added or
  extended in the same phase, with the same commands runnable on the host. Components that need a
  container (JANA2, DD4hep) run inside the `eic-shell` image in CI and on the host.
- Every new script directory under `{scripts}` joins the pyflakes paths in `lint-pyflakes.yml`.
- The GUI ruler (`{scripts}/webgui`) runs at every phase gate: a change outside the GUI must leave
  smoke bytes of every GUI URL equal to the phase's Step 0; a change inside the GUI goes through
  the GUI rules and the visual loop. PHASE0 rebuilds the fixture on schema 6 and re-establishes
  the GUI ruler on it (D32); from PHASE1 on the rule applies to that fixture.
- The phase report lists the test counts before and after, per suite.

## Decisions already made by the user

Do not re-litigate these. Decided in chat between 2026-10-29 and 2026-10-31.

- **Schema 6 ships in 2.5, and it ships first.** PHASE0 builds the schema and the data blob feature in the core (model, provider, SQL, migration, the `add`/`rm`/`vers` commands) and ends in a human review of the code; no other phase starts until the user approves it in chat. The rest of schema 6 (deprecation, tags, units, properties, the reserved time ranges) is created by the same migration in PHASE0 and given behavior in PHASE1 and PHASE2.
- **Strict version 6.** `_check_schema_version` accepts 6 and nothing else; there is no dual-version mode and no 2.4.1 compatibility release. The C++ library has no version check and selects named columns, so 2.4 C++ jobs keep reading; PHASE0 proves it with a test. Rollback is documented: drop what the upgrade added, set the version to 5; merged duplicates stay merged, which loses nothing because they were byte-identical.
- **Data identity is byte identity.** A constant set's identity is SHA-256 over the UTF-8 bytes of the stored vault text, computed in Python by one function in the model, which the vault setter, the backfill and `db rehash` call (D21). Nothing is canonicalized: `1.0` and `1.00` are two sets. Same hash and different bytes is an error that writes nothing. The hash is stored, never computed on the fly by the API or the GUI.
- **Shared constant sets inside one table.** `create_assignment` looks for a set of the same table with the same hash, compares the bytes, and reuses the set when they are equal; otherwise it creates one. Sharing never crosses tables. `rm -a` deletes a set with its last assignment, as 2.4 does for an unshared set; a set other assignments share stays; `rm -t` and `ccdb db dedup` remove unused sets left from history (decided 2026-11-01, Q43; note §5.2). A stored set is immutable: setting a different vault on it raises, and new data is a new assignment. `rm -t` of a table without assignments deletes the table's unused sets with it, as 2.4 deletes such a table (both decided 2026-10-31).
- **Historical duplicates are merged.** `ccdb db dedup` repoints every assignment of a table to the oldest of its byte-identical sets, deletes the others and the table's unused sets, writes one log record per table, and creates the unique index once no table holds duplicates; until then an interim non-unique index serves the lookups (D20). Report by default; `--dedup-i-am-sure` changes data (decided 2026-11-01, Q44; note §7).
- **InnoDB.** The fresh DDL names InnoDB for every table; the upgrade converts any table still on MyISAM and its dry run lists them with their sizes. No foreign key constraints in 2.5. The engine choice of 2012 was an era default, not a decision; hallddb is InnoDB already.
- **utf8mb4.** Every text column is utf8mb4: the fresh DDL declares it, the Python connection pins it, and `ccdb db upgrade` checks the character set of every table and column and converts whatever is not utf8mb4 yet, latin1 or any other, since CCDB instances use various encodings. Decided 2026-10-31.
- **Deprecation** of directories, variations and tables, never of assignments. A deprecated object needs a comment. It is hidden by default in `ls`, the directory tree, the GUI, the API and the MCP tools, shown with `-a` / `deprecated=all`. Anything that names the object directly (a request, `cat`, `vers`, `info`) works as before; `info` shows the deprecation status with the comment and the date. Columns: the existing `isDeprecated` and `deprecatedByUserId` plus new `deprecatedTime` and `deprecationComment`. The command copies the `-t -d -v` flags of `info`.
- **Tags are snapshots**, as a git tag is: an immutable, named pointer to a variation and a time. Resolving a request under a tag means resolving with the tag's variation and time for the run of the request, so one tag covers every table and every run range of a campaign. Request part `@name`; a tag replaces both variation and time and may not be combined with either. A tag's time may not be in the future. Tags are never modified; `ccdb tag rm` removes one with a log record; `rm -a` refuses an assignment a tag pins unless forced. The link table `variationsToTags` (`variations_has_tags` on hallddb) has no role left: not created in fresh schema 6, not dropped where it exists.
- **Validity time is reserved, not implemented.** `timeRanges(timeFrom, timeTo)` and a nullable `assignments.timeRangeId` exist from schema 6 so a later release needs no migration; no request syntax, no resolver, no CLI reads or writes them in 2.5.
- **`columns.units`**, the word physicists say and the attribute name of the NetCDF and HDF5 conventions: one free-text string per column, nullable, not validated in 2.5.
- **A `properties` table** holds the instance metadata and the per-object fields the FAIR and AI-readiness review found missing (description, contact, keywords, source and documentation URLs, license, citation), as rows keyed by owner and name, so later fields need no migration. The data card reads it; no environment-variable metadata.
- **Nothing is dropped.** `eventRanges`, `assignmentsMaterializedView`, the `isLocked` columns and every other existing object stay as they are. The user has plans for them.
- **JANA2:** a `CCDB_service` JService in the EICRecon style (constructor takes the application, logger, one-time initialization, parameters under one prefix, including `ccdb:tag`), used by factories in `ChangeRun()`. No compatibility with the legacy `JCalibrationGenerator` path. The old `{cpp}/jana_plugin` is retired.
- **DD4hep:** a basic integration counts, as long as the sentence "implemented integration with DD4hep" is true and tested.
- **MCP:** read-only, strictly. No tool, resource or prompt writes to the database under any flag. Tags are read there, created only by the CLI.
- **HTTP API:** FastAPI package `{api}`, beside the Flask GUI; pydantic models give the OpenAPI document; the MCP tools share the API's service functions.
- **Streaming and runs:** runs stay the unit; RCDB is the run registry that maps time to run. The reserved time range columns are the only validity-time item of 2.5. RCDB code is not part of this program; the API design leaves room for a time-to-run endpoint.
- **Simulation** takes alignment from the database, not digitization constants.
- **Model weights** are not stored in CCDB. A resources table holds url, sha256, size and metadata; a helper fetches and verifies the file.
- **Scaling design:** immutable URLs with long cache lifetimes, the data served as the stored blob without server-side rendering on the hot path, a per-run SQLite bundle as the unit a job downloads, a cache in front of the API as a mandatory part of the deployment.
- **Pitch texts** follow the "Feature pages and product descriptions" rules of the common file: strengths first, no competitor named in anything under `{docs}`.
- **Release:** 2.5.0 is the one release of this program, at the end. PHASE6 (demo) is the point at which ePIC is shown something, without a release.

## Defaults for open decisions

Follow the default. Each row is an ASK in the PHASE0 question seed, with the default as the
recommendation.

| # | decision | default |
|---|---|---|
| D1 | which core paths this program may edit | Two scopes. **Core phases (PHASE0, PHASE1):** `{py}/model.py`, `{py}/provider.py`, `{py}/path_utils.py`, `{py}/sql/` (fresh schema files, new `update_v6.py`), `{py}/cmd/commands/` (`add`, `rm`, `vers`, `ls`, `info`, `cat`, `dump`, `mktbl`, `db`; new `deprecate.py`, `tag.py`, `prop.py`) and the command registration, `{py}/testing.py`, `{py}/version.py`, `{py}/errors.py` (the three new exception classes) and `{scripts}/docs/` (the docs link check of PHASE0 item 9), both added (Gate A, 2026-11-01); in C++ only `{cpp}/src/CCDB/Helpers/PathUtils.*` (`ParseRequest`), the base provider's resolution path in `Providers/DataProvider.*` (the method the PHASE1 design note names), `Providers/MySQLDataProvider.cc`, `Providers/SQLiteDataProvider.cc`, for tag resolution; the tests of both; `{scripts}/webgui/make_fixture.py` for the fixture cases of D32; `{scripts}/shallow_copy` (script and tests, moved to schema 6) and `{py}/../examples/example_llapi_edit_assignment.py`, `example_llapi_copy.py` (rewritten for shared sets), decided 2026-10-31. **Later phases:** new code in new places (`{api}`, `{mcp}`, `{py}/snapshot.py`, `{py}/cmd/commands/api.py`, `mcp.py`, `{jana2}`, `{dd4hep}`, `{cpp}/src/CCDB/Providers/HTTPDataProvider.{h,cc}`, new tests), plus the command registration, `{cpp}/CMakeLists.txt` and `{cpp}/src/CCDB/CMakeLists.txt`, the one hook in `{cpp}/src/CCDB/CalibrationGenerator.cc` for `http://` connection strings, `pyproject.toml`, `{ci}`, and `{web}` under the GUI rules. Everything else goes through the core-patch PARK route. |
| D2 | JANA2 dependencies | `{jana2}` depends on JANA2 and `libccdb` only, never on EICRecon. Logging through JANA2's `JLogger`, parameters through `JParameterManager` under the prefix `ccdb:` (`ccdb:url`, `ccdb:variation`, `ccdb:time`, `ccdb:tag`, `ccdb:cache_dir`); `ccdb:tag` set together with `ccdb:variation` or `ccdb:time` is a configuration error. The code layout, naming and the one-time initialization mirror EICRecon's `DD4hep_service`. Built with `-DCCDB_BUILD_JANA2=ON`, off by default. |
| D3 | where JANA2 and DD4hep are built and tested | Inside the `eic-shell` container image (`eicweb/eic_xl`, the tag PHASE3 records), on the host through docker and in CI. The image ships JANA2, DD4hep and EICRecon at the versions ePIC uses, which makes it the version floor. |
| D4 | API stack and extras | `api = ["fastapi", "uvicorn", "orjson"]`, `mcp = ["mcp"]`, `export = ["pyarrow"]` as extras; the core package gains no runtime dependency; the Python floor stays 3.9 and CI runs the matrix. `ccdb api [-p PORT]` starts uvicorn with the CLI connection string, `ccdb.api:app` is the ASGI entry for a server. |
| D5 | API URL shape and caching | Prefix `/api/v1`. A URL that names an assignment by id, or a request string with an explicit time or a tag, is immutable and answers with `Cache-Control: public, max-age=31536000, immutable`. A resolving request (no time, no tag) answers with a `302` to the immutable form and `max-age=60`. Lists (versions, logs, variations, tags) answer with `max-age=60`. `ETag` on every response; on data responses it is the stored `sha256`. |
| D6 | data representations | Three forms per assignment, same resolver: `…/data` serves the stored blob bytes with the shape in headers (`X-CCDB-Rows`, `X-CCDB-Columns`, column names, types and units in a small JSON header field), `…/data.json` serves what the GUI's `data.json` serves, byte-identical, `…/data.txt` the `ccdb dump` text. The stored `sha256` and `size` travel in headers and in the JSON envelope; a test asserts they equal `hashlib` over the served bytes. |
| D7 | run bundle | `GET /api/v1/bundle?run=R&variation=V&time=T` or `…?run=R&tag=NAME` serves a SQLite file holding what `shallow_copy` selects for that triple, built on first request by `{py}/snapshot.py` into a disk cache (`CCDB_API_CACHE_DIR`, default a temp dir), keyed by the explicit triple; a tag is resolved to its triple first. Without `time` or `tag`, the endpoint redirects to the explicit form (D5). The bundle is a schema 6 database. |
| D8 | service layer | The API and the MCP tools import the GUI's query helpers (`{web}/queries.py`, `assignments.py`, `diff.py`) as they are. No move into a shared package in 2.5; a later cleanup may do it once three callers exist. |
| D9 | MCP shape | The official `mcp` Python SDK, tools as plain functions over the same service layer as the API, in-process, no HTTP hop. Transports: stdio for a laptop, streamable HTTP for a shared instance (`ccdb mcp --http`). Resources: the concepts pages from `{docs}`. A test asserts that the tool list names no write operation and that a provider whose write methods raise is never triggered by any tool. |
| D10 | C++ HTTP provider | Connection string `http://host/api/v1` or `https://…`. The provider downloads the run bundle for the requested run and variation and time or tag into `CCDB_HTTP_CACHE_DIR` (default `$HOME/.cache/ccdb`), verifies the `sha256` the API sends, and delegates every call to the existing SQLite provider on that file. libcurl, behind `-DCCDB_WITH_HTTP=ON` (default ON when libcurl is found). A per-table fallback is out of scope. |
| D11 | load-test data | A synthetic database shaped like hallddb: table count, rows and columns per table, blob sizes and assignments per table drawn from the read-only size survey of hallddb done in PHASE0 Step 0 (`COUNT`, `LENGTH(vault)` aggregates; no dump, no blob transfer). The survey script lives in `{scripts}/schema/survey.py` and its numbers in the PHASE0 report. |
| D12 | DD4hep pieces | Two plugins in one library `ccdb_dd4hep`: `CCDB_ConditionsLoader`, a `ConditionsDataLoader` that maps a CCDB table to conditions with a run IOV, alignment deltas (dx, dy, dz, rotations per detector element) as the worked example; and `CCDB_Constants`, a geometry plugin that defines compact XML constants from a one-row CCDB table at parse time. Built with `-DCCDB_BUILD_DD4HEP=ON`, off by default. |
| D13 | spack | A `package.py` under `{repo}/spack/packages/ccdb/`, tested by `spack install` from that local repo in CI (a `spack` container job). Submitting it upstream and to `eic-spack` is the user's action; the plan prepares the files and the text. |
| D14 | license and citation | `LICENSE` with GPL-2.0-or-later, as `pyproject.toml` already declares; `CITATION.cff` with the authors of `pyproject.toml`; Zenodo is a user action, the plan prepares `.zenodo.json`. |
| D15 | version during the program | `ccdb.version.version` becomes `2.5.0.dev0` in PHASE0 (its first product change) and `2.5.0` in PHASE12; `version.py` learns to read the PEP 440 suffix, `version_tuple` stays `(2, 5, 0)` (decided 2026-10-31, Q37). |
| D16 | demo | A compose file under `{repo}/docker/demo/` with MySQL holding ePIC-shaped tables, the API, nginx with the shipped cache configuration and the GUI; plus a standalone JANA2 application in `eic-shell` that reads one table through `CCDB_service` against that stack, once by variation and time and once by a campaign tag. A patch for an EICRecon branch with one factory using the service lives in `{space}/notes/epic/` for the demo day; EICRecon itself is not built in this repository's CI. |
| D17 | ePIC-shaped demo tables | The names, shapes and values come from the calibration parameters EICRecon reads today from parameters, configuration files and lookup tables (PHASE6 Step 0 collects the list from the EICRecon checkout in `eic-shell`). The generator is `{scripts}/demo/make_epic_tables.py`, deterministic like the GUI fixture; it sets units, properties and one tag. |
| D18 | hallddb measurements | All read-only through `mysql://ccdb_user@hallddb.jlab.org/ccdb`; MariaDB clients from 11.4 on need `--skip-ssl`, since hallddb has no TLS. A full dump of hallddb taken on 2026-10-31 lies in `/data/halld-ccdb/hallddb_ccdb_2026-10-31.sql.gz` (894 MB gzipped, 3.5 GB of data, includes the `users` table, owner-only permissions); it is the copy on which the upgrade, the dedup and the index build are timed, loaded into a local MariaDB 10.5 container with hallddb's settings (`{space}/tools/hallddb-copy.compose.yml`, database `ccdb_hallddb`; experiments use a second copy `ccdb_hallddb_trial`), so blob-reading measurements, the full duplicate scan included, run on the copy and not on production. PHASE0 Step 0: the size survey, the schema drift inventory and the duplicate measurement on a bounded sample (the 20 largest tables, `SHA2(CONVERT(vault USING utf8mb4), 256)` grouped per table, byte-identical groups and numeric-only groups counted); the full duplicate scan reads every blob on the production server and is an ASK. PHASE0 item 10: `ccdb db upgrade --dry-run` against hallddb. PHASE5: the cost of the largest constant set (175 951 rows × 6 columns) through the GUI's `data.json` and the API's three forms. |
| D19 | pitch material | The comparison with other conditions databases goes to `{space}/reports/comparison.md`, never under `{docs}`. The docs index, README and release notes follow the feature-page rules. The presentation is the user's; the plan delivers its content as a markdown outline in `{space}/reports/`. |
| D20 | hash columns and index | `constantSets.sha256 CHAR(64) CHARACTER SET ascii COLLATE ascii_bin` (hex, lower case) and `constantSets.size INT UNSIGNED` (bytes of the UTF-8 vault), both NULL during the backfill and `NOT NULL` once it is complete. Unique index `uq_constantSets_table_sha256 (constantTypeId, sha256)`, created by `db upgrade` when no CCDB table has duplicates and by `db dedup --dedup-i-am-sure` once none has, including after a `--table` run that cleaned the last one; MySQL and MariaDB have no partial indexes, so the index covers all of `constantSets` or nothing. Until then the interim non-unique index `ix_constantSets_table_sha256` on the same columns serves the lookups of `create_assignment`; dedup drops it when it creates the unique index (decided 2026-10-31, Q36). SQLite: the same columns and indexes. Detail: note §2.1, §2.3 (Gate A, 2026-11-01). |
| D21 | where the hash is computed | One function, `vault_digest(text)` in `{py}/model.py`, returns the hex SHA-256 and the byte size of the UTF-8 vault. The `vault` setter of `ConstantSet` calls it (`data_list` and `data_table` go through the setter; loading a set never calls it), and so do the upgrade backfill and `db rehash` (decided 2026-10-31, Q35). The backfill and the dedup repoint write with SQL text statements, because SQLAlchemy's `update()` would fill the Python-side `onupdate`; neither `constantSets.modified` nor `assignments.modified` changes. No SQL function computes a hash that is stored; `SHA2(CONVERT(vault USING utf8mb4), 256)` is used only to verify (D26) and to measure (D18). Detail: note §4.1 (Gate A, 2026-11-01). |
| D22 | collision policy | Same table, same hash, different bytes → `DataCollisionError` from `create_assignment`, nothing written, a log line with both set ids. Tested with a stubbed hash function, since a real SHA-256 collision cannot be produced. A collision found by `db dedup` or `db rehash` on real data is a STOP: it means corrupt data or a broken hash, and the user decides. |
| D23 | insert race | `create_assignment` is one transaction with one commit; pending session changes make it refuse with `SessionHasPendingChangesError`. It locks its table's `typeTables` row (`FOR SHARE`), looks up the table's sets with the same hash, unused ones included, and re-reads a reused set as a locking read (`FOR SHARE`), so `db dedup`, `rm -a` and `rm -t` cannot delete that set before the commit; a set found gone is no match. Two sessions inserting the same bytes at once: the new set is inserted inside a SAVEPOINT, the unique index rejects the second insert, and the provider rolls back to the savepoint, re-queries the set by hash as a locking read (a plain read under REPEATABLE READ, which hallddb runs, would miss the winner), compares the bytes and reuses it. A deadlock (MySQL 1213) or lock timeout (1205) rolls back and restarts the transaction, at most 3 times. SQLite: `BEGIN IMMEDIATE`, so writers wait instead of racing. Every writer (`create_assignment`, `cp`, `rm -a`, `rm -t`, `db dedup`) locks in one order: `typeTables` rows, then `constantSets` rows, then `assignments` rows. Tested in `mysql-tests.yml` with two sessions on both servers, including the races with `db dedup`, `rm -a`, `rm -t` and `cp`. Before the index exists (a table with historical duplicates not yet merged) the race can leave two identical sets; `db dedup` merges them. Detail: note §5.1, §5.2 (Gate A, 2026-11-01). |
| D24 | dedup rules | `ccdb db dedup [--table PATH] [--dedup-i-am-sure] [--no-transaction-check]`. Per table, one transaction with the restart rule of D23: group by `sha256`, lock the group's sets (`FOR UPDATE`), compare bytes in Python; unequal bytes are a collision that rolls back the table and stops the run (D22). The oldest set (smallest id) survives, every assignment of the others is repointed, and the others are deleted by a statement that keeps any set still in use. Unused sets left from history are removed the same way. Repoint and delete are SQL text statements, never the ORM. One log record per changed table: `Merged <N> constant sets into <M>, removed <K> unused sets`. Without `--dedup-i-am-sure` it reports per table the groups, the sets that would go, the assignments that would move and the bytes saved, and changes nothing. With the flag it runs the upgrade's open-transaction check, and a `sha256` that is not 64 lowercase hex characters stops the run before any change until `db rehash --rehash-i-am-sure` or the backfill hashes it. A run that leaves no duplicate in any table creates the unique index and drops the interim one (D20). SQLite: in place, one `BEGIN IMMEDIATE` transaction per table. Detail: note §7 (Gate A, 2026-11-01). |
| D25 | upgrade mechanics | `update_v6.py` for MySQL (MariaDB 10.5 and MySQL 8.3 tested) and SQLite. Idempotent and re-runnable: every table, column and index is checked for existence first (hallddb already differs from the fresh schema 5). Preflight, writing nothing: exactly one `schemaVersions` row, value 5; the privileges (`--skip-privilege-check` when they come through a role); no open transaction on the database (`--no-transaction-check` without PROCESS); `tags` empty; the character-set stops and no foreign key constraint on a CCDB table; the resources printed (rebuild space, binlog, replicas); session `sql_mode` strict and `lock_wait_timeout` 10 s. `--upgrade-i-am-sure` is the only confirmation and states that a verified backup exists; without it the command prints 2.4's backup warning, changes nothing and exits 1. No command makes a backup. Order: per-table DDL (InnoDB, utf8mb4 decided per column by its collation, new columns NULL, `tags` altered in place, new tables) → backfill of `sha256` and `size` in batches of 500 sets ordered by id, unhashed rows only (a `sha256` that is not 64 lowercase hex characters counts as unhashed), committed per batch, resumable → `NOT NULL` → the unique index when no CCDB table has duplicates, else the interim index (D20) → `schemaVersions` = 6, written last. Every ALTER names its algorithm and lock clause and runs under `lock_wait_timeout` 10 s with three retries on 1205. SQLite: the upgrade works on a copy and replaces the file atomically, keeping `<file>.v5`; `--in-place` skips the copy, for the upgrade and the rollback. `--dry-run [--duplicates none\|sample\|all]` (default `none`, which reads no vault) prints the DDL with its lock clauses, the MyISAM tables with sizes, the count of sets to hash and the estimated time, and writes nothing: a CI test runs it as a MySQL user with `SELECT` only and expects success, and `--upgrade-i-am-sure` with that user expects a clean failure before any change. `ccdb db rollback-v6 --rollback-i-am-sure` drops what v6 added and sets 5; it keeps engines and charsets, and refuses when schema 6 tables or columns hold data (`--drop-v6-data` deletes it first) or the server's `sql_mode` is not strict (`--allow-non-strict`). Measured on the hallddb copy: about 160 s on MariaDB 10.5. Detail: note §6, §9 (Gate A, 2026-11-01). |
| D26 | verification command | `ccdb db rehash [--sample N] [--server] [--rehash-i-am-sure]`: recomputes `vault_digest` in Python for all sets, or for N sets spread evenly over the id range, and compares with the stored `sha256` and `size`; it prints mismatches and exits 1 when any. `--server` additionally compares with `SHA2(CONVERT(vault USING utf8mb4), 256)` and `LENGTH(CONVERT(vault USING utf8mb4))` on MySQL, so two independent implementations must agree; it is refused on SQLite. `--rehash-i-am-sure` rewrites mismatches, writes one log record listing the set ids and exits 0 when every mismatch was repaired; it refuses a rewrite that would make two sets of one table equal and reports it for `db dedup`. Replaces the earlier working name `db check`. Detail: note §8 (Gate A, 2026-11-01). |
| D27 | tags | `tags(id, name UNIQUE, variationId, snapshotTime, comment, authorId, created)`. Names follow the variation name rules, up to 100 characters (`VARCHAR(100)`); uniqueness follows the column collation, so MySQL and MariaDB ignore case and trailing spaces and SQLite compares bytes. `snapshotTime` is a `DATETIME` holding a UTC instant, which the PHASE1 resolver converts per provider; `created` is a `DATETIME` too. The upgrade alters the schema 5 `tags` in place on MySQL and rebuilds it on SQLite, and refuses a non-empty one. `ccdb tag NAME [-v VARIATION] [-t TIME] -c COMMENT` creates (variation default `default`, time default now, a future time is refused), `ccdb tag` lists, `ccdb tag NAME` shows, `ccdb tag rm NAME` removes with a log record. In a request string the part `@NAME` is a tag; a request with a tag and a variation or a time is an error in Python and C++ alike. `rm -a ID` refuses when any tag whose variation is, or inherits from, the assignment's variation has `snapshotTime >= created`, unless `--force`. Detail: note §2.1, §2.2 (Gate A, 2026-11-01). |
| D28 | deprecation | Columns on `directories`, `typeTables` and `variations`: the schema 5 `isDeprecated` and `deprecatedByUserId`, now mapped in the ORM and added by the upgrade where a database lacks them, plus new `deprecatedTime DATETIME NULL DEFAULT NULL` (a bare `TIMESTAMP` gets automatic defaults on MariaDB 10.5) and `deprecationComment TEXT NULL`. `ccdb deprecate NAME [-t\|-d\|-v] -c COMMENT` and `ccdb deprecate --undo NAME [-t\|-d\|-v]`; without a flag NAME is tried as a table, then as a directory (`info` assumes a table; `deprecate` is one step friendlier). `ls -a` shows deprecated entries marked; `ls -l` shows the comment and the date. `info` always shows the named object and prints a deprecation line with the comment and the date; `cat`, `vers`, `dump` and requests are unchanged. The provider's listing methods keep returning everything, so 2.4 scripts see no change; they gain an opt-in `include_deprecated=False`, and the hidden-by-default rule is applied by the callers (`ls`, the tree, the GUI, the API, the MCP tools), each in its own phase. GUI: a "Show deprecated" switch above the tree carried as `deprecated=all` on every list view, remembered in local storage; deprecated entries muted with a badge, comment and date in the info panel. API and MCP: `deprecated=all` on every list, default hidden; object endpoints return the four fields. The C++ listing APIs are unchanged and show everything, documented. Detail: note §2.1 (Gate A, 2026-11-01). |
| D29 | properties | `properties(id, ownerType, ownerId, name, value, authorId, modified)`, unique on `(ownerType, ownerId, name)`; `ownerType` in `instance` (ownerId 0), `directory`, `table`, `variation`, `column`. Instance names: `experiment`, `description`, `license`, `citation`, `contact`, `url`. Object names: `description`, `contact`, `keywords`, `source_url`, `doc_url`, `license`, `citation`. Any other name is allowed. `ccdb prop set\|get\|ls [--instance\|NAME [-t\|-d\|-v]] key [value]`, a log record per change; `info` shows properties; the data card and `GET /api/v1/instance` read them. |
| D30 | units | `columns.units VARCHAR(64) NULL`. `mktbl` column syntax grows an optional part, `name=type:units` (`gain=double:MeV`), keeping `name=type` valid; `info`, the GUI table page, the API table info and the `data` headers show it. |
| D31 | reserved time ranges | `timeRanges(id, timeFrom DATETIME, timeTo DATETIME, comment)` and `assignments.timeRangeId INT NULL` with an index. Mapped in the ORM, written by nothing, read by nothing, named in the schema reference as reserved. |
| D32 | fixture on schema 6 | `make_fixture.py` keeps every existing case and adds: two assignments of one table with byte-identical data (one shared set), a `1.0` versus `1.00` pair (two sets), one deprecated directory, table and variation, two tags (one at creation time, one in the past), units on one table, instance and table properties. The fixture is rebuilt, `MANIFEST.md` rehashed, GUI golden recomputed and the diff recorded in the PHASE0 report with the reason per changed value; PHASE0 is the one phase where the GUI smoke bytes may differ from its Step 0, and only on pages the fixture change reaches. |
| D33 | database servers in CI | `mysql-tests.yml` runs the suite and the upgrade tests on MySQL 8.3 and on MariaDB 10.5 (hallddb's server), as two services or two jobs. |

## Known problems (seed list — verify each in the phase named)

Observed on 2026-10-30 and 2026-10-31 on the checkout at 9fb4262. Items 12 to 16 belong to
PHASE0; the rest to PHASE3 Step 0.

1. No `LICENSE` file and no `CITATION.cff` at the repository root, while `pyproject.toml` declares `GPL-2.0-or-later`.
2. `{cpp}/jana_plugin` targets the JANA1 API (`JCalibrationGenerator`, a `Makefile`) and is dead for EICRecon. `{docs}/apis/jana.md` says the JANA API is part of JANA, which describes the JANA1 copy; JANA2 ships `JCalibrationCCDB.h` copied from CCDB 0.06.
3. `{cpp}/CMakeLists.txt` (`project(ccdb_main)`) exports no CMake package: no `install(EXPORT …)`, no `ccdbConfig.cmake`, so a consumer cannot `find_package(ccdb)`. To confirm by a clean consumer build.
4. CCDB has no spack recipe (user's statement, to confirm against the spack and eic-spack repositories).
5. `{scripts}/shallow_copy/` is a script, not an importable module, so nothing in the package can build a run bundle.
6. The GUI's `data.json` splits the blob and renders JSON on every request: 1.7 to 2.7 ms for small sets on the fixture; the cost for the largest hallddb set is unmeasured.
7. The GUI has no HTTP cache headers on immutable URLs other than the exact-pair rule of the compare page (to verify route by route).
8. `docker/docker-compose.yml` and `docker/mysqlccdb`, `docker/mysqldb` predate the 2.4.0 GUI image; whether they still start is unknown.
9. Under Werkzeug 2.2 (AlmaLinux 9 RPMs), 5 of 86 GUI tests fail because they assert literal `/` and `:` in query strings that Werkzeug percent-encodes (halldwebdev note, 2026-10-27). CI runs newer Werkzeug and does not see it.
10. The docs site has no automated link and anchor check; the two pages of 9fb4262 were checked by an ad-hoc script that is not in the repository.
11. `cpp/README.md`, `install.linux.md` and `{docs}/get-started/installation.md` describe the C++ build; whether they agree with the current CMake is unverified.
12. The ORM enforces one set per assignment: `Assignment.constant_set` is `uselist=False` with `cascade="all, delete, delete-orphan", single_parent=True` (`{py}/model.py` lines 203 to 207), and `delete_assignment` deletes through it. 31 uses of `constant_set` in 8 files (`provider.py`, `cmd/commands/cat.py`, `webgui/views.py`, `webgui/assignments.py`, `templates/assignment.html`, two test modules, the model) must be inventoried before the relationship changes.
13. hallddb's schema differs from the fresh schema 5 (measured 2026-10-31, `information_schema` only): all 14 tables are InnoDB while the DDL says MyISAM; the link table is called `variations_has_tags`, not `variationsToTags`; every text column is latin1, the vault included (821 431 sets by `COUNT(*)`, 3 255 MB of vault text, MariaDB 10.5.29; 663 401 was the `information_schema` estimate); the `isDeprecated` and `isLocked` columns exist on `directories`, `typeTables` and `variations`. The upgrade must check existence per object, and `variations_has_tags` gets the same treatment as `variationsToTags`: untouched.
14. The schema 5 columns `isDeprecated`, `deprecatedByUserId`, `isLocked`, `lockTime`, `lockedByUserId` appear only in the DDL files and are mapped nowhere: not in the ORM, the provider, the CLI, the GUI or the C++ library.
15. Python's `_check_schema_version` accepts exactly 5; the C++ providers have no version check and select named columns (`constantSets.vault AS blob`, read by position of that selection), which is why added columns do not affect them. To prove by running the C++ suite against a schema 6 SQLite file.
16. `tags` is empty on hallddb and unused by every code path; `eventRanges` and `assignmentsMaterializedView` are referenced by no code.

## Phase plan

PHASE0 is the baseline and the schema. Each later phase has a Step 0, work items, a gate, a done
criterion and extra decision-table rows. Phases run in order; PHASE7 to PHASE11 may be reordered
by the user after PHASE6 without re-planning, since none of them depends on another. The next
phase starts only after the user has read the previous report and answered its BLOCKING
questions; after PHASE0 and PHASE1 the user's approval of the code itself is that answer.

### Shared ruler of this program

The GUI ruler of the common file (fixture, smoke, golden, browser check) applies unchanged. This
program adds:

- **Python suite** — `python -m unittest` over every `unit_test_*` module plus `integ_test_cli_manager` and `integ_test_provider_sqlite`, with `CCDB_TEST_SQLITE_CONNECTION` on a scratch file. The count per module is recorded at every gate.
- **MySQL suite** — the modules of `mysql-tests.yml` against MySQL 8.3 and MariaDB 10.5 (D33), on the host through the compose file `{scripts}/schema/compose.yml` that starts both.
- **Schema equality** — `{scripts}/schema/compare.py`: dumps tables, columns, types, nullability, indexes and engines of a database into a sorted text; fresh v6 and upgraded v5→v6 must produce the same text on MySQL and on SQLite. Run at every gate from PHASE0 on.
- **C++ suite** — `cmake -S {cpp} -B {space}/build/cpp && cmake --build {space}/build/cpp --target ccdb_tests` and `{space}/build/cpp/src/tests/ccdb_tests "~[mysql]"` (out of tree: `{cpp}/build` is not in `.gitignore`) on the schema 6 SQLite fixture; with `[http]`, `[jana2]` tags added by this program, excluded where the component is not built.
- **CLI smoke** — the `cli-smoke.yml` commands, extended by the phases with the new commands and their exit codes.
- **API ruler** — `{scripts}/api/`: `pages.py` (every API URL with a kind), `smoke.py --check` (status, bytes, time, SQL query count; in-process through the ASGI test client or `--base-url`), `golden.py compute|compare` (expected values from SQL on the GUI fixture, plus the GUI-equality check: `data.json` of the API equals `data.json` of the GUI byte for byte for every fixture assignment in `pages.py`). The OpenAPI document is stored as `{scripts}/api/openapi.json` and compared at every gate; a change to it is a reviewed diff in the phase report.
- **Container checks** — `{scripts}/eic/run_in_eic_shell.sh <command>` runs a command in the `eic-shell` image with `{repo}` mounted; the JANA2 and DD4hep tests run through it on the host and in CI.
- **Docs check** — `{scripts}/docs/check_links.py`: every relative link and anchor of every page under `{docs}` resolves; `_sidebar.md` names only existing pages.
- **Lint** — `pyflakes` over `{py}`, `{repo}/python/tests` and every directory under `{scripts}`.

The gate of a phase is what its section names from these, plus the phase's own numbers.

### PHASE0 — baseline and schema 6 core: shared constant sets

Task: measure the unchanged tree, then build schema 6 and the data blob feature in the core,
with the migration and its tools, and hand the user a review package. Two human gates: the
design note before code, the code before PHASE1.

- **Step 0** (unchanged tree): the working tree must be clean apart from this plan file and untracked local files (`.claude/`); the checkpoint script refuses its first save on a tree with modified tracked files and the Git rule makes it a STOP, so the user commits first. The user authorized git use for this program on 2026-10-31 with the phrase the global rules require; that authorization is renewed per request in chat and never assumed from this file. Then: build the schema 5 fixture (`make_fixture.py --verify`, hash into `{space}/fixture/MANIFEST.md`), run the Python suite, the MySQL suite on both servers, the C++ suite, GUI smoke `--check`, golden, the browser check in both browsers, cli-smoke, pyflakes; record every count in `{space}/reports/phase0_baseline.md`. Verify seed items 12 to 16 as findings F1…: the `constant_set` consumer inventory with what each one does, the C++ query shapes, the hallddb drift inventory (D18, read-only, `information_schema` only), the size survey and the bounded duplicate measurement (D18), into `{scripts}/schema/survey.py` and the report. If hallddb is unreachable, record it and continue.
- Work items, one checkpoint each:
  1. **Design note** `{space}/notes/schema6.md`: the complete DDL of schema 6 for MySQL and SQLite as a diff against schema 5 (D20, D27 to D31, InnoDB, nothing dropped); the ORM changes with the fate of every `constant_set` consumer from Step 0; the `create_assignment` algorithm with the collision and race paths (D21 to D23); the upgrade algorithm, its dry run and its rollback (D25); the dedup algorithm (D24); `rehash` (D26); the test matrix of this phase; what 2.4 clients experience. **Gate A**: ASK, BLOCKING, "approve the schema 6 design note"; no product code before the user's yes in chat. Corrections become a revised note under the same gate. Approved in chat 2026-11-01 (Q42).
  2. **Schema files and version**: `{py}/sql/mysql_schema.py` and `sqlite_schema.py` at schema 6 (InnoDB, all new objects, fresh `schemaVersions` row 6); `{repo}/sql/ccdb.mysql.sql` regenerated from them; `update_v6.py` DDL part with existence checks; `_check_schema_version` accepts 6; `ccdb.version.version` = `2.5.0.dev0`. `unit_test_schema_v6.py`: fresh init on SQLite and MySQL contains every expected object; a schema 5 database created by the previous files and upgraded equals the fresh one by `compare.py`; running the upgrade twice is a no-op; a schema 5 database with `variationsToTags` missing and one with it present both upgrade; a MyISAM table is InnoDB afterwards. `{scripts}/schema/compare.py` written here.
  3. **Model**: `ConstantSet.sha256`, `size`, the setter (D21); `Assignment.constant_set` becomes many-to-one without delete-orphan, `ConstantSet.assignments` the list; `TypeTable.constant_sets` unchanged; new models `Tag`, `TimeRange`, `Property`; `Column.units`; the deprecation columns mapped on `Directory`, `TypeTable`, `Variation`. Every consumer from the inventory adapted or shown unaffected, one test each. `unit_test_model_v6.py`: the setter hashes, `data_table` goes through it, a set with two assignments survives the deletion of one, the hash of a known blob equals a literal computed once by hand.
  4. **Provider, write path**: `create_assignment` find-or-create by `(table, sha256)` with byte compare, `DataCollisionError` (D22), the race path (D23), the log record naming a reused set; `delete_assignment` deletes the assignment and, when it was the last one, its set (note §5.2); `get_assignment` and friends unchanged in behavior. `unit_test_provider_shared_sets.py`: same bytes twice → one set, two assignments; `1.0` and `1.00` → two sets; other table, same bytes → two sets; stubbed hash collision → error, nothing written, counts unchanged; `rm -a` of one of two sharers keeps the set; `rm -a` of the last assignment deletes the set; `mysql-tests.yml` two-session race on both servers. The `add`, `rm` and `vers` commands: `vers -l` shows the hash prefix and "shared by N"; cli-smoke extended.
  5. **Upgrade backfill, dedup, rehash**: the backfill part of `update_v6.py` (D25) and `db upgrade --dry-run`; `db dedup` (D24); `db rehash` (D26); `db rollback-v6`. Tests: backfill of a database with 1 200 sets in batches, interrupted after the first batch and resumed, every hash equals Python's; dry run with a `SELECT`-only user succeeds and changes nothing (schema equality before and after), `--upgrade-i-am-sure` with that user fails cleanly; `db dedup --dedup-i-am-sure` on a constructed history (three identical sets, one unused set, one `1.0`/`1.00` pair) repoints to the oldest, removes the unused set, keeps the pair, writes the log record, creates the index; a second dedup is a no-op; rehash agrees with itself and with `--server` on MySQL for ASCII and non-ASCII vaults, and reports a mismatch after a vault is changed by SQL; rollback followed by upgrade equals a fresh upgrade.
  6. **Fixture on schema 6** (D32): `make_fixture.py` extended, fixture rebuilt, `MANIFEST.md`, GUI golden recomputed, smoke and golden and the browser check rerun, the diff against Step 0 explained value by value in the report. No GUI code changes in this phase; a GUI page that errors on the new fixture is a finding and a FIX in `{web}` under the GUI rules.
  7. **C++ on schema 6**: the C++ suite against the schema 6 fixture, and a new Catch2 test that reads the two sharing assignments and the `1.0`/`1.00` pair and compares with the Python results. No C++ source change expected; one needed → core-patch route.
  8. **CI**: `mysql-tests.yml` with both servers (D33); the schema equality step in `python-tests.yml` and `mysql-tests.yml`; `cli-smoke.yml` with the new `db` subcommands and `vers -l`; `lint-pyflakes.yml` with `{scripts}/schema` and `{scripts}/docs`.
  9. **Docs**: `{docs}/deployment/upgrade-2.5.md` (what changes, dry run, timing the backfill and the index on a copy, the same-day rule for Python clients, rollback, what C++ jobs see); `{docs}/concepts/constant-sets.md` (identity rule, sharing, why bytes and not numbers, what `vers -l` shows); the schema reference page at schema 6 with the reserved objects named as reserved; `{docs}/deployment/new-experiment.md` gains one line on buffer pool sizing for large InnoDB installs.
  10. **hallddb dry run** (D18): `ccdb db upgrade --dry-run` against hallddb through the read-only user, output into the report: DDL it would run, MyISAM tables (expected none), sets to hash, duplicate groups per table from the bounded measurement. The full scan only if the user answered the ASK of Step 0 with yes.
- Gate: Python suite, MySQL suite on both servers, schema equality on both and on SQLite, C++ suite on the schema 6 fixture, cli-smoke, GUI smoke `--check` and golden on the rebuilt fixture, browser check, docs link check, pyflakes.
- Done: `{space}/reports/phase0_schema6.md` is the review package: the schema diff; the list of changed files with line counts; the test modules before and after with counts; the design note's test matrix with a check mark per row and the test name; the dry-run outputs on the fixture and on hallddb; the dedup report on the fixture; the upgrade timings measured on the local copy of hallddb (821 431 sets); open questions. While the user authorizes git in chat, each work item is one commit on branch `schema6` and the review queue is `git diff v2.5...schema6` with a pull request into `v2.5`; without that authorization the changes stay uncommitted and the final checkpoint is a patch under `{space}`. **Gate B**: STATUS.md says `PHASE0 DONE — awaiting code review`; PHASE1 starts only when the user writes an approval in chat. Review remarks become PHASE0 work items under the same gate.
- Extra rows: a `constant_set` consumer cannot be adapted without changing what a user sees → ASK with both behaviors, continue with the rest. A byte-collision on hallddb's sample (D22) → STOP. The backfill estimate for hallddb exceeds one hour → ASK about the window; the design is unchanged. A test needs a write to a non-fixture database → STOP, never.

### PHASE1 — core features on schema 6: deprecation, tags, units, properties

Task: the behavior for what PHASE0 created, in Python, the CLI and, for tags, the C++ library.
Ends in the same human code review as PHASE0.

- **Step 0**: the PHASE0 gate on the approved tree.
- Work items, one checkpoint each:
  1. **Deprecation** (D28): provider methods `deprecate(obj, comment)` and `undeprecate(obj)` with log records; `get_directories`, `get_type_tables`, `get_variations` and the tree gain an `include_deprecated` keyword that defaults to the old behavior; `ls` and the CLI tree pass `False`; the `deprecate` command; `ls -a`, `ls -l`; the deprecation line in `info`. Tests: hidden by default, shown with the flag, a direct request and `cat`, `vers`, `info` on the object work unchanged, the comment is required, undo clears the fields, each log record.
  2. **Tags in Python** (D27): `Tag` CRUD in the provider with the future-time refusal; the request parser accepts `@NAME` and rejects a tag with a variation or a time; `get_assignment` by tag resolves with the tag's variation and time; the `tag` command; `cat`, `dump`, `vers`, `info` with a tag; the `rm -a` pin check. Tests: a tag made before a new assignment still resolves to the old one; a past-time tag; the parser cases; `rm -a` refused and forced.
  3. **Tags in C++**: `PathUtils` parses `@NAME`; the base provider's resolution path and the two providers resolve a tag with one query before the normal resolution; the same error for a tag with a variation or a time. Catch2 tests on the schema 6 fixture: the same tag cases as Python, answers compared with the Python results recorded in the fixture manifest. MySQL `[mysql]` tests as well.
  4. **Units** (D30): `mktbl` syntax, `info`, the dump header; tests including the old syntax.
  5. **Properties** (D29): provider methods, the `prop` command, `info` output; tests including the uniqueness rule and the log record.
  6. **Fixture**: `make_fixture.py` already holds the cases of D32; the fixture is not rebuilt in PHASE1. A missing case is a finding and an ASK, since a rebuild moves the GUI ruler.
  7. **CI and docs**: cli-smoke with `deprecate`, `tag`, `prop`, `ls -a`; `{docs}/concepts/tags.md` (the git analogy, what a tag freezes, what it does not, the no-delete policy), `{docs}/concepts/deprecation.md`, the CLI page with the three commands and the `@NAME` part, the C++ page with the tag request, `mktbl` units in the CLI page.
- Gate: the PHASE0 gate plus the new tests; GUI smoke bytes equal to Step 0 (no GUI change in this phase).
- Done: `phase1_core_features.md` in the shape of the PHASE0 review package; changes uncommitted; **Gate C**: PHASE2 starts only on the user's approval in chat.
- Extra rows: the C++ resolver change needs more than the files D1 names → core-patch route with the diff. A listing API in C++ seems to need the deprecation filter → ASK; the default is unchanged behavior.

### PHASE2 — GUI on schema 6

Task: what a user sees of schema 6 in the web GUI, under the GUI rules and the visual loop, one
visible feature per screenshot check.

- **Step 0**: the PHASE1 gate on the approved tree; GUI smoke and golden on the fixture.
- Work items, one checkpoint each:
  1. Assignment page: the `sha256`, the size, and "same data as" with links to the other assignments of the set; the versions list marks shared data with a small count.
  2. The "Show deprecated" switch (D28) on the tree, the versions, variations and compare pages, with `deprecated=all` in every URL and the muted rendering with a badge; comment and date in the info panels.
  3. Tags page (list) and tag page (the resolved assignment of every table for a run given in the URL, built on the compare-variations machinery); the Request page gains a tag selector that writes `@NAME`; a tag in the request string on the assignment page resolves.
  4. Table page: units per column; properties in the directory, table and variation info panels; the instance properties on the documentation or an About page.
  5. Golden extended for every new value; `pages.py` with the new URLs; browser check in both browsers.
- Gate: GUI smoke `--check`, golden, browser check, Python suite, docs link check, pyflakes; smoke bytes of unchanged pages equal to Step 0.
- Done: `phase2_gui.md` with the screenshots of each feature, counts, question sweep.
- Extra rows: a page needs a query the provider lacks → a read-only SQLAlchemy query in `{web}/queries.py` is normal work.

### PHASE3 — foundations

Task: the files an adoption review looks for first, the package that EICRecon can consume, and
the environment inventory the container phases need.

- **Step 0**: the PHASE2 gate. Environment: `nproc`, docker availability, the `eic-shell` image tag that pulls today and the JANA2, DD4hep and EICRecon versions inside it; spack availability; into `{space}/notes/ENVIRONMENT.md`. Seed items 1 to 11 confirmed or refuted as findings; item 3 by a consumer project under `{space}/notes/consumer/` that tries `find_package(ccdb)` against `cmake --install`; item 4 by searching the spack and eic-spack repositories. EICRecon style inventory: copy `DD4hep_service.{h,cc}`, one factory that uses it and the `services/` CMake pattern from the EICRecon checkout in `eic-shell` into `{space}/notes/epic/`, with a note of the conventions to mirror (D2). The docs link check script (`{scripts}/docs/check_links.py`) exists from PHASE0 item 9; its CI step in `documentation.yml`, run on the current site.
- Work items, one checkpoint each:
  1. `LICENSE` (D14), `CITATION.cff`, `.zenodo.json`; the README gains a Citation section; `unit_test_metadata_files.py` checks that the three files exist, that `CITATION.cff` parses and that its version equals `ccdb.version.version`.
  2. CMake package export: `install(TARGETS ccdb EXPORT ccdbTargets …)`, `ccdbConfig.cmake` and `ccdbConfigVersion.cmake`, namespace `ccdb::`, headers installed under `include/CCDB`. The consumer project moves to `{cpp}/examples/consumer/` and `cpp-tests.yml` gains a job that installs CCDB to a prefix and builds the consumer with `find_package(ccdb CONFIG REQUIRED)`. No source file of the library changes.
  3. Spack recipe (D13): `{repo}/spack/packages/ccdb/package.py` with the `+http`, `+jana2`, `+dd4hep` variants defined now and off; `cpp-tests.yml` or a new `spack.yml` installs it from the local repo in a spack container.
  4. Docs: `{docs}/get-started/installation.md` gains the CMake consumer snippet and the spack line; `install.linux.md` and `cpp/README.md` reconciled with the current build (seed item 11).
- Gate: Python suite, C++ suite including the consumer job, GUI smoke bytes equal to Step 0, docs link check, pyflakes.
- Done: `phase3_foundations.md` with the counts, the CI run links, the text of the upstream spack submission ready for the user, the question sweep.
- Extra rows: the license is not GPL-2.0-or-later → STOP; the file is a legal statement and the user decides. `eic-shell` does not pull or run on the host → ASK with the alternative (a JANA2 built from source in a plain container) and continue; PHASE4 and PHASE10 are frozen until answered.

### PHASE4 — JANA2 service

Task: `CCDB_service`, a JANA2 plugin and library in the EICRecon style, in `{jana2}`, built and
tested in `eic-shell`.

- **Step 0**: the PHASE3 gate; `{scripts}/eic/run_in_eic_shell.sh` runs `jana -v` and prints the JANA2 version from the image.
- Work items:
  1. Library `ccdb_jana2` and plugin `CCDB_service` (D2): `CCDB_service(JApplication*)`, parameters `ccdb:url` (default from `CCDB_CONNECTION`, then `JANA_CALIB_URL`), `ccdb:variation` (default `default`), `ccdb:time` (default empty, meaning newest), `ccdb:tag`, `ccdb:cache_dir`; one `ccdb::CalibrationGenerator` per service, one `ccdb::Calibration` per run through `GetCalibration(run)`, thread safe. Typed getters `GetConstants<T>(run, request)` for vectors, column maps and single values, returning the same values as `ccdb::Calibration::GetCalib`. Catch2 tests `[jana2]`: a `JApplication` with the plugin and a test SQLite database created by `ccdb db init` plus `ccdb add` and `ccdb tag`, asserting parameters, per-run caching, the time parameter, the tag parameter, the tag-with-time error, variation inheritance and the error for a missing table.
  2. Example factory `{jana2}/examples/` in the EICRecon factory layout: `ChangeRun()` fetches a table through the service and pushes the values into the algorithm configuration; `Process()` uses them. A test runs the factory over a dummy event source across two runs with different constants and asserts the switch.
  3. Resource helper `CCDB_service::GetResource(run, table)` (the resources decision): reads a one-row table with `url`, `sha256`, `size` columns, fetches the file into `ccdb:cache_dir` once, verifies the hash, returns the path. Test with a `file://` URL and a wrong hash.
  4. Retire `{cpp}/jana_plugin`: delete it; `{docs}/apis/jana.md` rewritten for JANA2 with the parameters, the factory example and the EICRecon integration steps (`add_subdirectory`, `find_package(ccdb)`); the CLI docs mention `JANA_CALIB_URL` compatibility in the service only.
  5. CI: `cpp-tests.yml` gains a job in the `eic-shell` image that configures with `-DCCDB_BUILD_JANA2=ON` and runs the `[jana2]` tests. The spack recipe's `+jana2` variant builds the same.
- Gate: Python suite, C++ suite plus `[jana2]` in `eic-shell`, consumer job, GUI smoke bytes equal to Step 0, docs link check, pyflakes.
- Done: `phase4_jana2.md` with the counts, the service API as a table, the output of the two-run factory test, the question sweep.
- Extra rows: the image's JANA2 lacks an API the service needs → PARK with the JANA2 version where it appears and the alternative. A change in `{cpp}/src/CCDB` seems needed beyond D1 → core-patch route.

### PHASE5 — HTTP API

Task: the FastAPI application `{api}` with the OpenAPI document, the three data forms, the run
bundle, cache headers, tags, deprecation and properties, the nginx configuration, the API ruler
and its CI.

- **Step 0**: the PHASE4 gate.
- Work items:
  1. Application skeleton (D4): `{api}/__init__.py` with `create_app(connection)` and `app`, engine and session handling as the GUI does (`AlchemyProvider.attach`, one engine per process, schema check once), `GET /api/v1/health` (same content as the GUI's), `GET /api/v1/instance` (the instance properties), the OpenAPI document with the version. `ccdb api` command. `unit_test_api_app.py`: startup without a connection fails with a message, health, instance, the OpenAPI document validates.
  2. Browse endpoints: directories (tree and one directory), tables (info with columns, comments, units and properties), variations (list, one, parents), run ranges, tags (list, one), versions of a table with the GUI's paging, sorting and filters, logs with search and paging, one log record; `deprecated=all` on every list (D28). Pydantic models per response. `{scripts}/api/pages.py`, `smoke.py`, `golden.py compute|compare` written with these endpoints; `api-tests.yml` runs them on the fixture.
  3. Assignments (D5, D6): resolve by request string (including `@NAME`), by id, or by `tag=` through `assignments.resolve_assignment`; `GET /api/v1/assignments/{id}` and `GET /api/v1/assignments?request=…` with the redirect rule; the three data forms with the blob header shape, the stored `sha256` and `size` and the `ETag`; compare (`diff` JSON and the unified diff file) by `a` and `b`. Golden: the GUI-equality check for `data.json`, the blob bytes equal to `constantSets.vault` by SQL, the header hash equal to the stored column and to `hashlib` over the served bytes, headers present and immutable where the rule says.
  4. Run bundle (D7): `{py}/snapshot.py` ported from `{scripts}/shallow_copy` to schema 6 with its behavior pinned by `unit_test_snapshot.py` (a bundle opened by the Python SQLite provider returns the same constants as the source for every table in the selection, shared sets included once); the script directory keeps a thin wrapper. `GET /api/v1/bundle` with the disk cache, the tag form and the explicit-time redirect; a test downloads a bundle for the fixture and reads it with `AlchemyProvider`.
  5. Table schema: `GET /api/v1/tables/{path}/schema` serving a JSON Schema built from the columns, with comments and units; test validates a `data.json` row set against it.
  6. Deployment: `docker/api/Dockerfile` (non-root, health check, pinned), `docker/nginx/ccdb-api.conf` with proxy cache, request coalescing (`proxy_cache_lock`) and the immutable rule; `{docs}/apis/http.md` (endpoints, the three data forms, the bundle, tags, the cache rules) and a section in `{docs}/deployment/new-experiment.md` under "Serving constants to jobs"; `api-tests.yml` gains a job that builds the image and runs `smoke.py --base-url` against it behind nginx, bytes equal to the in-process run.
  7. The hallddb measurement of the largest set through the GUI's `data.json` and the API's three forms (D18), read-only, into the report.
- Gate: Python suite, API smoke `--check`, API golden exact including GUI equality, `openapi.json` reviewed, container job bytes equal, C++ suite, GUI smoke bytes equal to Step 0, docs link check, pyflakes.
- Done: `phase5_api.md` with the counts, the endpoint table, the measured cost per data form for small and largest sets, the question sweep.
- Extra rows: an endpoint would need a provider method that does not exist → a read-only SQLAlchemy query in `{api}` is normal work (the common rule for web code); a write would be needed → STOP, the API is read-only.

### PHASE6 — demo

Task: one machine shows ePIC the whole thing: ePIC-shaped tables in MySQL, the API behind nginx,
the GUI, and a JANA2 application reading constants through `CCDB_service`, by variation and time
and by a campaign tag. The checkpoint at which ePIC is shown something.

- **Step 0**: the PHASE5 gate. Collect the EICRecon calibration parameter list (D17) from the checkout in `eic-shell` into `{space}/notes/epic/parameters.md`.
- Work items:
  1. `{scripts}/demo/make_epic_tables.py` (D17): deterministic, creates the tree (`/epic/<detector>/…`), tables with units, variations `default` and `mc`, assignments over two run ranges, one resources table, instance and table properties, one tag `campaign_demo`; a unit test checks determinism (two builds hash the same) and the counts.
  2. `docker/demo/compose.yml`: MySQL with the generated content, the API image, nginx, the GUI image; `docker/demo/README.md` with the three commands and the URLs. `{scripts}/demo/check.py` waits for health and runs the GUI smoke and the API smoke with `--base-url`, `--check`. A CI job (`demo.yml`) runs it.
  3. The JANA2 demo application `{jana2}/examples/epic_demo/`: reads two tables through the service for two runs, once with `ccdb:tag=campaign_demo`, prints them, exits 0; run in `eic-shell` against the compose stack with `ccdb:url=http://localhost:8080/api/v1` once PHASE8 exists, and with the MySQL URL until then. The CI job of PHASE4 runs it against the test SQLite.
  4. The EICRecon branch patch (D16): one factory in a copy of EICRecon inside `eic-shell`, built once on the host, the diff and the build log into `{space}/notes/epic/`; not in CI.
  5. Docs: `{docs}/get-started/demo.md`, linked from the index.
- Gate: PHASE5 gate plus `demo.yml` green and `check.py` clean on the host.
- Done: `phase6_demo.md` with the counts, a screenshot of the GUI on the demo tables, the demo application's output, the EICRecon build log, the question sweep. The report is also the hand-out for the ePIC meeting: a section written for that reader.
- Extra rows: EICRecon does not build on the host within two attempts → record the log, ASK, continue; the demo stands on the standalone application.

### PHASE7 — MCP server

Task: the read-only MCP server `{mcp}` over the API's service layer, the `ccdb mcp` command, a
recorded agent transcript.

- **Step 0**: the PHASE6 gate.
- Work items:
  1. Server (D9): tools `list_directories`, `list_tables`, `table_info`, `table_schema`, `list_variations`, `list_tags`, `resolve_request`, `get_constants` (paged rows, with the stored `sha256`), `list_versions`, `compare_assignments`, `search_log`, `instance_info`, `health`; every list tool takes `include_deprecated`, every resolving tool takes `tag`; each with a description written for an agent; resources: the concepts pages. `unit_test_mcp.py` through the SDK's in-memory client against the fixture: every tool answers, every answer equals the API's answer for the same arguments, the tool list contains no write operation, a provider with raising write methods is never triggered. Extra `mcp`, `ccdb mcp [--http PORT]`.
  2. `mcp-tests.yml`; pyflakes path.
  3. Docs: `{docs}/apis/mcp.md` with the tools table, a client configuration example, and a recorded transcript of an agent answering "what changed in `/epic/ecal/gains` between run periods A and B, and who changed it" on the demo tables, produced with the SDK's client in a script so it is reproducible.
- Gate: PHASE6 gate plus `mcp-tests.yml`.
- Done: `phase7_mcp.md`, question sweep.
- Extra rows: a tool would need information the API does not expose → add the API endpoint first, under the PHASE5 ruler, in this phase.

### PHASE8 — C++ HTTP provider

Task: `libccdb` reads through the API: an `http://` connection string downloads the run bundle
and the SQLite provider serves it.

- **Step 0**: the PHASE7 gate; libcurl found by CMake on the host and in CI.
- Work items:
  1. `HTTPDataProvider` (D10): URL parsing, bundle request with the explicit-time redirect followed, the tag form, download to the cache directory with the `sha256` verified, delegation to `SQLiteDataProvider` for every read, a clear error when the server or the cache directory is unavailable, timeouts through `CCDB_HTTP_TIMEOUT`. The one hook in `CalibrationGenerator.cc`. Catch2 `[http]` tests: the test harness starts `ccdb api` on the test SQLite on a free port (a Python helper under `{cpp}/src/tests/`), then reads constants through the provider and compares with the SQLite provider on the same file, by time and by tag; a second run with the server stopped reads from the cache; a wrong hash is rejected.
  2. `JANA_CALIB_URL=http://…` and `ccdb:url=http://…` work in the JANA2 service through the generator; the PHASE6 demo application runs against the compose stack through HTTP; the `[jana2]` test gains the HTTP case.
  3. CI: `cpp-tests.yml` gains the `[http]` job; the spack recipe's `+http` variant.
  4. Docs: `{docs}/apis/cpp.md` gains the HTTP connection string, the cache directory and the environment variables; `new-experiment.md`'s table of the ways jobs read constants gains the row.
- Gate: PHASE7 gate plus `[http]` tests, demo check over HTTP.
- Done: `phase8_http_provider.md`, question sweep.
- Extra rows: libcurl is unavailable in `eic-shell` → ASK; the provider stays optional and the demo uses MySQL in that image.

### PHASE9 — scaling numbers

Task: the published load test: configurations at the job counts ePIC quotes, on a
hallddb-shaped schema 6 database.

- **Step 0**: the PHASE8 gate; the PHASE0 survey numbers (or the fixture distribution, stated).
- Work items:
  1. `{scripts}/loadtest/make_db.py` (D11): the synthetic database from the survey, with the measured duplicate fraction so shared sets are represented; deterministic; unit tests on the generator's distributions.
  2. `{scripts}/loadtest/client.py`: asyncio client simulating N jobs that start within a window and each request M tables (per-table requests) or one bundle; reports median, p99, error rate, backend request count; unit tests on the aggregation over a recorded sample.
  3. Runs: MySQL direct (connection cliff), API bare, API behind nginx, bundle per run behind nginx, SQLite snapshot on a local filesystem; N in {1 000, 20 000, 100 000} with 200 tables, on the host with nothing else running; raw results as JSON in `{space}/reports/loadtest/`.
  4. Docs: `{docs}/deployment/scaling.md` with the method, the tables, one plot per configuration, and the statement that the cache is mandatory; linked from `new-experiment.md` and `streaming-readout.md`.
- Gate: PHASE8 gate plus the scripts' unit tests and pyflakes; the docs page's numbers equal the JSON.
- Done: `phase9_scaling.md`, question sweep.
- Extra rows: the host cannot simulate 100 000 clients → report the largest N that ran cleanly and the extrapolation method; ASK about a second machine.

### PHASE10 — DD4hep

Task: the two plugins of D12 in `{dd4hep}`, built and tested in `eic-shell`.

- **Step 0**: the PHASE9 gate; the DD4hep version in the image.
- Work items:
  1. `CCDB_Constants` geometry plugin: `<plugin name="CCDB_Constants" table="/epic/geometry/ecal_dims" run="1"/>` defines one constant per column, with the column's units in the constant's documentation string; test loads a compact XML in a `dd4hep::Detector` against a test SQLite and asserts `detector.constant<double>(name)`.
  2. `CCDB_ConditionsLoader`: a `ConditionsDataLoader` that, for a detector element and a run IOV, loads a CCDB table's rows into conditions (one row per element, columns as values), alignment deltas as the example with `DDAlign` applying them; test loads conditions for two runs and asserts the values and the IOV; a second test applies a delta and reads the element's placement back.
  3. CMake option, the `eic-shell` CI job, the spack variant.
  4. Docs: `{docs}/apis/dd4hep.md` with the XML snippets, the table shapes, and the simulation workflow (which run numbers, the `mc` variation, a tag per production); linked from `streaming-readout.md`'s Simulation section.
- Gate: PHASE9 gate plus the DD4hep tests in `eic-shell`.
- Done: `phase10_dd4hep.md`, question sweep.
- Extra rows: DDCond's loader interface in the image's version differs from the documentation → PARK with the version and the alternative (constants plugin only); the constants plugin item continues.

### PHASE11 — exports, data access and FAIR page

Task: the analysis-side pieces and the page that maps CCDB onto FAIR, now with the fields schema
6 added.

- **Step 0**: the PHASE10 gate.
- Work items:
  1. `ccdb export parquet <table> [-v] [-r] [-t] [--tag] -o DIR` (extra `export`): one file per table with the assignment metadata as columns (id, run range, variation, created, author, comment, `sha256`) and the units as column metadata, implemented in a new command module over the provider; `unit_test_export_parquet.py` reads the file back with pyarrow and compares with the provider; a DuckDB and a polars recipe in the docs, run as a test where the library is installed.
  2. `ccdb.frames.to_dataframe(provider, request)` returning pandas (and polars when installed) with typed columns and units in the frame's attributes; tests.
  3. Data card: `GET /tables/{path}/card` in the GUI (visual loop) and `/api/v1/tables/{path}/card` in the API: purpose and the other table properties, columns with comments and units, authors, run coverage, version count, last change, tags that cover it, license and citation from the instance properties; golden checks every value against SQL.
  4. Change feed: `GET /api/v1/logs.atom`; test validates the feed.
  5. Docs: `{docs}/concepts/fair.md` with the mapping table in two columns, today and roadmap, every row linking the feature; written under the feature-page rules.
- Gate: PHASE10 gate plus the new tests; GUI gate for the card page.
- Done: `phase11_exports.md`, question sweep.

### PHASE12 — pitch and release

Task: release 2.5.0 and the material for the ePIC decision.

- **Step 0**: the PHASE11 gate on the tree.
- Work items:
  1. Version `2.5.0`; release notes `{space}/reports/release-2.5.0.md` in the 2.4.0 notes' shape, with an Upgrading section that states schema 6, the same-day rule for Python clients, the dry run and the rollback; `{docs}/index.md` and README updated under the feature-page rules; the docs sidebar complete; every docs page link-checked.
  2. `{space}/reports/comparison.md` (D19) and `{space}/reports/pitch-outline.md`: the technical fit first (EICRecon service, tags as campaign snapshots, streaming model, scaling numbers), then stewardship and FAIR, then the roadmap.
  3. The upstream texts: the spack pull request, the eic-spack request, the Zenodo steps, ready for the user.
- Gate: every suite and ruler of the program green on the final tree.
- Done: `phase12_release.md`; the final checkpoint is what the user reviews, commits and tags.

## Deferred to 2.6 (for the record, not for this program)

The validity-time resolver and request syntax on the reserved `timeRanges`, assignment
deprecation, foreign key constraints on InnoDB, a canonical numeric form beside the byte
identity, Postgres on the Python side, a per-table HTTP fallback in the C++ provider, the
deprecation filter in the C++ listing APIs, an RCDB time-to-run endpoint in the API, the HSF
conditions database REST adapter, a move of the GUI query helpers into a shared service package.
