# CCDB 2.5 — AI-readiness program plan

To start a run, the user gives you one line: `Read {repo}/web-agents-common.md, {repo}/ccdb-2.5.md and {repo}/ccdb-ai-ready.md first. Run PHASE-A<N>.`

Read the three files in that order before anything else:

1. `web-agents-common.md` — the work protocol, the FIX / ASK / PARK / STOP protocol, the memory
   layout of `{space}`, the findings index, and the documentation and coding rules.
2. `ccdb-2.5.md` — the testing rule and the shared ruler of the 2.5 program. Both apply here
   unchanged: every work item lands with a test that fails without the change, and the gate of a
   phase is the full 2.5 ruler plus the phase's own numbers.
3. This file — what belongs to this program: the goal, the decisions already made, the defaults
   for open decisions and the phases.

Three rules of the common file are overridden here by the user's decisions of 2026-11-03, and only
in the way A-D6 to A-D8 state: git (commits on a branch), the core scope (the files A-D7 names),
and the run mode. Everywhere else the common rules stand.

The program follows the 2.5 program and lands in the same release: v2.5.0 is not tagged. Nothing
here changes the database schema. Every item is a command, an endpoint, an MCP tool, a GUI page or
a library call over schema 6 as it is.

## Paths

| name | path | what lives there |
|---|---|---|
| {repo} | /home/romanov/dev/ccdb-ai-ready | a git worktree of the CCDB checkout on branch `ai-ready`, created from `origin/v2-main` (b16f3b6, 2.5.0 merged by #122) |
| {space} | /home/romanov/dev/ccdb/space-ccdb-2.5 | the 2.5 workspace in the main checkout, outside version control. This program's reports go to `{space}/reports/ai-ready/` |
| {py} | {repo}/python/ccdb | the Python package: `provider.py`, `model.py`, `cmd/commands/`, `api/`, `mcp/`, `webgui/` |
| {cpp} | {repo}/cpp | the C++ library (`src/CCDB`), Catch2 tests (`src/tests`) |
| {jana2} | {repo}/jana2 | the JANA2 service |
| {scripts} | {repo}/scripts | `api/` (the API ruler), `docs/`, `mcp/` |
| {docs} | {repo}/docs | docsify site |
| {ci} | {repo}/.github/workflows | the workflows named in `ccdb-2.5.md` |
| {examples} | {repo}/python/examples | the examples `python-examples.yml` runs |

## Goal

Make CCDB 2.5 the calibration database whose readiness for AI use can be measured, whose
constants carry their provenance into every job that reads them, and whose tags name a
processing pass completely. The source of the requirements is the assessment framework of the
GlueX AI-readiness article (Panta, Sawatzky, Morean, Romanov, Higinbotham, 2026, arXiv:2609.34987): seven categories, 26 sub-criteria, and
the rule that every readiness claim is reproducible, comparable and defensible. The report
`{space}/reports/ai-readiness.md` maps the article onto CCDB and lists the code changes; this
plan implements changes 1, 2, 3, 4, 5, 6, 8 and 10 of that list. Changes 7 (value expectations on
`add`), 9 (RCDB and Rucio links), 11 (locks and roles) and 12 (agents that write) are not in this
program.

What the program delivers, in the words a user meets:

- `ccdb db readiness`: a deterministic JSON profile of an instance, the same numbers at
  `/api/v1/readiness`, as the MCP tool `readiness`, and as a GUI page.
- A record of the constants a job resolved: in the C++ and Python libraries when a program
  turns it on (`EnableUsageRecord`), written by the JANA2 service, checked by `ccdb provenance`.
- Properties on tags, so a tag names the software, container, data and DOI of a pass.
- `ccdb export tag`: the constants of a tag as one SQLite file with a DataCite metadata file and a
  hash, ready for a repository deposit. CCDB makes no network call.
- schema.org `Dataset` metadata on every data card.
- A property vocabulary that `prop set` checks, served by the API.
- UCUM unit checks in `mktbl` and `edit`, counted by the readiness profile.
- A Great Expectations example on the Parquet export, run in CI.

Everything that works in 2.5.0 keeps working. No flag changes meaning; new flags and commands only
add.

## Decisions already made by the user

| id | decision |
|---|---|
| A-D1 | Everything in this plan goes into 2.5; there is no 2.5.x or 2.6 split (2026-11-03). |
| A-D2 | CCDB never contacts an outside service by itself: no Zenodo upload, no hooks. `export tag` writes files; a person or a CI job uploads them (2026-11-03). |
| A-D3 | Collaboration data work (units, descriptions, licenses, uncertainty tables, cut values) is out of scope. The program measures these gaps; it does not fill them (2026-11-03). |
| A-D4 | Recommendations and docs name cheap, gradual steps in plain language (feedback of 2026-07-20 on the article). |
| A-D5 | Confirmation flags keep 2.4's `--<verb>-i-am-sure` spelling; no flag name implies an automatic action (standing). |
| A-D6 | Git: `please-git` for this program (2026-11-03). Work on branch `ai-ready` in the worktree `{repo}`; one commit per work item once its test and gate checks pass, so commits replace the checkpoints of the common file. No pull request. No push until PHASE-A5 is done, because `documentation.yml` publishes the docs site from any pushed branch. The main checkout (`/home/romanov/dev/ccdb`, branch `fix-56-edit-comment`, PR #125) is not touched. |
| A-D7 | Core scope (default taken 2026-11-03, the user stated no preference). These existing core files may be edited, with their tests: A1 `{py}/cmd/commands/db.py`; A2 `{cpp}/src/CCDB/Calibration.h`, `Calibration.cc`, `{py}/provider.py`; A3 `{py}/provider.py` (`PROPERTY_OWNER_TYPES`, property lookup by tag), `{py}/cmd/commands/prop.py`, `tag.py`, `info.py`, `export.py`; A4 `prop.py`, `mktbl.py`, `edit.py`; plus command registration, `pyproject.toml` and `{ci}`. New files need no decision. A change to any other existing core file goes the core-patch PARK route. |
| A-D8 | Run mode (default taken 2026-11-03). PHASE-A0 and PHASE-A1 run, then the run stops so the user checks the readiness profile the article prints. After the user's OK, A2 to A5 run without stopping between phases: a gate is a check, and a non-blocking question takes its default. |
| A-D9 | The docs written on 2026-11-03 describe every phase as done; they wait uncommitted in `{repo}`. Each phase commits only the sections it implements, corrected to the code it shipped (default taken 2026-11-03). |
| A-D10 | The record of resolved assignments is off by default in both libraries; a program turns it on: C++ `Calibration::EnableUsageRecord(bool)`, `IsUsageRecordEnabled()`, `GetResolvedAssignments()`; Python `AlchemyProvider.usage_record_enabled = True`, `resolved_assignments`. The JANA2 service turns it on when `ccdb:provenance=PATH` is set (user, 2026-11-03, Q64). |

## Defaults for open decisions

The user answers these in chat. Until then, the default applies.

| id | question | default |
|---|---|---|
| A-Q1 | Change 2, light or full? | Both, in this order: the light item (the JANA2 service logs the pinned time or tag and warns when a production job has neither) is PHASE-A2 item 1; the full record is items 2–4. The user may stop the phase after item 1. |
| A-Q2 | Where does the JANA2 service write the job record? | Parameter `ccdb:provenance=PATH`; empty by default, so nothing is written unless asked. |
| A-Q3 | Is an unknown property name an error? | A warning. `--free` silences it. An instance may extend the vocabulary with the instance property `property_names` (a comma-separated list). |
| A-Q4 | UCUM units: error or warning? | A warning in `mktbl` and `edit`; never an error. Physics units outside UCUM are written as annotations (`{ADC}`), which UCUM allows. |
| A-Q5 | The staleness window of the readiness profile | 5 years by default (`--stale-years`), echoed in the profile's `config`. |
| A-Q6 | Which engines does `export tag` support? | MySQL, MariaDB and SQLite sources; the output is always SQLite, built by the bundle builder of the API with the run range opened to every run. |

## Phase plan

Phases run in order. PHASE-A0 is the baseline. Each later phase has a Step 0, work items, a gate,
a done criterion. The next phase starts when the previous report is in `{space}/reports/ai-ready/`
and its BLOCKING questions are answered in chat.

### PHASE-A0 — baseline

Task: a green tree and the numbers the program will change.

- **Step 0**: the branch `ai-ready` from `v2-main` in the worktree `{repo}`; the only uncommitted changes are this plan and the docs of A-D9. Commit the plan first.
- Work items:
  1. Run the whole 2.5 ruler; record the counts in `{space}/reports/ai-ready/a0_baseline.md`.
  2. Record the Hall D profile by hand once more from the schema 6 trial copy (read-only): units, descriptions, comments, open-ended ranges, stale tables, anonymous authors, duplicate sets, instance properties. These are the numbers `ccdb db readiness` must reproduce in PHASE-A1.
- Gate: the ruler green.
- Done: `a0_baseline.md`.

### PHASE-A1 — the readiness profile (change 1)

Task: one deterministic computation of an instance's readiness, served four ways.

- **Step 0**: the A0 gate.
- Work items:
  1. `{py}/readiness.py`: `profile(provider, config) -> dict`. The dict holds `config` (the inputs: `stale_years`, `generated`, the CCDB version, the schema version), `metadata` (columns with units / total; tables with a description / total; versions with a comment / total; tables with a `contact`, `source_url` or `doc_url` property), `history` (open-ended run ranges; versions by `anonymous`; tables with no write for `stale_years`; tables never filled; deprecated tables), `data` (constant sets, duplicate sets merged, bytes), `instance` (`license`, `citation`, `contact`, `experiment`, `url` set or not), `units` (columns whose unit string is valid UCUM, after PHASE-A4; `null` before). Every count is one SQL query; no sampling. `unit_test_readiness.py` builds a fixture and checks every number; a second test runs the profile twice and compares the dicts.
  2. `ccdb db readiness [--stale-years N] [--json]`: the text form is a table of the same numbers; `--json` prints the dict. `integ_test_cli_manager.py` gets the command; `cli-smoke.yml` runs it.
  3. `GET /api/v1/readiness?stale_years=N`: the dict, `Cache-Control: public, max-age=3600`. `{scripts}/api/pages.py` and `golden.py` learn it; the OpenAPI document diff is in the report.
  4. MCP tool `readiness(stale_years)`: the same dict. `{scripts}/mcp/transcript.py` gets one step.
  5. GUI page `/readiness`: the numbers with one bar per coverage item (visual loop); a link from the instance page.
  6. Docs: `{docs}/concepts/ai-readiness.md` (the metric definitions, one line each, and how to read the profile); the `db` section of `{docs}/cli.md`; `{docs}/apis/http.md` and `{docs}/apis/mcp.md` rows.
- Gate: the ruler plus the new tests; the profile of the Hall D trial copy equals the A0 hand count.
- Done: `a1_readiness.md` with the Hall D profile as JSON.

### PHASE-A2 — what a job resolved (change 2)

Task: the calibration third of a processing pass, recorded by the code that resolves it.

- **Step 0**: the A1 gate.
- Work items:
  1. **Light.** `CCDB_service` logs at startup the connection string (password hidden), the variation, and the time or tag it pins; when neither `ccdb:time` nor `ccdb:tag` is set, it logs a warning that the job reads the newest constants and cannot be repeated by its parameters. A `[jana2]` test checks both messages. *The user may end the phase here (A-Q1).*
  2. `Calibration::GetResolvedAssignments()` in `{cpp}`: for every request served since connection, the request string, the assignment id, the SHA-256, the run range, the variation and the creation time, in request order; recorded only after `EnableUsageRecord(true)` (A-D10); a `[sqlite]` and an `[http]` Catch2 test. Python: `AlchemyProvider.usage_record_enabled` (False) and `resolved_assignments`, filled by `get_assignment`; `unit_test_usage_record.py`.
  3. `CCDB_service` parameter `ccdb:provenance=PATH` (A-Q2): at the end of the job, the list as JSON with a header (`ccdb_version`, `connection` without password, `variation`, `time` or `tag`, `run`, `generated`). A `[jana2]` test reads the file back.
  4. `ccdb provenance FILE.json [--tag]`: checks every assignment id and hash against the connected database and prints the tags whose resolution equals the file's; exit code 1 when a hash differs. Test in `integ_test_cli_manager.py`.
  5. Docs: a section "What a job used" in `{docs}/apis/jana.md` and `{docs}/apis/cpp.md`; `{docs}/cli.md`.
- Gate: the ruler plus the new tests; the JANA2 and C++ suites through `run_in_eic_shell.sh`.
- Done: `a2_provenance.md`.

### PHASE-A3 — tags as named passes (changes 3 and 10)

Task: a tag carries what a pass needs, and leaves the database as one file ready for a deposit.

- **Step 0**: the A2 gate.
- Work items:
  1. `tag` as a property owner type (`PROPERTY_OWNER_TYPES` gains `"tag"`; `owner_id` is the tag's id; no schema change). `ccdb prop set|get|ls|rm @NAME KEY [VALUE]` — the `@` names a tag as it does in requests. Standard names for tags: `software`, `container`, `data`, `rucio_did`, `doi`, `description`, `citation`. `ccdb tag ls -l`, `ccdb info @NAME`, `/api/v1/tags/{name}`, the MCP `list_tags` and the GUI tag page show them. Tests: `unit_test_properties.py` extended; API golden rows.
  2. `ccdb export tag @NAME -o DIR`: writes `DIR/NAME.sqlite` (every table, the tag's variation chain, every assignment the tag sees for every run, the tag itself), `DIR/NAME.sha256`, and `DIR/NAME.datacite.json` built from the instance properties (`citation` → creators and title, `license`, `url`) and the tag's properties (`description`, `software`, `container`, `data`, `rucio_did`) in DataCite 4.5 JSON; `relatedIdentifiers` carries the `doi` of a previous export of the same tag when set. The builder is the API bundle builder with the run clip removed (A-Q6). `unit_test_export_tag.py` opens the file with the Python provider and compares one request per table against the source; it validates the metadata JSON against the DataCite schema stored under `{scripts}/docs/`.
  3. Docs: `{docs}/concepts/tags.md` (properties; the deposit workflow in four lines: export, upload, record the DOI with `prop set @NAME doi`), `{docs}/cli.md`.
- Gate: the ruler plus the new tests; `export tag` of the GUI fixture's tag opened by the C++ library (Catch2 `[sqlite]`).
- Done: `a3_tags.md`.

### PHASE-A4 — vocabulary and discovery (changes 4, 6, 8)

Task: metadata that programs can check and catalogs can find.

- **Step 0**: the A3 gate.
- Work items:
  1. `{py}/vocabulary.py`: the standard property names per owner type as data (the table of `{docs}/cli.md` moves here and the docs page is generated from it by `{scripts}/docs/`), plus the instance extension `property_names` (A-Q3). `prop set` warns on an unknown name unless `--free`. `GET /api/v1/properties/vocabulary` serves it. Tests.
  2. UCUM: `{py}/units.py` validates a unit string against UCUM's grammar with the base units, prefixes and the common derived units in a table (no network, no new dependency); annotations in braces pass. `mktbl` and `edit` warn on an invalid unit (A-Q4). The readiness profile fills `units`. `unit_test_units.py` with the units of the Hall D trial copy's known tables as cases.
  3. schema.org `Dataset` as JSON-LD: a `<script type="application/ld+json">` block on the GUI card page and `GET /api/v1/tables/{path}/card?format=jsonld`; fields from the card (name, description, license, citation, creator from authors, dateModified, variableMeasured from the columns with units, identifier = the table path, url). A test validates required fields; the GUI check runs the card page.
  4. Docs: `{docs}/concepts/fair.md` roadmap column: rows F4 and I2 move to today; `{docs}/cli.md` prop and mktbl sections.
- Gate: the ruler plus the new tests; GUI gate for the card page.
- Done: `a4_vocabulary.md`.

### PHASE-A5 — the expectations example and the docs sweep (change 5)

Task: the tabular readiness tools shown working on CCDB data, and every page consistent.

- **Step 0**: the A4 gate.
- Work items:
  1. `{examples}/example_expectations_parquet.py`: exports one demo table to Parquet, runs a Great Expectations suite (column set, types, `min`/`max` on one column, row count per assignment) and prints the result; `python-examples.yml` runs it with the `export` extra and `great_expectations` installed in that job only.
  2. `{docs}/apis/analysis.md` section "Checks with Great Expectations" showing the example; `{scripts}/docs/test_cli_like_docs.py`-style check that the page shows the file.
  3. Docs sweep: `{docs}/index.md` "AI and agent ready" group gets the readiness profile, the job record and the tag export as items; `{docs}/_sidebar.md` gets `concepts/ai-readiness.md`; `check_links.py` green.
  4. Release notes section "AI readiness" in `{space}/reports/release-2.5.0.md`.
- Gate: every suite and ruler green on the final tree.
- Done: `a5_release.md`; the final checkpoint is what the user reviews.

## State of the program

Every phase is done on the branch `ai-ready` (2026-11-03): reports `a0_baseline.md` to `a5_release.md` in
`{space}/reports/ai-ready/`. The docs on the branch describe what the branch holds; each phase committed its own
sections. The article *Making a Calibration Database AI-Ready: CCDB 2.5*
(`/od/JLab/Projects/AiDataReady/ccdb-ai-ready`) describes the same code; its status block lists the sentences that
depend on the branch until it is merged into `v2-main`.

Deviations from the phases as written, each with its reason in the phase report:

| phase | deviation |
|---|---|
| A1 | two open-ended fields (`open_ended_run_ranges` from a run above 0, `versions_for_all_runs` from 0); `history.tags` and `data.unused_sets` added |
| A2 | the record is off by default and turned on by `EnableUsageRecord` / `usage_record_enabled` (A-D10); it keeps distinct resolutions without run range and creation time, which `ccdb provenance` reads by id |
| A3 | the DOI is not shown on data cards; the DataCite record also names the instance contact |
| A4 | `edit` does not check units (a stub on v2-main, rewritten by #125); `AlchemyProvider.set_column_units` sets units of old tables; the UCUM module is `ccdb/ucum.py` |
| A5 | the example runs on the standard test database, in the Python 3.9 examples job |
