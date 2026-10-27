# CCDB web GUI — production plan and common rules

> Since 2026-10-14 the common rules live in `{repo}/web-agents-common.md` and the check scripts (`tools/` below) in `{repo}/scripts/webgui/`, run with `--space {space}`. This file stays the plan of the first program.

To start a run, the user gives you one line: `Read /work/ccdb-webgui.md first. Run PHASE<N>.`
This file holds the whole program: the goal, the phase plan with each
phase's task, ruler and done criterion, then the environment, the work
protocol, the FIX / ASK / PARK / STOP protocol, and the documentation,
coding and git rules.

## Paths

| name | path | what lives there |
|---|---|---|
| {repo} | /home/romanov/dev/ccdb | CCDB repository checkout, branch `v2-main` |
| {web} | {repo}/python/ccdb/webgui | Flask app (`__init__.py`), `templates/`, `static/` |
| {space} | {repo}/space-ccdb-webgui | your notes, reports, plots, screenshots, patches |

## Goal

Make the CCDB web GUI ready for production: correct data on every page, current libraries, a
consistent visual style with a light/dark theme switch, and a deployable package. The GUI is
read-only. It serves two uses, and both must keep working:

1. Local: `ccdb gui [-p PORT]` — the CLI starts Flask with the CLI connection string.
2. Server: gunicorn serves `ccdbweb:app` ({repo}/python/ccdbweb.py) behind a reverse proxy, from a Docker image ({repo}/docker/webgui/Dockerfile).

## Decisions already made by the user

Do not re-litigate these.

Decided on 2026-10-13 after a challenge of each item; evidence and code samples in `{space}/planning/challenge.md`, mockups in `{space}/planning/mock/`.

- Remove jQuery completely: no jQuery, no jQuery UI, no jQuery plugins.
- Drop DataTables. No table library replaces it: tables are server-rendered pages (see below).
- Bootstrap 5.3.8 (latest 5.3.x) is the only CSS framework, loaded as one stylesheet plus Bootstrap's own JS bundle. Remove the local Bootstrap 4.2.1 files, Material Design Lite, Font Awesome, Feather and the Bootstrap Icons font. Own CSS stays under 200 lines in `static/css/ccdb.css`, built on Bootstrap CSS variables. Keep the markup shallow: Bootstrap 6 renames responsive classes (`col-md-6` → `md:col-6`), and the move to 6.0 must stay a rename pass. Bootstrap 6 alpha and Pico CSS were evaluated and rejected for now (alpha five days old with a Chrome 130 / Firefox 132 browser floor; Pico lacks sidebar, pagination and modal).
- Icons: an inline SVG sprite in the base template with the icons the app uses, copied from Bootstrap Icons (MIT): folder, open folder, table, info, sun, moon, menu, download, copy, search. Usage `<svg class="ico"><use href="#i-folder"/></svg>`; colors follow `currentColor`. No icon font.
- Layout: top navbar with brand, version and theme menu; left sidebar (`offcanvas-md`) that becomes a drawer behind a hamburger button on phones; `<main>` fills the rest.
- Tree: native `<details>/<summary>` with a filter box and open state remembered in `localStorage`, in about 20 lines of vanilla JS. No tree library (Wunderbaum rejected: beta, own look, nothing needed at 65 directories and 684 tables). Info popups load HTML into a Bootstrap modal through `fetch`.
- Tables (versions, logs, variations, show-request data): server-rendered. Page, sort, search and filters (run range, variation) are GET parameters; Bootstrap's pagination component renders page links; every view has a shareable URL and works without JavaScript. A small vanilla script adds live search by re-fetching only the table fragment. No table library, no HTMX.
- Data seam for future features (comparison of tables, plots): every page is built from plain data (dataclasses or dicts) returned by query helpers, and templates only render that data. A JSON view of the same data is then one `jsonify` call. Assignment data is available as JSON and as the text dump from the start. Plot and comparison pages are out of scope for this program; the structure must not stand in their way.
- Assignment addressing: the CCDB request string (`/FCAL/gains:30000:default:2017-11-16_10-03-20`) is the primary identifier — it is what the CLI, the C++ and Python APIs and users' notes use, so every assignment view accepts it and every link shown to users carries it. The database id is accepted as a second form (`/assignments/<id>`) for short links and tooling; it never replaces the request string. One resolver turns either form into an assignment, and all views (page, JSON, text dump, future comparison) go through it. Tables and directories keep their path URLs.
- Request page: native `<datalist>` over all tables for autocomplete; no library.
- Add a light/dark theme switch: light, dark and auto (follows the OS). It uses Bootstrap `data-bs-theme`, persists in `localStorage`, and the page must not flash the wrong theme on load.
- Keep JavaScript out of Jinja templates. Put it in `static/js/*.js` ES modules. Pass server data through `data-*` attributes or `<script type="application/json">` blocks. Two inline scripts are allowed: the theme bootstrap in `<head>` (it must run before first paint) and a short module call that starts a page. A few lines inline beat an extra file when a page needs only a few lines.

## Defaults for open decisions

Follow the default. Each item is already an ASK in the Step 0 question seed (see PHASE0).

| # | decision | default |
|---|---|---|
| D1 | asset delivery | Vendor pinned dist files into `{web}/static/vendor/<lib>-<version>/`, fetched by a committed script that checks a sha256 manifest. The wheel already ships `static/`. A server on the lab network then runs with no CDN access. |
| D2 | JS build step | None: no Node, no npm, no bundler. Native ES modules plus vendored dist files. Maintainers then need only Python. |
| D3 | table page size and search fields | Default page size 50, selectable 25/50/100/200. Search matches comment and author on versions, description and author on logs, name and comment on variations. Sorting on every column shown. |
| D4 | tree page weight | The tree is rendered server-side in full (65 directories, 684 tables today; the mockup with the inline SVG sprite is 352 KB HTML, 18 KB gzipped — enable gzip in gunicorn or the reverse proxy). Switch to lazy loading per directory only if the tree grows past ~5000 nodes. |
| D5 | URL prefix | The app works under a sub-path (for example `/ccdb/`). Build every URL with `url_for`, also the URLs JavaScript uses. Enable `ProxyFix` through a config knob. |
| D6 | connection config | `CCDB_CONNECTION` only, the variable the `ccdb` command reads (the old `SQL_CONNECTION_STRING` is gone, user decision 2026-10-14). Not set → fail at startup with a clear message. No default credentials in code. |

## Known problems (seed list — verify each in PHASE0)

Observed on 2026-10-13 against `mysql://ccdb_user@hallddb.jlab.org/ccdb` with commit f61eaaf.

Data and backend:

1. The table info modal shows the parent directory: `AlchemyProvider.get_type_table_by_id` (provider.py) returns `parent_dir` instead of the table. `/get-table-info/1` showed "Table name: test_vars, DB ID 3".
2. Authors: the table modal renders `table.author`, but `TypeTable` has no `author` relationship, so the field is blank. The directory modal shows the numeric `author_id`. `show_request` and `download_request` look up the author with hand-written queries, although `Assignment.author` exists.
3. Missing objects return 500 instead of 404: `/get-dir-info/999999` (KeyError in `get_directory_by_id`), `/get-table-info/999999` (NoResultFound), `/show_request?request=/FCAL/gains:1:nosuchvar` (template reads `None.constant_set`), and `/dowload_request` with no `request` (the view returns None).
4. An unknown table in `/show_request` returns 200 with the plain-text body "Something is not found in the DB".
5. Slow versions page: `/versions/FCAL/gains` renders 3484 rows (1.6 MB) in 24 s on the lab network and 121 s over a remote link. Suspected cause: lazy loads of `run_range` and `variation` for each row (N+1 queries over the WAN), plus all rows rendered server-side.
6. The request form autocomplete offers only the first 10 tables (`acpl.slice(0, 10)` in test_request.html).
7. The logs page loads the latest 1000 records but sorts them oldest first.
8. The run-range sentinel `2147483647` appears raw in some views. Others render it as "inf." or ∞.
9. Variations show no hierarchy, although `Variation.parent` exists.
10. The app creates a new SQLAlchemy engine on every request, runs the schema version check on every request, and never disposes the engine. Open MySQL sockets grew from 9 to 17 over 20 requests. There is no `pool_pre_ping`, so a long-running server risks "MySQL server has gone away".
11. The app has a hard-coded default connection string with test credentials, and gunicorn deployments ignore `CCDB_CONNECTION`.
12. `print_app_functions` prints to stdout on every app creation.

