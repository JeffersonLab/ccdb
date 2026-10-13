# CCDB web GUI — production plan and common rules

To start a run, the user gives you one line: `Read /work/ccdb-webgui.md first. Run PHASE<N>.`
This file holds the whole program: the goal, the phase plan with each
phase's task, ruler and done criterion, then the environment, the work
protocol, the FIX / ASK / PARK / STOP protocol, and the documentation,
coding and git rules.

## Paths

| name | path | what lives there |
|---|---|---|
| {repo} | /work/ccdb | CCDB repository checkout, branch `v2-main` |
| {web} | {repo}/python/ccdb/webgui | Flask app (`__init__.py`), `templates/`, `static/` |
| {space} | /work/space-ccdb-webgui | your notes, reports, plots, screenshots, patches |

## Goal

Make the CCDB web GUI ready for production: correct data on every page, current libraries, a
consistent visual style with a light/dark theme switch, and a deployable package. The GUI is
read-only. It serves two uses, and both must keep working:

1. Local: `ccdb gui [-p PORT]` — the CLI starts Flask with the CLI connection string.
2. Server: gunicorn serves `ccdbweb:app` ({repo}/python/ccdbweb.py) behind a reverse proxy, from a Docker image ({repo}/docker/webgui/Dockerfile).

## Decisions already made by the user

Do not re-litigate these.

- Remove jQuery completely: no jQuery, no jQuery UI, no jQuery plugins.
- Drop DataTables. It depends on jQuery and its Bootstrap 4 styling clashes with Bootstrap 5. Reimplement every table with a modern library.
- Bootstrap 5.3 (latest 5.3.x) is the only CSS framework. Remove the local Bootstrap 4.2.1 files, Material Design Lite, Font Awesome and Feather icons. Use Bootstrap Icons.
- Replace the hand-made jQuery tree with a modern tree. Bootstrap has no tree component. Choose between native `<details>/<summary>` styled with Bootstrap plus a small vanilla script, or a vanilla tree library such as Wunderbaum.
- Add a light/dark theme switch: light, dark and auto (follows the OS). It uses Bootstrap `data-bs-theme`, persists in `localStorage`, and the page must not flash the wrong theme on load.
- Keep JavaScript out of Jinja templates. Put it in `static/js/*.js` ES modules. Pass server data through `data-*` attributes or `<script type="application/json">` blocks. Two inline scripts are allowed: the theme bootstrap in `<head>` (it must run before first paint) and a short module call that starts a page. A few lines inline beat an extra file when a page needs only a few lines.

## Defaults for open decisions

Follow the default. Each item is already an ASK in the Step 0 question seed (see PHASE0).

| # | decision | default |
|---|---|---|
| D1 | asset delivery | Vendor pinned dist files into `{web}/static/vendor/<lib>-<version>/`, fetched by a committed script that checks a sha256 manifest. The wheel already ships `static/`. A server on the lab network then runs with no CDN access. |
| D2 | JS build step | None: no Node, no npm, no bundler. Native ES modules plus vendored dist files. Maintainers then need only Python. |
| D3 | table library | Tabulator 6.x: vanilla JS, has a Bootstrap 5 theme, renders thousands of rows through a virtual DOM, and supports server-side pagination, sorting and filtering. Before you adopt it, verify that the theme follows `data-bs-theme=dark`; if it does not, write a CSS override or pick another library and record why. |
| D4 | tree | Native `<details>/<summary>` with a vanilla filter box and open-state memory, unless Step 0 numbers show the page is too heavy (current tree page: 188 KB HTML). Then use Wunderbaum with lazy loading. |
| D5 | URL prefix | The app works under a sub-path (for example `/ccdb/`). Build every URL with `url_for`, also the URLs JavaScript uses. Enable `ProxyFix` through a config knob. |
| D6 | connection config | `CCDB_CONNECTION` first, then `SQL_CONNECTION_STRING` for the existing docker-compose. Neither set → fail at startup with a clear message. No default credentials in code. |

## Known problems (seed list — verify each in PHASE0)

Observed on 2026-10-13 against `mysql://ccdb_user@hallddb.jlab.org/ccdb` with commit f61eaaf.

Data and backend:

1. The table info modal shows the parent directory: `AlchemyProvider.get_type_table_by_id` (provider.py) returns `parent_dir` instead of the table. `/get-table-info/1` showed "Table name: test_vars, DB ID 3".
2. Authors: the table modal renders `table.author`, but `TypeTable` has no `author` relationship, so the field is blank. The directory modal shows the numeric `author_id`. `show_request` and `download_request` look up the author with hand-written queries, although `Assignment.author` exists.
3. Missing objects return 500 instead of 404: `/get-dir-info/999999` (KeyError in `get_directory_by_id`), `/get-table-info/999999` (NoResultFound), `/show_request?request=/FCAL/gains:1:nosuchvar` (template reads `None.constant_set`), and `/dowload_request` with no `request` (the view returns None).
4. An unknown table in `/show_request` returns 200 with the plain-text body "Something is not found in the DB".
5. Slow versions page: `/versions/FCAL/gains` renders 3484 rows (1.6 MB) in 24 s. Suspected cause: lazy loads of `run_range` and `variation` for each row (N+1 queries over the WAN), plus all rows rendered server-side.
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

20. Dockerfile: `python:3.10-slim`, unpinned requirements, unused Bokeh, root user, no health check, and it does not install the `ccdb` package. The `web` extra in pyproject.toml lacks gunicorn.

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
- **Browser check** — Playwright for Python (`uv add --dev playwright`, `playwright install firefox chromium`). `{space}/tools/browse.py` opens each page in light and dark mode, saves screenshots to `{space}/plots/phase<N>/`, and records browser console errors and failed network requests.

### PHASE0 — baseline and inventory (no product code changes)

Task: build the shared ruler, measure the current GUI, verify each item in the seed list, and evaluate libraries for D3 and D4.

- **Step 0**: fixture DB + smoke suite running against the unchanged app at f61eaaf. Record `{space}/reports/smoke_phase0_baseline.json`.
- Then: golden data and the browser check (baseline screenshots, console errors); confirm or refute every seed item and record each one as a finding; size up the tree page (HTML bytes, DOM nodes, render time with ≥ 1000 tables); evaluate table and tree libraries against these criteria — no jQuery, Bootstrap 5.3 dark-mode compatible, maintained (a release within the last 12 months), license, gzip size, server-side pagination. Record the picks with evidence in DECISIONS.md.
- Ruler: the fixture DB and the scripts themselves. Before Step 0 is recorded, editing them is normal work.
- Done: `{space}/reports/phase0_baseline.md` with the measured numbers per route, findings F1… in `phase0_findings.md` and FINDINGS.md, library picks, and a question sweep. Question seed: write D1–D6 as plain ASKs with the default as the recommendation, and ask whether the run container can reach hallddb.jlab.org read-only for a secondary check.
- Extra rows: a seed item does not reproduce on the fixture → record the finding as RESOLVED or "needs production data" and ASK. Do not bend the fixture to force a reproduction.

### PHASE1 — backend and data correctness

Task: fix every data, backend and security finding (seed items 1–13, 17, and the route name in 19). Templates change only where a data fix needs it; the visual redesign is PHASE2.

- **Step 0**: re-run the PHASE0 smoke suite and golden comparison on the unchanged tree; the numbers must match the baseline (time within ±30 %, everything else exact).
- Work items, one checkpoint each:
  1. App configuration (D6): one shared engine per process with `pool_pre_ping=True` and `pool_recycle`, a scoped session per request, the schema check once at startup, no stdout prints (use `logging`).
  2. Provider fixes — test-first: write a failing unit test in `{repo}/python/tests/`, then fix. This covers `get_type_table_by_id`, `get_directory_by_id` on a missing id, and eager loading in `get_assignments` (`contains_eager` for the joins it already makes). Run the full unit and SQLite integration suite after each fix.
  3. Error handling: 404 page for missing objects, 400 for bad requests, one error template, no 500 on any edge-case URL in the smoke list.
  4. JSON endpoints for large tables: `/api/...` with server-side pagination, sorting and filtering for versions, logs and variations. Keep HTML routes for first paint.
  5. Escaping: remove every `|safe` that wraps database text; render comments with escape + line breaks; `download_request` returns `text/plain; charset=utf-8` in the `ccdb dump` format. Keep `/dowload_request` as a redirect to `/download_request` so old links work.
  6. URL prefix support (D5) and author names everywhere.
- Ruler / gate: the full unit and integration suite passes; golden comparison is exact on every page; zero 500 responses on the smoke list; the versions page for the 3500-row table answers in < 1 s locally with a query count that does not grow with the row count; every injection string from the fixture comes back escaped.
- Done: `{space}/reports/phase1_backend.md` with before/after smoke numbers and the question sweep.
- Extra rows: fixing a provider bug changes behavior that the CLI or other callers depend on (a test outside webgui fails) → PARK with the diff saved. The provider is shared with the `ccdb` CLI and with users' scripts.