Security:

13. HTML injection: assignment comments render with `|safe`. `dir_to_ul` builds HTML with unescaped f-strings. `tables_autocomplete` is concatenated into a `<script>` with `|safe`. `download_request` returns unescaped data as `text/html`.

Frontend:

14. `dash_base.html` loads Bootstrap 5.3.3 from a CDN and then the local Bootstrap 4.2.1 CSS, so Bootstrap 4 rules override Bootstrap 5.
15. Pages load jQuery 3.5.1 or 3.6.0 (some pages twice), jQuery UI 1.13.1, DataTables 1.10.20 with Bootstrap 4 styling, Font Awesome 6.0.0-beta3, and unpinned Feather and Bootstrap Icons.
16. The favicon path `/docs/4.0/assets/img/favicons/favicon.ico` is broken. The navbar hard-codes "CCDB v 2.0" instead of using `ccdb.version`.
17. JavaScript uses absolute URLs (`/get-dir-info/...`), which break under a URL prefix.
18. The footer bug link (halldweb1 MantisBT) and the documentation page (GitHub issues) disagree.
19. Dead code and assets: `index.html` (Material Design Lite demo), `direcotires.html` and the `/dirs` route (debug list, broken `document.onload`), `/hello`, `material.*`, `styles.css`, `dog.png`, `user.jpg`, `bootstrap*.css/js` 4.2.1. The route `/dowload_request` is misspelled.

Packaging:

20. Dockerfile: `python:3.10-slim`, unpinned requirements, unused Bokeh, root user, no health check, and it does not install the `ccdb` package. (The `web` extra stays without a WSGI server by decision; the image installs its own.)

## Phase plan

Each phase has a Step 0 (finish and record it before any other work), a ruler (what "correct"
means), a done criterion, and extra decision-table rows. Phases run in order. The next phase
starts only after the user has read the previous report and answered its BLOCKING questions.

### Shared ruler — fixture database, smoke suite, golden data

PHASE0 builds these. Later phases use them and may only extend them, never weaken them. A
change to what they accept goes through the "change the gate" row.

- **Fixture DB** — `{space}/fixture/ccdb_fixture.sqlite`, built by a committed-style script `{space}/tools/make_fixture.py`: run `ccdb.testing.recreate_test_sqlite_db()`, then add the cases the seed list needs:
  - one table with ≥ 3500 assignments across ≥ 5 variations;
  - nested directories at least 6 levels deep, and ≥ 1000 tables in total;
  - a variation hierarchy with at least 3 levels;
  - comments and names containing `<script>`, `"`, `'`, `&`, newlines and non-ASCII text;
  - run ranges that end at `2147483647`;
  - ≥ 2000 log records from at least 3 authors.

  The script is deterministic: a fixed seed and fixed timestamps. Store its sha256 in `{space}/fixture/MANIFEST.md`.
- **Smoke suite** — `{space}/tools/smoke.py`. For every route and a list of edge-case URLs it records the HTTP status, bytes, time, and SQL query count. Count queries with a SQLAlchemy `before_cursor_execute` event listener in the test harness, not in the app. It writes `{space}/reports/smoke_<phase>_<label>.json` and prints a short table.
- **Golden data** — `{space}/tools/golden.py` computes the expected values for each page (table path, columns, row counts, author names, run ranges, variation names, comments) straight from SQL on the fixture DB, independent of the web layer. The data gate compares what the pages show (JSON API responses or parsed HTML) against this golden set.
- **Browser check** — Playwright for Python, run as `uv run --with playwright==1.63.0` (pinned to the installed browser builds) so the repo stays untouched (`playwright install chromium firefox` once; see ENVIRONMENT.md). `{space}/tools/browse.py` opens each page in light and dark mode, saves screenshots to `{space}/plots/phase<N>/`, and records browser console errors and failed network requests. The visual loop runs it in Chromium; phase gates run it in Chromium and Firefox, since Firefox is the default browser on lab Linux desktops.

### PHASE0 — baseline and inventory (no product code changes)

Task: build the shared ruler, measure the current GUI, verify each item in the seed list, and record the library decisions in DECISIONS.md.

- **Step 0**: fixture DB + smoke suite running against the unchanged app at f61eaaf. Record `{space}/reports/smoke_phase0_baseline.json`.
- Then: golden data and the browser check (baseline screenshots, console errors); confirm or refute every seed item and record each one as a finding; size up the tree page (HTML bytes, DOM nodes, render time with ≥ 1000 tables) to confirm D4. Library evaluation is done (`{space}/planning/challenge.md`); copy its decisions into DECISIONS.md.
- Ruler: the fixture DB and the scripts themselves. Before Step 0 is recorded, editing them is normal work.
- Done: `{space}/reports/phase0_baseline.md` with the measured numbers per route, findings F1… in `phase0_findings.md` and FINDINGS.md, and a question sweep. Question seed: write D1–D6 as plain ASKs with the default as the recommendation, and ask whether the run container can reach hallddb.jlab.org read-only for a secondary check.
- Extra rows: a seed item does not reproduce on the fixture → record the finding as RESOLVED or "needs production data" and ASK. Do not bend the fixture to force a reproduction.

### PHASE1 — backend and data correctness

Task: fix every data, backend and security finding (seed items 1–13, 17, and the route name in 19) inside the web layer. A finding whose fix lives in the core library becomes a patch proposal (see Environment). Templates change only where a data fix needs it; the visual redesign is PHASE2.

- **Step 0**: re-run the PHASE0 smoke suite and golden comparison on the unchanged tree; the numbers must match the baseline (time within ±30 %, everything else exact).
- Work items, one checkpoint each:
  1. App configuration (D6): one shared engine per process with `pool_pre_ping=True` and `pool_recycle`, a scoped session per request, the schema check once at startup, no stdout prints (use `logging`).
  2. Provider defects — `get_type_table_by_id` returning the directory, `get_directory_by_id` on a missing id, lazy loads in `get_assignments`: for each, write the failing test and the proposed fix as a core patch under `{space}/notes/core-patches/` and PARK it. Give the web layer what it needs without the core change: the views look up tables and directories by id through `ccdb.model` and answer 404 themselves; the paginated routes (item 4) build their own eager-loading query. Run the full unit and SQLite integration suite after each web-side change.
  3. Error handling: 404 page for missing objects, 400 for bad requests, one error template, no 500 on any edge-case URL in the smoke list.
  4. Paginated table routes: versions, logs and variations take `page`, `per_page`, `sort`, `search` and their filters as GET parameters and run one bounded SQL query per page (eager loading, no N+1). The query parsing lives in one small helper shared by the three routes. Query helpers return plain dataclasses (rows, page info, table metadata); views render them. Templates keep their current look; the fragment response and the live search are PHASE2.
  5. Assignment resolver and views. One helper resolves an assignment from either `?request=<request string>` (the primary form, kept on `show_request` and the data routes) or `/assignments/<int:id>` (the short form). Three views use it: the page (metadata + data), `data.json` (columns and rows), and `data.txt` (the `ccdb dump` text; `download_request` keeps working as the request-string entry point). Both forms must give byte-identical responses for the same assignment. A request string that resolves to several assignments (no timestamp) picks the newest, as the CLI does, and the page shows the exact request string it resolved to. Assignments are append-only in CCDB, so data responses for an exact request or an id may carry long cache headers.
  6. Escaping: remove every `|safe` that wraps database text; render comments with escape + line breaks; the text dump returns `text/plain; charset=utf-8` in the `ccdb dump` format (item 5). Keep `/dowload_request` and `/download_request` as redirects so old links work.
  7. URL prefix support (D5) and author names everywhere.
- Ruler / gate: the unit tests and the SQLite integration tests pass (`python -m unittest` over the `unit_test_*` modules including the new `unit_test_provider_attach`, `unit_test_provider_lookups` and the `unit_test_webgui*` modules, plus `integ_test_cli_manager` and `integ_test_provider_sqlite`; the MySQL module needs a throwaway MySQL server and stays a user-side check — never point it at hallddb, the runner wipes its database); the golden comparison also checks the assignment JSON against SQL through both addressing forms; golden comparison is exact on every page; zero 500 responses on the smoke list; the versions page for the 3500-row table answers in < 1 s locally with a query count that does not grow with the row count; every injection string from the fixture comes back escaped.
- Done: `{space}/reports/phase1_backend.md` with before/after smoke numbers and the question sweep.
- Extra rows: a finding can only be fixed in the core library (no web-side workaround keeps the gate exact) → PARK with the patch saved; the finding stays OPEN, BLOCKING(the item) until the user applies the patch.

### PHASE2 — frontend rebuild

Task: rebuild the base layout and every page on Bootstrap 5.3 with no jQuery. This covers seed items 14–16, 18 and 19, the theme switch, the tree, the tables, and the request form. Every work item below runs through the visual loop, one visible feature at a time; item 1 alone is several passes (navbar, sidebar, footer).

- **Step 0**: PHASE1 gate passes on the current tree; vendor script (D1) fetches Bootstrap 5.3.8 (CSS + JS bundle, the only vendored library) and verifies its sha256 manifest.
- Work items:
  1. `dash_base.html`: navbar with the version from `ccdb.version`, a sidebar with the active page highlighted, a theme switch, a working favicon, one footer link target (ASK which one), and no inline CSS beyond a few lines.
  2. Theme: light, dark and auto with no flash on load. Every page and component (tables, tree, modals, code blocks) is readable in both modes.
  3. Tree page (D4): directory/table tree with a filter box, remembered open state, keyboard access, and info modals that load through `url_for`-built URLs.
  4. Tables (D3): versions, logs and variations as server-rendered pages on the paginated routes. Each route returns only the table fragment (table + pagination) when the request carries `X-Fragment: 1` or `HX-Request: true` (the second name costs nothing and keeps HTMX adoptable later); `static/js/table.js` (about 25 lines) debounces input by 250 ms, fetches the fragment, swaps it, and rewrites the URL with `history.replaceState`. Versions keeps the run-range filter, shows ∞ for the sentinel and links each row by its exact request string. Variations shows the hierarchy. Assignment data in a `table-responsive` block with a sticky header.
  5. Request page: autocomplete over all tables with a native `<datalist>`, variation select, run number and date; the date field documents the accepted format (`YYYY:MM:DD-hh:mm:ss`, partial allowed — see `ccdb.path_utils.parse_time`).
  6. Assignment page (`show_request?request=…`, also reachable as `/assignments/<id>`): metadata card, data table, a copy button for the exact request string, and download links for the text dump and the JSON.
  7. Remove dead templates, routes and assets (item 19). Grep first: something outside webgui may link to them.