### PHASE2 — frontend rebuild

Task: rebuild the base layout and every page on Bootstrap 5.3 with no jQuery. This covers seed items 14–16, 18 and 19, the theme switch, the tree, the tables, and the request form.

- **Step 0**: PHASE1 gate passes on the current tree; vendor script (D1) fetches the pinned libraries and verifies their sha256 manifest.
- Work items:
  1. `dash_base.html`: navbar with the version from `ccdb.version`, a sidebar with the active page highlighted, a theme switch, a working favicon, one footer link target (ASK which one), and no inline CSS beyond a few lines.
  2. Theme: light, dark and auto with no flash on load. Every page and every library (tables, tree, modals, code blocks) is readable in both modes.
  3. Tree page (D4): directory/table tree with a filter box, remembered open state, keyboard access, and info modals that load through `url_for`-built URLs.
  4. Tables (D3): versions, logs and variations on the JSON endpoints with server-side pagination. Versions keeps the run-range filter and shows ∞ for the sentinel. Variations shows the hierarchy.
  5. Request page: autocomplete over all tables (native `<datalist>` or the table library's search), variation select, run number and date; the date field documents the accepted format (`YYYY:MM:DD-hh:mm:ss`, partial allowed — see `ccdb.path_utils.parse_time`).
  6. Show-request page: metadata card, data table, a copy button for the request string, and a download link.
  7. Remove dead templates, routes and assets (item 19). Grep first: something outside webgui may link to them.
- Ruler / gate: PHASE1 gate still passes; `grep -ril jquery {web}` is empty; no inline `<script>` beyond the two allowed kinds; Playwright reports zero console errors and zero failed requests on every page in both themes; every page works with the CDN blocked (D1); the page set renders at 1400×900 and 390×844 (phone) without horizontal scroll.
- Done: `{space}/reports/phase2_frontend.md` with light and dark screenshots per page next to the PHASE0 baseline, page weights before and after, and the question sweep.
- Extra rows: a library fails the dark-mode or no-jQuery criterion during integration → FIX with the runner-up from DECISIONS.md if the switch is verified in this run; otherwise PARK that page.

### PHASE3 — production packaging

Task: seed item 20 and deployment documentation.

- **Step 0**: PHASE2 gate passes.
- Work items: the `web` extra gains `gunicorn`; Dockerfile on a current slim Python image that installs the package with `pip install .[web]`, runs as non-root, and has a `HEALTHCHECK` on a `/health` route that pings the database; docker-compose passes `CCDB_CONNECTION`; a gunicorn config file with workers taken from an env knob; a deployment page in `{repo}/docs/` covering env vars, URL prefix, reverse proxy, a read-only DB user, and logging.
- Ruler / gate: if docker or podman is available, build the image and run the smoke suite against the container with the fixture DB mounted; otherwise PARK the container check and verify the wheel: `uv build`, install it in a clean venv, run gunicorn from it, run the smoke suite.
- Done: `{space}/reports/phase3_packaging.md` and the final question sweep.

## Common rules

### Environment

- You are running in a docker container in autonomous mode.
- {space} holds all your notes, memory and records.
- YOU ARE NOT ALLOWED TO DO ANY CHANGES IN GIT: no commits, no pushes, no branch, stash or index changes. Reading, `git diff`, `git log`, `git show` and restoring your own edited files with `git checkout -- <path>` are allowed. See Git for checkpoints.
- **Never write to a database other than the fixture DB.** If `CCDB_CONNECTION` points to a real server (hallddb or any MySQL), use it read-only through the web GUI and the smoke suite. Never run a `ccdb` CLI command that modifies data against it.
- Permissions:
  - Do not access the host system.
  - Use **uv** for Python, and add packages with uv — choose libraries yourself (do NOT use typer; plain argparse is fine).
  - If you need system packages (browsers for Playwright, fonts, …), install them and record what must be installed for future runs in {space}/notes/ENVIRONMENT.md.
- Check the core count (`nproc`) and use it for parallel jobs, keeping ~2 cores headroom. Timing measurements in the smoke suite run with nothing else beside them.

### How you work

- On start: read {space}/STATUS.md if it exists, then process {space}/QUESTIONS.md as the FIX / ASK / PARK / STOP section describes — both before any other action. Then resume from where the last run stopped instead of restarting. Keep STATUS.md under ~40 lines; it is the resume entrypoint. Its first line names the active phase. If QUESTIONS.md does not exist yet, there are no questions — continue.
- When you create code, make it easy for humans to use and maintain: anywhere someone starts reading, the context is quickly clear.
- When you have enough information to act, act. Do not re-litigate decisions already made. If weighing a choice, pick one and record the recommendation. This never overrides FIX / ASK / PARK / STOP: a doubt it routes to a question stays a question.
- Store one lesson per file in {space}/notes/ with a one-line summary at the top; update rather than duplicate; delete notes that turn out wrong.
- Put screenshots and plots in {space}/plots/phase{#}/ and write results up in {space}/reports/phase{#}_.... Previous results, plots and knowledge must persist as you progress.
- Record any new assumption as a config knob in {space}/notes/DECISIONS.md so it is cheap to change later. Tie decisions to evidence and measured numbers.
- You are operating autonomously; the user cannot answer questions mid-run. For reversible actions that follow from this file, proceed. When anything unexpected happens — or you catch yourself about to assume something the user could have specified — use the FIX / ASK / PARK / STOP protocol. Never pursue a doubtful assumption silently.
- Write every question into {space}/QUESTIONS.md the moment it occurs to you. That file is your only channel to the user, and it carries every kind of question — the ones that block you and the ones that do not.
- Token thrift: you run on a limited LLM budget, so be economical with your own effort — compute is cheap, tokens are expensive:
  - Never load raw data or full HTML pages into your context. Write scripts that print small samples, stats, and summaries; read those instead.
  - Redirect ALL server, test and browser-run stdout/stderr to log files; inspect them only via tail/grep.
  - Run servers and long jobs detached (nohup, background) and poll their logs; never block a tool call on a long run. Loop over routes, pages and themes INSIDE scripts, never one tool call per point.
  - Prefer one well-prepared run over many small iterations.
  - Validate from printed numbers (status codes, counts, bytes, ms, query counts, console-error counts); look at a screenshot at most once per page per milestone.
  - Do not re-read files you just wrote; re-read only the region you are editing.
  - Milestone-first: finish and record each phase's Step 0 before any other work. A finished verified milestone is worth more than three half-finished ones.
  - Before any open-ended search, state in your notes what you expect to find and why. If you can't, put it in the report as "recommended next step" instead of doing it.
  - Assume you can be interrupted at any moment (rate limits): keep scripts, notes, and partial results on disk at all times so a future run resumes rather than restarts; update STATUS.md as you go.

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
| a bug in the CCDB core (`ccdb.provider`, `ccdb.model`, `ccdb.path_utils`, CLI) | this is an EXPECTED finding, not an emergency. Record it in the phase's findings ledger with a minimal reproducer and severity, and add its line to {space}/reports/FINDINGS.md. Who may repair it is phase-bound: **PHASE1 fixes core bugs the web GUI depends on**, test-first (failing test, fix, full suite green). PHASE0 records and never fixes; PHASE2 and PHASE3 record and ASK. A core bug the GUI does not depend on is recorded only. |
| a bug in code you don't own and can't change (a vendored JS library, Flask, SQLAlchemy, a browser, the container) | write the question first; a minimal reproducer is good "continuing meanwhile" work. It blocks — or could skew — the ruler → **STOP**; it blocks one work item → **PARK** that item; nothing of yours is blocked → **ASK** and continue. |
| a discovery that would change the SCOPE — the goal, the decisions already made, or the phase plan | **PARK**: write the finding and the proposed re-scope. Run no work on it. The written plan stays the plan until the user changes it. |
| the phase's done criterion is met | normal completion: write the phase report, then sweep for questions — reread your notes, findings ledger and DECISIONS.md and **ASK** everything the user should decide or know before the next phase starts. Reconcile {space}/reports/FINDINGS.md against every phase<N>_findings.md ledger before you write that report: every finding indexed, every status current, the counts line true. Save the final checkpoint (see Git). Set the first line of STATUS.md to `PHASE<N> DONE — report at <path>` and end the run. Finishing with an empty QUESTIONS.md is a defect, not a clean run. |

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
- Only PHASE1 sets a core finding to FIXED. Any phase sets FIXED for webgui and packaging findings within its own task.

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
- JavaScript: native ES modules, no build step (D2), no globals beyond what a vendored library defines. One module per page or feature in `static/js/`, plus a shared `static/js/common.js` for theme and fetch helpers.
- Templates: one base layout, blocks for title, page header, content and page scripts. No CSS in `style=""` attributes beyond one-off layout tweaks; shared styles go in `static/css/ccdb.css` built on Bootstrap CSS variables so both themes work.
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