- Ruler / gate: PHASE1 gate still passes; `grep -ril jquery {web}` is empty outside `static/vendor/` (Bootstrap's bundle carries an optional jQuery hook); no inline executable `<script>` beyond the two allowed kinds (`<script type="application/json">` data blocks are fine); Playwright reports zero console errors and zero failed requests on every page in both themes, in Chromium and Firefox, apart from the HTTP status of the deliberate 404 edge page in the page list; every page works with the CDN blocked (D1); the page set renders at 1400×900 and 390×844 (phone) without horizontal scroll, judged by browse.py's Firefox 390 px records (Chromium's mobile emulation hides overflow).
- Done: `{space}/reports/phase2_frontend.md` with light and dark screenshots per page next to the PHASE0 baseline, page weights before and after, and the question sweep.
- Extra rows: in this phase the app's own JavaScript is three small modules (`common.js`: theme menu and fetch-into-modal; `tree.js`; `table.js`); a page that needs more, or a new library → PARK with the reason; the lean budget is a user decision for this phase only.

### PHASE3 — production packaging

Task: seed item 20 and deployment documentation.

- **Step 0**: PHASE2 gate passes.
- Work items: CCDB ships no WSGI server — the `web` extra stays Flask only, and the server and the reverse proxy are the deployment's choice (decided 2026-10-13). Dockerfile on a current slim Python image that installs the package with `pip install .[web]` plus the image's own WSGI server (gunicorn as the example), runs as non-root, and has a `HEALTHCHECK` on a `/health` route that pings the database; docker-compose passes `CCDB_CONNECTION`; the server's worker count comes from an env knob in the image; a deployment page in `{repo}/docs/` covering env vars, URL prefix (`CCDB_WEBGUI_PROXY_FIX`), reverse proxy, any WSGI server with gunicorn as the example, a read-only DB user, and logging.
- Ruler / gate: if docker or podman is available, build the image and run the smoke suite against the container with the fixture DB mounted; otherwise PARK the container check and verify the wheel: `uv build`, install it in a clean venv, run gunicorn from it, run the smoke suite.
- Done: `{space}/reports/phase3_packaging.md` and the final question sweep.

### PHASE4 — website fixes

Task: the round of improvements the user asked for on 2026-10-14 after browsing the GUI on hallddb; web layer only. The user is online during this phase: questions go to chat first and are mirrored into `{space}/QUESTIONS.md`.

- **Step 0**: the PHASE3 gate passes on the current tree (HEAD 1f7cb2a): tests, smoke `--check`, golden exact, browser check in both browsers; the numbers match `reports/phase3_packaging.md` and `reports/smoke_phase3_pathlinks.json`. HEAD moved after checkpoint 24, so the checkpoint series restarts at 25.
- Work items, one checkpoint each, every one through the visual loop:
  1. Info boxes. `created` and `modified` of a table or directory record are equal in practice (nothing in CCDB edits the record after creation; 0 of 684 tables and 0 of 64 directories differ on hallddb). The table box replaces Modified with the number of assignments and when the last one was added; the directory box shows the same for the tables under it.
  2. Tree filter. Ancestors of a match stay visible (today a directory whose own path lacks the text hides its matching tables). `*` and `?` wildcards in the filter box, with the CLI's pattern semantics as the precedent (`search_type_tables`: `*` any text, `?` one character, matched against the whole name).
  3. Tree toolbar. Expand all and Collapse all buttons. The filter stops recording every folder it opens as the remembered state.
  4. Compare variations. A page `/vars/compare?variation=<name>&parent=<ancestor>` lists, as a tree, the tables with assignments in the chain segment from the chosen ancestor (exclusive) to the variation (inclusive); the parent select offers the ancestors, the direct parent is the default. Each table shows the assignment count per variation in the segment, linked to its filtered versions page. The variations list gets an eye button per row that opens the page. The tree macro moves to `_tree.html` so both pages render the same markup. The root variation has no parent and gets no comparison: grouping its 689 442 assignments on hallddb takes 8 s. Optional `run` and `time` parameters narrow the assignments considered: the run range must contain the run, the assignment must be created up to the time (Q33).
  5. Assignment data table: a row index column, counted from 0. JSON and text dumps stay byte-identical.
  6. Assignment data layout: `layout=auto|horizontal|vertical` as a GET parameter with a switch on the page; auto is vertical for one row and more than two columns (Q34), horizontal otherwise.
  7. Column types in the data view (added 2026-10-14): under the column name in the horizontal layout, as a column in the vertical layout. The fixture gains a one-row, six-column table with an assignment, so the auto rule is visible in the browser check (allowed extension: regenerate, new hash in MANIFEST.md, previous gate re-run).
- Ruler / gate: the PHASE3 gate. `pages.py` gains the compare page (a chain pair, the root, the empty case `subsubtest`, an unknown variation → 404, a parent outside the chain → 400) and the layout variants of the assignment page; golden gains the affected-table sets from SQL and reads the transposed data table; the page readers follow the markup (row index cell, layout attribute) and the golden values do not change. Smoke bytes of every data URL (JSON, text) equal Step 0.
- Done: `{space}/reports/phase4_fixes.md` with before/after numbers, a screenshot per item, and the question sweep.
- Extra rows: items 1, 2, 4 and 6 start only after their chat question has an answer; items 3 and 5 are routine engineering and start right after Step 0. An answer that changes the shape of an item beyond its description above is a scope change → PARK.

#### PHASE4 round 2 — the user's second message (2026-10-14)

Four more items on top of checkpoint 32-docs; same ruler and protocol, checkpoints continue at 33, and the review unit moves to the last checkpoint of the round. Step 0 of the round: the working tree equals checkpoint 32-docs (tracked diff against the patch, untracked set against the tar), then tests, smoke `--check` and golden re-run with the PHASE4 gate numbers (142 tests, 64 URLs, 196 checks); the browser gate run of the phase stands as the reference.

  8. Answered A on 2026-10-25 and applied in PHASE5 (item 9 there). Data layout names. The page follows `ccdb cat`: Vertical is one line per column, which is tall for one row and wide for many rows, so the names look swapped on many-row tables ("when you press horizontal it looks vertical and vice versa"). Q40 in chat: A) swap the labels, B) name the forms (Auto | Table | Transposed), C) keep the names and define them by shape — Vertical is the form with more lines, Horizontal the wider one, Auto unchanged; recommendation C. Starts after the answer. Whatever is chosen, the attribute the golden reader transposes on keeps naming the physical form, the two address forms stay byte-identical, and a rows > columns case joins the tests.
  9. Tree toolbar: Expand, Collapse, Sort A…Z, Sort by ID. The sort is remembered like the open state (one localStorage key) and applies on both tree pages; folders before tables, A…Z case-insensitive and natural (`layer2` before `layer10`), by ID within each kind. A…Z is the default when nothing is remembered, and the server renders that order (directories and tables by name), so the page without JavaScript, the golden reader and the screenshots agree.
  10. Versions page: a "Show info" button in the header rolls down the table's info block (Bootstrap collapse) — the rows of the tree's info modal, moved to a partial that the modal fragment and the versions page both include. Golden picks the versions table by a marker attribute instead of its position.
  11. Variations page: "Compare variations" becomes a filled primary button, clearly a button in both themes.
  12. Built on 2026-10-25 as PHASE5 item 10 (checkpoint 47-log-record). Log record page (the user's third message, 2026-10-15, with a screenshot of the Logs page on hallddb: the comment column truncates, "we need to create log-record page … where we can see full comment (might be lengthy)"; row click or an eye button, "decide what is better"). `GET /logs/<id>` shows one record: created, action, author, description, the affected object as text (`assignments 812174`; for an assignment of a create or update record a link to `/assignments/<id>`, built without a lookup), the database id and the full comment — comments reach 65 535 characters and 500 lines on hallddb (program output with aligned columns), so the comment is a wrapping monospace block. The list keeps its table; every row opens its record on a click (the Created stamp is the real link, for keyboards, new tabs and pages without JavaScript), because a button at the row end is off-screen on a phone. Unknown id → the 404 page.
- Ruler additions: `notes/checks/tree_behaviour.py` gains the sort cases (remembered across a reload); golden reads the marked versions table and, for item 8, the shape rule if chosen; `pages.py` gains a rows > columns layout page if item 8 needs one; doc page entries for the sort buttons, Show info and the log record. Item 12: the fixture gains one newest log record with a long multi-line comment (appended after everything else, so no other timestamp moves; new hash in MANIFEST.md); `pages.py` gains the record pages (newest, hostile comment, missing id); golden compares the record page with the database row (fields, full comment, affected text and link) and the row links of the list; `notes/checks/log_row_click.py` checks the row click. Gate as PHASE4; smoke bytes of the data URLs equal Step 0.

### PHASE5 — compare assignments

Task: a page that compares the data of two assignments of a table — two calibration passes, the same constants at two times, a variation against its parent — in three views, reached from the versions page, the sidebar and the assignment page. Web layer only: the diff is pure Python over the strings CCDB stores, built on the assignment resolver and the data seam. The user is online during this phase: questions go to chat first and are mirrored into `{space}/QUESTIONS.md`. The decisions D25–D32 below were taken in chat on 2026-10-25 (Q45–Q52). Two questions were dropped by the user without a decision, Q43 (where PHASE4 items 8 and 12 go) and Q44 (the untracked `docs/web-security-audit.md`): decide nothing about them in advance; when one of them stops the run, it is a `BLOCKING(!)` question at that moment.

Starting point: HEAD is 862944a (the security fixes of 2026-10-19 are committed), so checkpoints 25–37 no longer apply and the series restarts at 38. PHASE4 items 8 and 12 are not part of this phase. The compare page shares the `layout` parameter and `assignments.vertical_layout` with the assignment page, so the answer to Q40 applies to both pages at once.

Production bounds (hallddb, read-only, 2026-10-25): the largest constant sets are 175 951 rows × 6 columns, 12.4 MB per blob (`solenoid_*`); 12 of 688 tables exceed 100 000 cells and 20 exceed 10 000. A page that renders two such sets in full is 50 MB; D29 bounds it. The assignment page renders them in full today: record it as a finding, out of scope here.

- **Step 0**: the PHASE4 gate on the current tree: tests, smoke `--check`, golden exact, browser check in both browsers; the numbers match checkpoint 37 in `checkpoints/INDEX.md` (152 tests, smoke 64/0, golden 197/0). `docs/web-security-audit.md` is untracked and not yours: the Git rule applies (a first save the checkpoint script refuses is a STOP with a question).
- Work items, one checkpoint each, items 2–6 through the visual loop:
  1. Diff module `{web}/diff.py`, no Flask import: `diff_tables(a, b)` takes the two sides (columns and rows as `assignments.assignment_dict` returns them) and returns a `TableDiff` dataclass: the columns, one row per row index with `Cell(a, b, changed)` values, the counts (cells, changed cells, rows with a change, columns with a change), and for a changed pair of numbers the difference and the relative change. Every assignment of a table has the table's `rows_count` rows, so the two sides always have the same shape; unequal lengths are bad data and raise `ValueError`, which the view answers with 400. Unit tests in `unit_test_webgui_diff.py`: equal sets, changed cells, numeric and non-numeric pairs, unequal lengths. Fixture, appended after everything else so no earlier timestamp moves: a second assignment of `/calib/ccal/parms` in variation `calib` with two of its six values changed (a request without a timestamp resolves to the newest assignment, so a second `default` assignment would change what the existing `parms` pages show), and a new table `/calib/ccal/channels` with 600 rows × 4 columns and two `default` assignments whose data differ in seven cells spread over several pages of 200 rows, so paging, `changed=1` and the two-times use case have a case to run on. Regenerate, new hash in MANIFEST.md, previous gate re-run.
  2. Route `GET /compare` (endpoint `compare_assignments`, template `compare_assignments.html`, sidebar section `compare`): the form and the resolution of the two sides. `a` and `b` each hold a request string or a database id; a value made of digits only is an id (`parse_request` reads `1234` as a table path, so the view decides before parsing), and both forms go through `assignments.resolve_assignment`. The page labels the sides A and B, as the URL names them; which assignment is A and which is B is the user's choice, and the page never reorders them. Both sides must belong to one table; two tables answer 400 naming both paths. The form sends parts (`table`; per side `variation`, `run`, `time`, or `id`); the view composes the request strings and redirects to the canonical `?a=…&b=…` URL, as `show_request` does with `path`. Table picker: the request page's `<datalist>` over all tables; the variation selects list the table's variations once a table is chosen (`queries.table_variation_names`), all variations otherwise; a changed table reloads the page, as `compare.js` does for the variations page. The page shows the exact request string each side resolved to, with a link to its assignment page. A side that does not resolve: D32.
  3. Per-cell view, `view=cells`, the default: one data table in the assignment page's layouts (`layout=auto|horizontal|vertical`, the same parameter and the same rule). A changed cell carries `data-changed`, the B value above the A value, the difference (B minus A) in its `title`. Above the table: a summary line (`N of M cells changed in K rows`) and the switches for view, layout and `changed=1`, which keeps the rows (vertical: the columns) with a change. A metadata card with one column per side: variation, run range, created, author, comment, request string with a copy button, the data links. Paging and the big-table rule: D29. Color: D28.
  4. Per-column view, `view=columns`: horizontal, each column shows A and B side by side under one header; vertical, one line per column with an A and a B value column per row index. Same marking and summary.
  5. Table-to-table view, `view=tables`: table B above table A, with the row index of both. Same marking (D30).
  6. Entry points: a Compare button in the versions page header (a filled primary button, as Compare variations on the Variations page) that opens the form with the table chosen; a sidebar entry Compare with a sprite icon (`i-compare`, Bootstrap Icons `arrow-left-right`); on the assignment page the two buttons of D31.
  7. `GET /compare/data.json?a=…&b=…` serving the `TableDiff` (D32), the doc page entry, and a read-only hallddb measurement of the largest pair (time and bytes of each view, with and without `changed=1`) for the report.
  8. Added 2026-10-25 (Q53, finding F34: the assignment page renders a 40 000 × 11 table as a 10 MB page): the assignment data table comes in pages of 200 rows like the comparison, every row with its true index; the page links address the assignment by its request string on both address forms; JSON and text dumps stay whole. `pages.py` gains the last page, a smaller page size, a page past the end and a bad page of the 600-row assignment; golden checks their rows and indexes against the vault blob.
  9. Added 2026-10-25 (Q40 A, PHASE4 item 8): the layout words name the shape seen on a many-row table: Vertical is one line per row, Horizontal one line per column, on the assignment page and the compare page; the URL values and the auto rule stay; the markup attribute becomes `data-lines="rows|columns"`, so the golden reader transposes on the physical form and the URL value and the attribute never share a word; `pages.py` gains `show_big_horizontal` and `diff_horizontal`, the one-line-per-column forms of a many-row table; doc entry Data layout.
  10. Added 2026-10-25 (PHASE4 item 12, "decide best for users everywhere"): the log record page `/logs/<id>` as designed in `{space}/notes/design-phase4.md`, opened by a click on a row of the Logs list (the Created stamp is the real link); the fixture gains the newest record with a 60-line comment (new hash in MANIFEST.md); `pages.py` gains the record pages (newest, hostile comment, missing id); golden compares the record page with the database row and the row links of the list with the newest ids; `notes/checks/log_row_click.py` checks the click, the Ctrl-click and a drag selection; doc entry Logs.
  11. Added 2026-10-25 (Q55 A): the record page names the affected objects as users know them and links them to their pages while they exist: a table or directory by path, a variation by name, an assignment by id; a deleted object keeps the record's words. The fixture gains three records naming a table, a variation and a deleted table (new hash); golden checks the links of every record page against the database.
  12. Added 2026-10-26 (the user's message: "pick to compare" button on the versions view, checkboxes, a third pick removes the first, survives pagination): a Pick to compare toggle in the versions header reveals a checkbox per assignment; the first two picks are A and B, a third drops the oldest; the picks and the mode persist in session storage per table across paging, live search and reloads; a bar shows the pair with a Compare link and a Clear button. JavaScript only (`static/js/pick.js`); the header Compare button stays the path without it. The golden reader drops the pick cells; `notes/checks/pick_to_compare.py` checks the flow; doc entry.
  13. Added 2026-10-26 (the user: "in versions list we also need DB ids, probably as the first column"): the versions list shows the database id of every assignment as its first column, sortable; golden checks the ids against SQL.
  14. Added 2026-10-26 (the user: a unified diff download on the compare page, one line per row, headers naming A and B by request string): `GET /compare/data.diff?a=…&b=…` serves the whole comparison in the unified diff format (`diff -u`, `git diff`), the data lines in the `ccdb dump` layout of the text download so the diff of the two downloads and the file agree hunk for hunk, three rows of context, the two header lines naming the resolved request strings with A or B, the id and the creation time after a tab, written even when nothing differs; the hunks are built from the diff module's changed rows (the sides are aligned row by row), not from a sequence match; plain text with a `download` attribute on the page's link (`<table>_<a id>_<b id>.diff`). `pages.py` gains the file by ids, by request strings, the `parms` pair, equal sides and the edges; golden checks the headers, the `-` and `+` lines and the hunks against the vault blobs; `unit_test_webgui_diff` checks the module against `difflib` and the route; doc entry.
- Ruler / gate: the PHASE4 gate. `pages.py` gains the form, a pair by request strings, by ids, mixed, each view, `changed=1`, `layout=vertical`, the same assignment on both sides (zero changes), the `channels` pair on pages 1 and 3 and with `changed=1`, the `parms` pair across `default` and `calib`, and the edges (unknown side, malformed side, two tables, bad `view`, bad `changed`). Golden computes the expected diff of the fixture pairs from the vault blobs by SQL and reads the `data-changed` cells and the summary counts of every view and layout. Smoke bytes of every existing data URL equal Step 0. `unit_test_webgui_diff` joins the module lists of `python-tests.yml` and `mysql-tests.yml`. `notes/checks/compare_assignments_behaviour.py` checks the form script.
- Done: `{space}/reports/phase5_compare.md` with before/after numbers, a screenshot per view in both layouts and both themes, the hallddb measurement, and the question sweep.
- Extra rows: an answer or a finding that changes the shape of an item beyond its description above is a scope change → PARK. The diff module stays free of Flask and of the web layer's dataclasses, so a later `ccdb diff` command can take it over without a rewrite.

Decisions of 2026-10-25 (chat; the question of each is in the first column):

| # | decision | decided |
|---|---|---|
| D25 (Q45) | the two sides | Parameters `a` and `b`, labels A and B everywhere; no Old and New: which assignment is which is the user's choice, and the page never reorders them. In the stacked views B is above A, in the side-by-side view A is left. |
| D26 (Q46) | two different tables | Same table only. Two tables answer 400 naming both paths. |
| D27 (Q47) | equality | A cell is changed when the two strings differ, as CCDB stores them; a changed pair of numbers shows the difference and the relative change in the cell's `title`. |
| D28 (Q48) | color | One state, one color: changed cells use `--ccdb-diff-changed` on `--bs-success-bg-subtle` (green), defined on `:root` and `[data-bs-theme=dark]`. Row counts never differ within a table, so there is no one-sided cell. |
| D29 (Q49) | big tables | Rows are paged with the pagination component (`page`, `per_page` from `PAGE_SIZES`; the default is 200 for this page alone, `DEFAULT_PAGE_SIZE` stays 50); `changed=1` filters before paging. A pair above 20 000 cells opens with `changed=1` unless the URL says `changed=0`. The two blobs are loaded and diffed in full on every request (about one second for the largest pair; measured in item 7); a cache is out of scope. |
| D30 (Q50) | table-to-table marking | Changed cells are marked in this view too; the view differs from per-cell only in showing both values in place. |
| D31 (Q51) | more entry points | The assignment page gets Compare with previous (`b` = this assignment, `a` = the previous one: the same request string with `created` minus one second, so the resolver finds what the request returned before, no new query; request strings have second resolution, so two assignments created in the same second, as scripted uploads do, are one to the resolver: the button then points one step further back, to what came before both) and Compare with… (opens the form with `a` filled). No row checkboxes on the versions list, no diff links on the Compare variations page. |
| D32 (Q52) | a failing side, JSON | A side that does not resolve re-renders the form with an inline alert on that side, status 404 (400 when malformed), instead of the error page; `pages.py` lists these as edges. `GET /compare/data.json` serves the diff; no text form. |

## Common rules

### Environment

- You are running in a docker container in autonomous mode.
- {space} holds all your notes, memory and records.
- YOU ARE NOT ALLOWED TO DO ANY CHANGES IN GIT: no commits, no pushes, no branch, stash or index changes. Reading, `git diff`, `git log`, `git show` and restoring your own edited files with `git checkout -- <path>` are allowed. See Git for checkpoints.
- **The core library is read-only.** Never edit `{repo}/python/ccdb/` outside `webgui/` — `provider.py`, `model.py`, `path_utils.py`, the CLI — nor the existing tests. The provider is shared with the `ccdb` CLI and with users' scripts. When a change there seems needed: write the failing test and the proposed diff to `{space}/notes/core-patches/<NN-slug>.patch` (test + fix + reproducer), then **PARK** with a `BLOCKING(!)` question that explains the change, its effect on other callers, and the web-side workaround if one exists; freeze the item that needs it and continue with independent work. The user applies core patches. Web code may run its own read-only SQLAlchemy queries on `ccdb.model` classes where the provider has no fitting method; that is normal work and is not a core change.
- **Never write to a database other than the fixture DB.** If `CCDB_CONNECTION` points to a real server (hallddb or any MySQL), use it read-only through the web GUI and the smoke suite. Never run a `ccdb` CLI command that modifies data against it.
- Permissions:
  - Do not access the host system.
  - Use **uv** for Python, and add packages with uv — choose libraries yourself (do NOT use typer; plain argparse is fine).
  - If you need system packages (browsers for Playwright, fonts, …), install them and record what must be installed for future runs in {space}/notes/ENVIRONMENT.md.
- Check the core count (`nproc`) and use it for parallel jobs, keeping ~2 cores headroom. Timing measurements in the smoke suite run with nothing else beside them.

### How you work

- On start: read {space}/STATUS.md if it exists, then process {space}/QUESTIONS.md as the FIX / ASK / PARK / STOP section describes — both before any other action. Then resume from where the last run stopped instead of restarting. If QUESTIONS.md does not exist yet, there are no questions — continue.
- When you create code, make it easy for humans to use and maintain: anywhere someone starts reading, the context is quickly clear.
- When you have enough information to act, act. Do not re-litigate decisions already made. If weighing a choice, pick one and record the recommendation. This never overrides FIX / ASK / PARK / STOP: a doubt it routes to a question stays a question.
- You are operating autonomously; the user cannot answer questions mid-run. For reversible actions that follow from this file, proceed. When anything unexpected happens — or you catch yourself about to assume something the user could have specified — use the FIX / ASK / PARK / STOP protocol. Never pursue a doubtful assumption silently.
- Write every question into {space}/QUESTIONS.md the moment it occurs to you. That file is your only channel to the user, and it carries every kind of question — the ones that block you and the ones that do not.

#### Visual loop — one feature at a time

Any change a user can see — layout, template, CSS, JS behavior, theme — goes through this loop, one feature per pass. A feature is one work item or one visible part of it: the navbar, the theme switch, the tree filter, the pagination bar.

1. Implement the one feature. Do not start the next one.
2. Run `{space}/tools/browse.py` in Chromium on the pages the feature touches: light and dark, 1400×900 and 390×844. Screenshots go to `{space}/plots/phase<N>/<feature>/`; the script prints console errors and failed requests.
3. Look at those screenshots and the printed counts, then decide: it looks right → save a checkpoint and start the next feature; it does not → fix it and rerun step 2. After two fix attempts the feature goes to the tool-error row of the decision table (PARK, with the screenshot path in the question).

Never stack two visual features before step 2 has run for the first. The phase gate at the end repeats the check over every page; the loop keeps that final check from finding ten defects at once.

#### Memory: where each kind of knowledge lives

Your context is lost at every restart and compaction. Everything you need later goes to disk the moment you learn it, and each fact has one home. Writing the same fact in two places means one of them goes stale.

| kind of knowledge | home | rule |
|---|---|---|
| resume state | `{space}/STATUS.md` | ≤ 40 lines, enforced. First line: the active phase. Then a `## LIVE` block, then the top block (what just finished, where to continue, pointers). No history: move finished-run lines to the phase report. |
| running things | `## LIVE` block in STATUS.md | one line per background server, detached job, monitor or temp resource (PID, port, log path, started when). Update it the moment something starts or ends — never at run end. After a crash the next run reads it and cleans up. |
| measured numbers | `{space}/reports/` | the phase report and smoke JSONs are the only home of a number. STATUS.md and notes point to them; they do not repeat them. |
| decisions | `{space}/notes/DECISIONS.md` | every assumption as a config-like entry with the evidence and the numbers behind it, so it is cheap to change later. Decisions are not recorded in prose elsewhere. |
| defects | `FINDINGS.md` + phase ledgers | see Findings below. |
| questions and answers | `{space}/QUESTIONS.md` | see FIX / ASK / PARK / STOP. |
| traps and lessons | `{space}/notes/lesson-<slug>.md` | one trap per file: what bit, why, the rule that avoids it. Write it the same day it bites — a trap seen but not written is the costliest kind. Update rather than duplicate; delete notes that turn out wrong. |
| user corrections | `{space}/notes/feedback-<slug>.md` | when an answer in QUESTIONS.md corrects you or sets a preference that generalizes beyond one item, write it: the trigger (quote the answer), why, how to apply. Before every phase report, sweep the answers of this phase for such corrections. |
| environment facts | `{space}/notes/ENVIRONMENT.md` | packages, browsers, system installs future runs need. |
| the index | `{space}/notes/README.md` | one line per note and report: identity, pointer, as-of date. Never results in the hook — hooks that carry numbers rot within days. Add the line in the same step that creates the file. |

- Before any open-ended search, state in your notes what you expect to find and why. If you can't, put it in the report as "recommended next step" instead of doing it.
- Put screenshots and plots in {space}/plots/phase{#}/ and write results up in {space}/reports/phase{#}_.... Previous results, plots and knowledge must persist as you progress.
- Token thrift: you run on a limited LLM budget, so be economical with your own effort — compute is cheap, tokens are expensive:
  - Never load raw data or full HTML pages into your context. Write scripts that print small samples, stats, and summaries; read those instead.
  - Redirect ALL server, test and browser-run stdout/stderr to log files; inspect them only via tail/grep.
  - Run servers and long jobs detached (nohup, background) and poll their logs; never block a tool call on a long run. Loop over routes, pages and themes INSIDE scripts, never one tool call per point.
  - Prefer one well-prepared run over many small iterations.
  - Validate from printed numbers (status codes, counts, bytes, ms, query counts, console-error counts). Look at screenshots when the visual loop asks for them — the pages one feature touched — and otherwise at most once per page per milestone.
  - Do not re-read files you just wrote; re-read only the region you are editing.
  - Milestone-first: finish and record each phase's Step 0 before any other work. A finished verified milestone is worth more than three half-finished ones.
  - Assume you can be interrupted at any moment (rate limits): keep scripts, notes, and partial results on disk at all times so a future run resumes rather than restarts; update STATUS.md and its LIVE block as you go.

### When something unexpected happens — FIX, ASK, PARK, or STOP

- The user reads {space}/QUESTIONS.md between runs and answers inline.
- The user might say explicitly that they are online and can answer interactively.
- If the user gives no such command, that file is your only channel to the user, so it carries every question you have: what blocks you, what you would ask if the user sat beside you, and what they should decide before the next phase.
- Questions are a deliverable of this job!
- A parked question costs a paragraph and you keep working; a stop costs a run; a wrong assumption silently pursued can invalidate a whole phase. A run that ends with clear questions and a clean frozen ledger is a successful run.

Four responses cover everything:

- **FIX** — resolve it inside this run, no question. FIX applies only when the resolution is verified in this run: the tests pass, the gate passes, the counts match. A fix that rests on an unverified interpretation is not a FIX — the interpretation is itself the question: PARK it.
- **ASK** — write a plain question, freeze nothing, keep working.
- **PARK** — write a `BLOCKING(!)` question, freeze its subject, keep working on something independent.
- **STOP** — write a `BLOCKING(!)` question, freeze everything, update STATUS.md, end the run.

A question is **BLOCKING(!)** when its answer could invalidate or redirect work this run would otherwise do. When the answer affects only future runs or the user's own decisions, it is a plain ASK: write it and keep working. Between ASK and PARK, weigh what a wrong guess costs — if it costs work already done, PARK.

The decision table routes what goes wrong. ASK also covers what the table never sees: a preference the user could have stated, a question for the CCDB maintainers, a scope doubt about work you are not doing, a finding that deserves a verdict. Routine engineering choices (naming, code structure, library picks within the criteria above) are yours — never ask those.

**Absolute STOPs, regardless of the table below:** an action would write to a database other than the fixture DB; an action would destroy something you cannot regenerate (the user's uncommitted changes in {repo} that are not yours, a recorded reference, the findings ledger — overwriting your own build trees, outputs and caches is routine and never triggers this); something would cost real money; the task is impossible as specified; or proceeding would require breaking a correctness rule of the phase (its gate, its frozen fixture, its golden data). Proposing a change to a rule is not breaking it — that is a PARK.

#### Decision table — check top to bottom, first match wins

The phase section defines this run's **ruler**: its Step 0 reference, its gate, and its frozen items. Rows below refer to those.

| you observe | response |
|---|---|
| two defensible readings of the task lead to different work or a different result the user sees, and you are about to pick one | **PARK** the choice, with your intended reading as the recommendation. Routine engineering choices (naming, code structure, library picks within the criteria) are yours — never park those. |
| the phase's gate fails on your change | **FIX**: re-run the gate with your change reverted (restore the last checkpoint). Reverted code passes → revert, record REJECTED in STATUS.md. Reverted code also fails → the ruler is broken: two rows down. Never adjust the gate, the golden data, or the fixture to make your change pass — wanting to is the next row. |
| you want to change what the gate accepts, the fixture DB, the golden data, or the definition of "correct" (after the phase's Step 0 established it) | **PARK** the proposal with evidence; do NOT apply it. Continue only work that does not touch the disputed definition; if none exists, **STOP**. Mechanical repairs of a checking script that change no verdict (a crash fix) are the tool-error row — after fixing, prove verdicts unchanged by re-running it on the last recorded checkpoint. Before Step 0 establishes the ruler, editing the checking scripts is normal Step 0 work. Extending the fixture with new cases while keeping the old ones is allowed: regenerate, update MANIFEST.md, re-run the previous phase's gate, and record it in STATUS.md. |
| the fixture DB is MISSING but `make_fixture.py` and MANIFEST.md exist | **FIX**: regenerate with the script, verify the sha256 against MANIFEST.md, record the regeneration in STATUS.md. A fixture that is PRESENT but hash-mismatching — or a regenerated one that still mismatches — is a broken ruler: **STOP** with a question; never regenerate over it. |
| the phase's Step 0 numbers no longer reproduce | during Step 0: **FIX** — debug the setup. After Step 0 is recorded: one clean rerun (fresh venv, server restarted) with no code changes to rule out a stale environment; if the mismatch persists, **STOP** — the ruler is broken and nothing checked after this is valid. |
| a test error, tool error, or crash | **FIX**: debug it. Count attempts per blocked task, not per error message: if the task is still blocked after two distinct fix attempts, restore the last checkpoint, then — evidence points at code you don't own → next row; the error sits in the check path itself (smoke, golden, browser harness) → **STOP** (a broken ruler is not parkable); otherwise **PARK** this one item (question: drop it, or is there context I'm missing?). |
| a bug in the CCDB core (`ccdb.provider`, `ccdb.model`, `ccdb.path_utils`, CLI) | this is an EXPECTED finding, not an emergency. Record it in the phase's findings ledger with a minimal reproducer and severity, and add its line to {space}/reports/FINDINGS.md. No phase edits the core (see Environment): if the GUI depends on the bug, write the test and the proposed patch under `{space}/notes/core-patches/` and **PARK**; a web-side workaround that keeps the gate exact is an option in the question. A core bug the GUI does not depend on is recorded only. |
| a bug in code you don't own and can't change (a vendored JS library, Flask, SQLAlchemy, a browser, the container) | write the question first; a minimal reproducer is good "continuing meanwhile" work. It blocks — or could skew — the ruler → **STOP**; it blocks one work item → **PARK** that item; nothing of yours is blocked → **ASK** and continue. |
| a discovery that would change the SCOPE — the goal, the decisions already made, or the phase plan | **PARK**: write the finding and the proposed re-scope. Run no work on it. The written plan stays the plan until the user changes it. |
| the phase's done criterion is met | normal completion: write the phase report, then sweep for questions — reread your notes, findings ledger and DECISIONS.md and **ASK** everything the user should decide or know before the next phase starts. Sweep the answered questions of this phase for corrections that generalize and write each as a `notes/feedback-<slug>.md`; update `notes/README.md`. Reconcile {space}/reports/FINDINGS.md against every phase<N>_findings.md ledger before you write that report: every finding indexed, every status current, the counts line true. Save the final checkpoint (see Git). Set the first line of STATUS.md to `PHASE<N> DONE — report at <path>` and end the run. Finishing with an empty QUESTIONS.md is a defect, not a clean run. |

If no row matches: **PARK**. If no row matches and the doubt is about whether your checks are valid — you cannot tell whether the ruler is right — **STOP**.

#### ASK — the exact protocol

Append to {space}/QUESTIONS.md (N = highest Q number in the file + 1):

```markdown
## Q<N> <date> — <one-line question>
- Found: <what prompted it; measured numbers where they exist, otherwise the exact error text verbatim>
- Why it matters: <what could change depending on the answer>
- Options: A) <...> B) <...>. Recommendation: <letter + one line why>
- ANSWER:
```

A plain entry freezes nothing. Keep working — including on its subject, following your recommendation. It needs no STATUS.md line; the entry is the record. Options must span the plausible answers: your recommendation AND the strongest alternative.

#### PARK — the exact protocol

1. Append to {space}/QUESTIONS.md, `BLOCKING(!)` opening the question line (N = highest Q number in the file + 1):

   ```markdown
   ## Q<N> <date> — BLOCKING(!) <one-line question>
   - Found: <what happened; measured numbers where they exist, otherwise the exact error text verbatim>
   - Why it matters: <what could change depending on the answer>
   - Options: A) <...> B) <...>. Recommendation: <letter + one line why>
   - Frozen until answered: <concrete items or file paths>
   - Continuing meanwhile: <the item you switch to + one line why it touches nothing frozen>
   - ANSWER:
   ```

   Options must span the plausible answers: your recommendation AND the strongest alternative. A question that freezes nothing is an ASK, not a PARK — write it in the plain format.
2. The freeze names concrete items and lasts the whole run: before starting ANY work item, check it against the Frozen lists of ALL open BLOCKING(!) questions — allowed only if it touches none of the named items. Your Recommendation is not an answer: frozen work stays frozen regardless of your confidence.
3. Restore the working tree to the last checkpoint before switching. If the in-progress diff is evidence for the question, save it under {space}/notes/ first and reference it from the entry.
4. Switch to the next work item that passes the freeze check in step 2. If none exists, STOP.
5. Add one line to STATUS.md: `Q<N> parked; continuing with <item>`.

#### STOP — the exact protocol

For question-driven stops: write the BLOCKING(!) question in the PARK format (Frozen: everything; Continuing: nothing), update STATUS.md so the next run resumes from the answer, end the run. Normal completion writes the phase report and its ASK sweep instead. Stopping with a written question is a good outcome.

#### Processing QUESTIONS.md on run start

The set of active freezes is exactly the `Frozen until answered:` lines of `BLOCKING(!)` entries without `[closed]` in their header — nothing else. Plain entries never freeze anything. For each entry:

- ANSWER filled and decisive → apply it, append `[closed <date>]` to the header; for a BLOCKING(!) entry also rewrite its Frozen line to `Frozen: none [unfrozen <date>]`.
- ANSWER filled but conditional or unclear → do NOT unfreeze. Append a follow-up question quoting the answer verbatim; do only its unconditional part.
- ANSWER empty on a plain entry → it stays open and blocks nothing. Do not re-litigate it and do not ask it again; append new evidence to the entry if you find any.
- ANSWER empty on a BLOCKING(!) entry → the freeze stands; do not re-litigate (appending new evidence to the entry is allowed).
- A BLOCKING(!) entry without `[closed]` says `Frozen: everything` and ANSWER is empty → this run can do nothing: append `still waiting on Q<N>` to STATUS.md and end the run. Do not work around the freeze or reinterpret the question.

### Findings — the global index

Defects are the second thing this program produces for the user, after the code. They accumulate across phases, so they get one entry point that never moves: **{space}/reports/FINDINGS.md**, the index of every finding any phase has ever recorded.

Each finding lives in two places, and both are written in the same work step:

- the **full entry** — reproducer (URL or test), root cause, evidence, severity — in the discovering phase's ledger, {space}/reports/phase<N>_findings.md. That file is the log: append-only, never renumbered, never rewritten when a later phase changes the verdict (append a Status line instead).
- **one line** in FINDINGS.md, status first.

Rules for the index:

- **Numbers are global and permanent.** F<N> continues across phases: if PHASE0 writes F1—F25, PHASE1 continues at F26. A new finding takes the next free number in FINDINGS.md; numbers are never reused, never renumbered, and never reordered.
- **Status first, so the file is readable in one pass.** The vocabulary is fixed:

  | status | meaning |
  |---|---|
  | FIXED | fix in the working tree, its test or gate check passes, checkpoint saved |
  | RESOLVED | investigation found no defect; the behavior is pinned by a test or smoke check |
  | WON'T FIX | recorded reason; needs a user or upstream decision |
  | OPEN | recorded and unfixed; the ledger pins today's behavior |

  Append `, BLOCKING(<what it blocks>)` to the status of any finding that stands in the way of named future work — `OPEN, BLOCKING(PHASE2 tree page)`. This marker routes attention: before starting the work it names, confirm the finding or raise the question it points to. It is not the question protocol's freeze — only a `BLOCKING(!)` question freezes anything.
- **Columns**: status, number, one-line title, component (core / webgui-backend / webgui-frontend / packaging), and the checkpoint name that fixed it or the question number that owns it.
- **The status in the index is the status.** A verdict recorded only in a phase ledger is a verdict nobody finds. Change one, change both, in the same work step.
- **Keep the counts line at the bottom true** — totals per status, and which OPEN findings block what. It is the first thing a reader reads and the easiest thing to leave stale. The same goes for the F-range in the title.
- A core finding becomes FIXED only after the user applies its patch and the full suite passes on the result; until then it is OPEN with the question number that owns it. Any phase sets FIXED for webgui and packaging findings within its own task.

### How you document

Applies to user-facing documents, texts and code+comments. For yourself you write how it is better for your recall and understanding.

- Act as a technical writer following the Google Developer Documentation Style Guide.
- Strip every sentence to its cleanest components: remove every word that does not contribute to the meaning.
- Eliminate clutter: avoid redundancies ("completely finished" → "finished").
- Remove hedge words that weaken prose: very, little, pretty, rather, actually.
- Avoid jargon: use simple, direct language a general reader understands without a dictionary (established domain terms are fine).
- Never the rhetorical "X, not Y" construction ("fast, not correct" prose); state X and let the reader infer not-Y. A negation that is itself the instruction ("output must not differ") is fine.
- No slang and no editorializing epithets (nominal, finally, honest, clever).
- Use the em dash (—) for any dash in text, ranges included.
- Eliminate excessive claims. Never use words that assume the user's skill level or the task's difficulty. Avoid words such as: simply, just, easily, easy, obvious, obviously, straightforward, trivial, painless, and basically.
- Eliminate ambiguous pronouns. Never use first person plural pronouns (we, us, our).
- Use direct address and imperative mood. Speak directly to the reader as "you" or give direct commands. Example: "Run the script" instead of "We will run the script".
- State the goal before the action. Example: "To start the server, run the command" instead of "Run the command to start the server".
- Omit unnecessary politeness. Do not use "please" or "kindly".
- Be objective and literal: describe what the software does.
- Don't write code history, sentiments about code changes or prompt details in text. Any written text exists for a new human reader to understand the context in the minimal time.
- History or details may still exist if they help prevent a bug or warn of risky places. E.g. "Trying to optimize X will involve Y and will probably fail because of Z".
- Never leave pieces of prompt context and prompt jargon in comments. BAD: "As said in ccdb-webgui.md ...", "seed item 5", "PHASE1".
- A comment earns its place by saying something the code can't: the rationale, the constraint, the non-obvious consequence. BAD: "// loop over rows".
- Lead a non-trivial block with a short intent line, then the mechanism. Name the trap or the gotcha explicitly.

### How you code

- You write for humans, so a human maintainer feels comfortable reading (minimal cognitive load) and editing the code.
- Match the surrounding style when editing CCDB files: `ccdb.provider` and `ccdb.model` have their own naming and layout — new code inside them follows the file it lives in, not your defaults.
- Python: support the versions in pyproject.toml (`requires-python >= 3.9`); no new runtime dependency for the core package. Web-only dependencies go in the `web` extra.
- JavaScript: native ES modules, no build step (D2), no globals beyond what a vendored library defines. One module per page or feature in `static/js/`, plus a shared `static/js/common.js` for theme and fetch helpers. A new vendored library (for example a plot library in a later program) goes through D1 like Bootstrap.
- Templates: one base layout, blocks for title, page header, content and page scripts. No CSS in `style=""` attributes beyond one-off layout tweaks; shared styles go in `static/css/ccdb.css` built on Bootstrap CSS variables so both themes work. Any color the app adds (tree lines, badges, future plot series) is a CSS variable on `:root` and `[data-bs-theme=dark]`, so scripts can read it with `getComputedStyle`.
- You don't follow 80-character line cut-offs. If it is easier to read in one long line — do it. If a function definition reads better with each argument on its own line — use it. Decide from a human reader's point of view.
- Don't use short obscure variable names like `ac3` or `bumdbx`, but also don't make them unnecessarily long like `my_variable_to_hold_data`. Keep balance.
- Any place in the code must satisfy: if a new reader reads only this place, the variable names and comments let them understand the context and what is going on.
- A lot of import nesting is bad. Import B from A which is imported from C from D makes humans follow the whole chain and open all files. One very long file with everything is bad too. Decide on balance — the current single 316-line `webgui/__init__.py` may split into app setup, page views and API views.
- For a single loop `i` is OK; for nested loops indexes must help understand the context: `row_i, col_i` for tables. Decide on balance.

### Git

Never commit, push, branch, stash, rebase or change the index. Never rewrite history. Never touch a branch.

Your progress lives in the working tree of {repo} plus **checkpoints** in {space}/checkpoints/:

- In PHASE0 Step 0, write `{space}/tools/checkpoint.sh` with two commands:
  - `save <NN-name>` stores `git diff --binary HEAD` plus a tar of untracked, non-ignored files (`git ls-files --others --exclude-standard`) as `{space}/checkpoints/<NN-name>.{patch,tgz}`, and appends a line with the name, the time and the gate result to `{space}/checkpoints/INDEX.md`.
  - `restore <NN-name>` returns the working tree to exactly that state: it restores tracked files with `git checkout -- .`, removes only the untracked files listed in the newest checkpoint tar, then applies the named patch and tar.
- Save a checkpoint after every finished work item whose gate checks pass. "Restore the last checkpoint" in this file means `checkpoint.sh restore` with the newest INDEX.md entry.
- Before the first save, check `git status`: if {repo} has changes that are not yours, **STOP** and ask — never mix them into a checkpoint or discard them.
- At the end of each phase, the newest checkpoint patch is what the user reviews and commits.
