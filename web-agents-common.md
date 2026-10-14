# CCDB web GUI — common rules for agent runs

To start a run, the user gives you one line: `Read {repo}/web-agents-common.md and {repo}/<program>.md first. Run PHASE<N>.`

This file holds what every program on the web GUI shares: the paths, the standing rules of the
GUI, the shared ruler (the check scripts in `{repo}/scripts/webgui/`), the shape of a phase, the
work protocol, the FIX / ASK / PARK / STOP protocol, and the documentation, coding and git rules.
The program plan `{repo}/<program>.md` holds what belongs to one program only: its goal, the
decisions already made, the defaults for open decisions, the known problems and the phases.
`ccdb-webgui.md` is the plan of the first program, the production modernization of 2026-10, and
the model for the next one.

## Paths

| name | path | what lives there |
|---|---|---|
| {repo} | the CCDB checkout; the program plan gives the absolute path and the branch | |
| {web} | {repo}/python/ccdb/webgui | Flask app (`__init__.py`, `db.py`, `views.py`, `queries.py`, `assignments.py`, `errors.py`), `templates/`, `static/` |
| {scripts} | {repo}/scripts/webgui | the check scripts: fixture, smoke, golden, browser check, checkpoints; see its README.md |
| {space} | {repo}/space-<program> | your notes, reports, plots, screenshots, patches, checkpoints; outside version control (`.gitignore` lists `space-*/`) |

## The program plan

Write a program plan with these sections, in this order. Everything else comes from this file,
and the plan does not repeat it.

1. **Paths** — the values of `{repo}` and `{space}` for this run.
2. **Goal** — what the program delivers and what must keep working.
3. **Decisions already made by the user** — not to be re-litigated.
4. **Defaults for open decisions** — a numbered table (D1, D2, …). Each row is an ASK in the Step 0 question seed, with the default as the recommendation.
5. **Known problems** — the numbered seed list, verified in PHASE0.
6. **Phase plan** — PHASE0 is the baseline (see Phases); each later phase has a task, a Step 0, work items, a ruler (gate), a done criterion and its extra decision-table rows.

A plan may tighten a rule of this file for one program, for example a smaller JavaScript budget
or a stricter gate. It may not loosen one.

## Standing rules of the web GUI

Decisions already made for the GUI as a whole. A program builds on them; changing one is a user
decision and belongs in the program plan.

- The GUI is read-only. Two ways to run it must keep working: `ccdb gui [-p PORT]`, where the CLI starts Flask with its own connection string, and a WSGI server on `ccdbweb:app` (`{repo}/python/ccdbweb.py`) behind a reverse proxy. CCDB ships no WSGI server: the `web` extra is Flask only, and the deployment picks the server; the Docker image in `{repo}/docker/webgui/` uses gunicorn. Deployment is documented in `{repo}/docs/deployment/webgui.md`.
- Configuration comes from `CCDB_CONNECTION`, the variable the `ccdb` command reads, and from nothing else. No default credentials in code; a missing connection string fails at startup with a clear message. `CCDB_WEBGUI_PROXY_FIX=1` enables `ProxyFix` behind a reverse proxy under a sub-path. Every URL, also the ones JavaScript uses, is built with `url_for`.
- One SQLAlchemy engine per process (`pool_pre_ping`, `pool_recycle`), a scoped session per request, the schema check once at engine creation, `logging` instead of prints. The provider is bound to that engine with `AlchemyProvider.attach`.
- Bootstrap 5.3.x is the only CSS framework, vendored into `static/vendor/` by `python -m ccdb.webgui.vendor` against a sha256 manifest: no CDN at runtime. No jQuery, no DataTables, no icon font; icons are an inline SVG sprite copied from Bootstrap Icons. Own CSS stays under 200 lines in `static/css/ccdb.css`, built on Bootstrap CSS variables; any color the app adds is a CSS variable on `:root` and `[data-bs-theme=dark]`, so scripts can read it with `getComputedStyle`. Keep markup shallow: the move to Bootstrap 6 must stay a rename pass.
- No JavaScript build step: native ES modules in `static/js/`, one module per page or feature plus `common.js` for theme and fetch helpers, no globals beyond what a vendored library defines. JavaScript stays out of Jinja templates; server data goes through `data-*` attributes or `<script type="application/json">` blocks. Two inline scripts are allowed: the theme bootstrap in `<head>`, which must run before first paint, and a short module call that starts a page. A new vendored library goes through the vendor script like Bootstrap.
- Theme: light, dark and auto (follows the OS) through `data-bs-theme`, persisted in `localStorage`, with no flash of the wrong theme on load. Every component is readable in both modes.
- Layout: a top navbar with brand, version and theme menu; a left sidebar (`offcanvas-md`) that becomes a drawer behind a hamburger button on phones; one base layout with blocks for title, page header, content and page scripts. Every page renders at 1400×900 and 390×844 without horizontal scroll.
- Tree: native `<details>/<summary>` with a filter box and the open state remembered in `localStorage`. Info popups load HTML into a Bootstrap modal through `fetch`.
- Tables (versions, logs, variations, assignment data) are server-rendered pages. Page, sort, search and filters are GET parameters; every view has a shareable URL and works without JavaScript; one bounded SQL query per page, no N+1. A route returns only its table fragment when the request carries `X-Fragment: 1` or `HX-Request: true`, and `table.js` uses that for live search. The open-ended run sentinel `2147483647` renders as ∞.
- Data seam: query helpers return plain data (dataclasses or dicts) and templates only render it, so a JSON view of the same data is one `jsonify` call. Plot and comparison pages build on this seam.
- Assignment addressing: the CCDB request string (`/FCAL/gains:30000:default:2017-11-16_10-03-20`) is the primary identifier on every view and in every link shown to users. The database id (`/assignments/<id>`) is a second form for short links and tooling. One resolver serves both forms, and both give byte-identical responses. Assignment data is served as the page, as JSON and as the `ccdb dump` text.
- Escaping: no `|safe` around database text; every string from the database is rendered escaped.
- The core library, `{repo}/python/ccdb/` outside `webgui/`, is read-only for you; see Environment.

## Shared ruler — fixture database, smoke suite, golden data, browser check

The scripts in `{scripts}` are the ruler of every phase; `{scripts}/README.md` has the exact
commands. CI runs them on every push. A program may only extend them, never weaken them; a
change to what they accept goes through the "change the gate" row of the decision table.

- **Fixture DB** — `{space}/fixture/ccdb_fixture.sqlite`, built by `{scripts}/make_fixture.py --space {space} --verify`: the standard test content plus a 3600-assignment table over 6 variations, a 7-level directory chain, 1000 bulk tables, hostile names and comments (`<script>`, quotes, `&`, newlines, non-ASCII text), run ranges that end at `2147483647`, a 4-level variation chain and 2400 log records from three authors. Fixed seed and timestamps: every build hashes the same. Record the sha256 in `{space}/fixture/MANIFEST.md` at Step 0 of PHASE0. The hash depends on the SQLite library version, so a mismatch after a Python upgrade means a rebuild with `--verify` and a new recorded hash, not a changed fixture.
- **Smoke suite** — `{scripts}/smoke.py`: status, bytes, time and SQL query count for every URL in `pages.py`, edge cases included. `--check` fails on any server error and on a status outside what the URL's kind allows. `--base-url` runs it against a live server (gunicorn, a container) for a byte-level comparison with the in-process app.
- **Golden data** — `{scripts}/golden.py compute` derives what every page must show straight from SQL on the fixture, independent of the web layer; `compare` parses the pages, reports every mismatch and exits with 1 on a failure. When templates change, update the page readers; the golden values do not change.
- **Browser check** — `{scripts}/browse.py` with Playwright: every page in light and dark, 1400×900 and 390×844, a screenshot per visit, console errors, failed requests, page weight and horizontal overflow. `--check` fails on any of them. The visual loop runs it in Chromium; phase gates run it with `--browser all`, since Firefox is the default browser on lab Linux desktops. Playwright is not a project dependency: run `uv run --project {repo} --with playwright==<version> python {scripts}/browse.py …`, pinned to the installed browser builds; `{space}/notes/ENVIRONMENT.md` records the version and the install command.
- **Tests** — `python -m unittest` in `{repo}/python` over every `unit_test_*` module plus `integ_test_cli_manager` and `integ_test_provider_sqlite`, with `CCDB_TEST_SQLITE_CONNECTION` pointing at a scratch file. Never point it at the fixture and never at a real server: the runner recreates the database it is pointed at. The MySQL module needs a throwaway MySQL server and stays a CI or user-side check.
- **Checkpoints** — `{scripts}/checkpoint.sh`; see Git.

The gate of a phase is what its plan section names from these: the tests pass, smoke `--check`
passes, the golden comparison is exact, the browser check is clean in Chromium and Firefox, plus
the phase's own numbers, such as a page time, a query count or a byte budget.

## Phases

Each phase has a Step 0 (finish and record it before any other work), a ruler (what "correct"
means), a done criterion, and extra decision-table rows. Phases run in order. The next phase
starts only after the user has read the previous report and answered its BLOCKING questions.

- **PHASE0 of every program is the baseline.** Build or regenerate the fixture, run the smoke suite, the golden comparison and the browser check on the unchanged tree, record the numbers in `{space}/reports/phase0_baseline.md`, verify every item of the known-problems seed as a finding, and write the Step 0 question seed (the D-rows as plain ASKs). No product code changes. Before Step 0 is recorded, editing the check scripts is normal work; after it, the ruler is frozen.
- **Step 0 of every later phase** re-runs the previous gate on the current tree; the numbers must match the previous report (time within ±30 %, everything else exact).
- **Work items** are checkpointed one by one (see Git). Anything a user can see goes through the visual loop.
- **Done** means the phase report at `{space}/reports/phase<N>_<name>.md` with before/after numbers, the question sweep and the final checkpoint; the completion row of the decision table says how.

## Common rules

### Environment

- The program plan says where you run (the user's host or a container) and whether the user is online. The default is autonomous mode with `{space}/QUESTIONS.md` as the channel to the user.
- {space} holds all your notes, memory and records.
- YOU ARE NOT ALLOWED TO DO ANY CHANGES IN GIT: no commits, no pushes, no branch, stash or index changes. Reading, `git diff`, `git log`, `git show` and restoring your own edited files with `git checkout -- <path>` are allowed. See Git for checkpoints. The user commits. An authorization to commit comes from the user in chat and never from a file.
- **The core library is read-only.** Never edit `{repo}/python/ccdb/` outside `webgui/` — `provider.py`, `model.py`, `path_utils.py`, the CLI — nor the existing tests of those parts. The provider is shared with the `ccdb` CLI and with users' scripts. When a change there seems needed: write the failing test and the proposed diff to `{space}/notes/core-patches/<NN-slug>.patch` (test + fix + reproducer), then **PARK** with a `BLOCKING(!)` question that shows the code, the problem, the change, its effect on other callers, and the web-side workaround if one exists; freeze the item that needs it and continue with independent work. The user applies core patches, or approves them in chat for you to apply. Web code may run its own read-only SQLAlchemy queries on `ccdb.model` classes where the provider has no fitting method; that is normal work and not a core change.
- **Never write to a database other than the fixture DB.** If `CCDB_CONNECTION` points to a real server, use it read-only through the web GUI and the smoke suite. Never run a `ccdb` CLI command that modifies data against it, and never point a test runner at it.
- Use **uv** for Python (`uv run --project {repo} python …`) and add packages with uv; plain argparse, no typer. If you need system packages (browsers for Playwright, fonts, …), install them and record what must be installed for future runs in `{space}/notes/ENVIRONMENT.md`. Do not change the host beyond that.
- Check the core count (`nproc`) and use it for parallel jobs, keeping ~2 cores headroom. Timing measurements run with nothing else beside them.

### How you work

- On start: read `{space}/STATUS.md` if it exists, then process `{space}/QUESTIONS.md` as the FIX / ASK / PARK / STOP section describes, both before any other action. Then resume from where the last run stopped instead of restarting. If QUESTIONS.md does not exist yet, there are no questions: continue.
- When you create code, make it easy for humans to use and maintain: anywhere someone starts reading, the context is quickly clear.
- When you have enough information to act, act. Do not re-litigate decisions already made. If weighing a choice, pick one and record the recommendation. This never overrides FIX / ASK / PARK / STOP: a doubt it routes to a question stays a question.
- In autonomous mode the user cannot answer questions mid-run. For reversible actions that follow from this file and the plan, proceed. When anything unexpected happens, or you catch yourself about to assume something the user could have specified, use the FIX / ASK / PARK / STOP protocol. Never pursue a doubtful assumption silently.
- Write every question into `{space}/QUESTIONS.md` the moment it occurs to you. It carries every kind of question: the ones that block you and the ones that do not. When the user is online, ask in chat as well, and mirror the question and the answer into the file.

#### Visual loop — one feature at a time

Any change a user can see — layout, template, CSS, JS behavior, theme — goes through this loop, one feature per pass. A feature is one work item or one visible part of it: the navbar, the theme switch, the tree filter, the pagination bar.

1. Implement the one feature. Do not start the next one.
2. Run `{scripts}/browse.py --space {space} --phase <N> --feature <feature> --pages <labels>` in Chromium on the pages the feature touches: light and dark, 1400×900 and 390×844. Screenshots go to `{space}/plots/phase<N>/<feature>/`; the script prints console errors and failed requests.
3. Look at those screenshots and the printed counts, then decide: it looks right → save a checkpoint and start the next feature; it does not → fix it and rerun step 2. After two fix attempts the feature goes to the tool-error row of the decision table (PARK, with the screenshot path in the question).

Never stack two visual features before step 2 has run for the first. The phase gate at the end repeats the check over every page in both browsers; the loop keeps that final check from finding ten defects at once.

#### Memory: where each kind of knowledge lives

Your context is lost at every restart and compaction. Everything you need later goes to disk the moment you learn it, and each fact has one home. Writing the same fact in two places means one of them goes stale.

| kind of knowledge | home | rule |
|---|---|---|
| resume state | `{space}/STATUS.md` | ≤ 40 lines, enforced. First line: the active phase. Then a `## LIVE` block, then the top block (what just finished, where to continue, pointers). No history: move finished-run lines to the phase report. |
| running things | `## LIVE` block in STATUS.md | one line per background server, detached job, monitor or temp resource (PID, port, log path, started when). Update it the moment something starts or ends, never at run end. After a crash the next run reads it and cleans up. |
| measured numbers | `{space}/reports/` | the phase report and the JSON reports are the only home of a number. STATUS.md and notes point to them; they do not repeat them. |
| decisions | `{space}/notes/DECISIONS.md` | every assumption as a config-like entry with the evidence and the numbers behind it, so it is cheap to change later. Decisions are not recorded in prose elsewhere. |
| defects | `FINDINGS.md` + phase ledgers | see Findings below. |
| questions and answers | `{space}/QUESTIONS.md` | see FIX / ASK / PARK / STOP. |
| traps and lessons | `{space}/notes/lesson-<slug>.md` | one trap per file: what bit, why, the rule that avoids it. Write it the same day it bites; a trap seen but not written is the costliest kind. Update rather than duplicate; delete notes that turn out wrong. |
| user corrections | `{space}/notes/feedback-<slug>.md` | when an answer corrects you or sets a preference that generalizes beyond one item, write it: the trigger (quote the answer), why, how to apply. Before every phase report, sweep the answers of this phase for such corrections. |
| environment facts | `{space}/notes/ENVIRONMENT.md` | packages, browsers, system installs future runs need. |
| the index | `{space}/notes/README.md` | one line per note and report: identity, pointer, as-of date. Never results in the hook; hooks that carry numbers rot within days. Add the line in the same step that creates the file. |

- Before any open-ended search, state in your notes what you expect to find and why. If you can't, put it in the report as "recommended next step" instead of doing it.
- Put screenshots and plots in `{space}/plots/phase<N>/` and write results up in `{space}/reports/phase<N>_<name>.md`. Previous results, plots and knowledge persist as you progress.
- Token thrift: you run on a limited LLM budget, so be economical with your own effort; compute is cheap, tokens are expensive.
  - Never load raw data or full HTML pages into your context. Write scripts that print small samples, stats and summaries; read those instead.
  - Redirect ALL server, test and browser-run stdout/stderr to log files; inspect them only via tail or grep.
  - Run servers and long jobs detached (nohup, background) and poll their logs; never block a tool call on a long run. Loop over routes, pages and themes INSIDE scripts, never one tool call per point.
  - Prefer one well-prepared run over many small iterations.
  - Validate from printed numbers (status codes, counts, bytes, ms, query counts, console-error counts). Look at screenshots when the visual loop asks for them, the pages one feature touched, and otherwise at most once per page per milestone.
  - Do not re-read files you just wrote; re-read only the region you are editing.
  - Milestone-first: finish and record each phase's Step 0 before any other work. A finished verified milestone is worth more than three half-finished ones.
  - Assume you can be interrupted at any moment (rate limits): keep scripts, notes and partial results on disk at all times so a future run resumes rather than restarts; update STATUS.md and its LIVE block as you go.

### When something unexpected happens — FIX, ASK, PARK, or STOP

- The user reads `{space}/QUESTIONS.md` between runs and answers inline.
- The user might say explicitly that they are online and can answer interactively.
- If the user gives no such command, that file is your only channel to the user, so it carries every question you have: what blocks you, what you would ask if the user sat beside you, and what they should decide before the next phase.
- Questions are a deliverable of this job.
- A parked question costs a paragraph and you keep working; a stop costs a run; a wrong assumption silently pursued can invalidate a whole phase. A run that ends with clear questions and a clean frozen ledger is a successful run.

Four responses cover everything:

- **FIX** — resolve it inside this run, no question. FIX applies only when the resolution is verified in this run: the tests pass, the gate passes, the counts match. A fix that rests on an unverified interpretation is not a FIX; the interpretation is itself the question: PARK it.
- **ASK** — write a plain question, freeze nothing, keep working.
- **PARK** — write a `BLOCKING(!)` question, freeze its subject, keep working on something independent.
- **STOP** — write a `BLOCKING(!)` question, freeze everything, update STATUS.md, end the run.

A question is **BLOCKING(!)** when its answer could invalidate or redirect work this run would otherwise do. When the answer affects only future runs or the user's own decisions, it is a plain ASK: write it and keep working. Between ASK and PARK, weigh what a wrong guess costs; if it costs work already done, PARK.

The decision table routes what goes wrong. ASK also covers what the table never sees: a preference the user could have stated, a question for the CCDB maintainers, a scope doubt about work you are not doing, a finding that deserves a verdict. Routine engineering choices (naming, code structure, library picks within the rules above) are yours; never ask those.

**Absolute STOPs, regardless of the table below:** an action would write to a database other than the fixture DB; an action would destroy something you cannot regenerate (the user's uncommitted changes in {repo} that are not yours, a recorded reference, the findings ledger; overwriting your own build trees, outputs and caches is routine and never triggers this); something would cost real money; the task is impossible as specified; or proceeding would require breaking a correctness rule of the phase (its gate, its frozen fixture, its golden data). Proposing a change to a rule is not breaking it; that is a PARK.

#### Decision table — check top to bottom, first match wins

The phase section of the program plan defines this run's **ruler**: its Step 0 reference, its gate, and its frozen items. Rows below refer to those.

| you observe | response |
|---|---|
| two defensible readings of the task lead to different work or a different result the user sees, and you are about to pick one | **PARK** the choice, with your intended reading as the recommendation. Routine engineering choices (naming, code structure, library picks within the rules) are yours; never park those. |
| the phase's gate fails on your change | **FIX**: re-run the gate with your change reverted (restore the last checkpoint). Reverted code passes → revert, record REJECTED in STATUS.md. Reverted code also fails → the ruler is broken: two rows down. Never adjust the gate, the golden data, or the fixture to make your change pass; wanting to is the next row. |
| you want to change what the gate accepts, the fixture DB, the golden data, or the definition of "correct" (after the phase's Step 0 established it) | **PARK** the proposal with evidence; do NOT apply it. Continue only work that does not touch the disputed definition; if none exists, **STOP**. Mechanical repairs of a checking script that change no verdict (a crash fix) are the tool-error row; after fixing, prove verdicts unchanged by re-running it on the last recorded checkpoint. Before Step 0 establishes the ruler, editing the checking scripts is normal Step 0 work. Extending the fixture with new cases while keeping the old ones is allowed: regenerate, update MANIFEST.md, re-run the previous phase's gate, and record it in STATUS.md. |
| the fixture DB is MISSING but `make_fixture.py` and MANIFEST.md exist | **FIX**: regenerate with the script, verify the sha256 against MANIFEST.md, record the regeneration in STATUS.md. A fixture that is PRESENT but hash-mismatching, or a regenerated one that still mismatches, is a broken ruler: **STOP** with a question; never regenerate over it. |
| the phase's Step 0 numbers no longer reproduce | during Step 0: **FIX**, debug the setup. After Step 0 is recorded: one clean rerun (fresh venv, server restarted) with no code changes to rule out a stale environment; if the mismatch persists, **STOP**: the ruler is broken and nothing checked after this is valid. |
| a test error, tool error, or crash | **FIX**: debug it. Count attempts per blocked task, not per error message: if the task is still blocked after two distinct fix attempts, restore the last checkpoint, then: evidence points at code you don't own → next row; the error sits in the check path itself (smoke, golden, browser harness) → **STOP** (a broken ruler is not parkable); otherwise **PARK** this one item (question: drop it, or is there context I'm missing?). |
| a bug in the CCDB core (`ccdb.provider`, `ccdb.model`, `ccdb.path_utils`, CLI) | this is an EXPECTED finding, not an emergency. Record it in the phase's findings ledger with a minimal reproducer and severity, and add its line to `{space}/reports/FINDINGS.md`. No phase edits the core (see Environment): if the GUI depends on the bug, write the test and the proposed patch under `{space}/notes/core-patches/` and **PARK**; a web-side workaround that keeps the gate exact is an option in the question. A core bug the GUI does not depend on is recorded only. |
| a bug in code you don't own and can't change (a vendored JS library, Flask, SQLAlchemy, a browser, the container) | write the question first; a minimal reproducer is good "continuing meanwhile" work. It blocks, or could skew, the ruler → **STOP**; it blocks one work item → **PARK** that item; nothing of yours is blocked → **ASK** and continue. |
| a discovery that would change the SCOPE: the goal, the decisions already made, or the phase plan | **PARK**: write the finding and the proposed re-scope. Run no work on it. The written plan stays the plan until the user changes it. |
| the phase's done criterion is met | normal completion: write the phase report, then sweep for questions: reread your notes, the findings ledger and DECISIONS.md and **ASK** everything the user should decide or know before the next phase starts. Sweep the answered questions of this phase for corrections that generalize and write each as a `notes/feedback-<slug>.md`; update `notes/README.md`. Reconcile `{space}/reports/FINDINGS.md` against every `phase<N>_findings.md` ledger before you write that report: every finding indexed, every status current, the counts line true. Save the final checkpoint (see Git). Set the first line of STATUS.md to `PHASE<N> DONE — report at <path>` and end the run. Finishing with an empty QUESTIONS.md is a defect, not a clean run. |

If no row matches: **PARK**. If no row matches and the doubt is about whether your checks are valid, that is, you cannot tell whether the ruler is right: **STOP**.

#### ASK — the exact protocol

Append to `{space}/QUESTIONS.md` (N = highest Q number in the file + 1):

```markdown
## Q<N> <date> — <one-line question>
- Found: <what prompted it; measured numbers where they exist, otherwise the exact error text verbatim>
- Why it matters: <what could change depending on the answer>
- Options: A) <...> B) <...>. Recommendation: <letter + one line why>
- ANSWER:
```

A plain entry freezes nothing. Keep working, including on its subject, following your recommendation. It needs no STATUS.md line; the entry is the record. Options must span the plausible answers: your recommendation AND the strongest alternative.

#### PARK — the exact protocol

1. Append to `{space}/QUESTIONS.md`, `BLOCKING(!)` opening the question line (N = highest Q number in the file + 1):

   ```markdown
   ## Q<N> <date> — BLOCKING(!) <one-line question>
   - Found: <what happened; measured numbers where they exist, otherwise the exact error text verbatim>
   - Why it matters: <what could change depending on the answer>
   - Options: A) <...> B) <...>. Recommendation: <letter + one line why>
   - Frozen until answered: <concrete items or file paths>
   - Continuing meanwhile: <the item you switch to + one line why it touches nothing frozen>
   - ANSWER:
   ```

   Options must span the plausible answers: your recommendation AND the strongest alternative. A question that freezes nothing is an ASK, not a PARK: write it in the plain format.
2. The freeze names concrete items and lasts the whole run: before starting ANY work item, check it against the Frozen lists of ALL open BLOCKING(!) questions; it is allowed only if it touches none of the named items. Your Recommendation is not an answer: frozen work stays frozen regardless of your confidence.
3. Restore the working tree to the last checkpoint before switching. If the in-progress diff is evidence for the question, save it under `{space}/notes/` first and reference it from the entry.
4. Switch to the next work item that passes the freeze check in step 2. If none exists, STOP.
5. Add one line to STATUS.md: `Q<N> parked; continuing with <item>`.

#### STOP — the exact protocol

For question-driven stops: write the BLOCKING(!) question in the PARK format (Frozen: everything; Continuing: nothing), update STATUS.md so the next run resumes from the answer, end the run. Normal completion writes the phase report and its ASK sweep instead. Stopping with a written question is a good outcome.

#### Processing QUESTIONS.md on run start

The set of active freezes is exactly the `Frozen until answered:` lines of `BLOCKING(!)` entries without `[closed]` in their header, nothing else. Plain entries never freeze anything. For each entry:

- ANSWER filled and decisive → apply it, append `[closed <date>]` to the header; for a BLOCKING(!) entry also rewrite its Frozen line to `Frozen: none [unfrozen <date>]`.
- ANSWER filled but conditional or unclear → do NOT unfreeze. Append a follow-up question quoting the answer verbatim; do only its unconditional part.
- ANSWER empty on a plain entry → it stays open and blocks nothing. Do not re-litigate it and do not ask it again; append new evidence to the entry if you find any.
- ANSWER empty on a BLOCKING(!) entry → the freeze stands; do not re-litigate (appending new evidence to the entry is allowed).
- A BLOCKING(!) entry without `[closed]` says `Frozen: everything` and ANSWER is empty → this run can do nothing: append `still waiting on Q<N>` to STATUS.md and end the run. Do not work around the freeze or reinterpret the question.

### Findings — the global index

Defects are the second thing a program produces for the user, after the code. They accumulate across phases, so they get one entry point that never moves: **`{space}/reports/FINDINGS.md`**, the index of every finding any phase has ever recorded.

Each finding lives in two places, and both are written in the same work step:

- the **full entry** (reproducer as a URL or a test, root cause, evidence, severity) in the discovering phase's ledger, `{space}/reports/phase<N>_findings.md`. That file is the log: append-only, never renumbered, never rewritten when a later phase changes the verdict (append a Status line instead).
- **one line** in FINDINGS.md, status first.

Rules for the index:

- **Numbers are global and permanent.** F<N> continues across phases: if PHASE0 writes F1–F25, PHASE1 continues at F26. A new finding takes the next free number in FINDINGS.md; numbers are never reused, never renumbered, and never reordered.
- **Status first, so the file is readable in one pass.** The vocabulary is fixed:

  | status | meaning |
  |---|---|
  | FIXED | fix in the working tree, its test or gate check passes, checkpoint saved |
  | RESOLVED | investigation found no defect; the behavior is pinned by a test or smoke check |
  | WON'T FIX | recorded reason; needs a user or upstream decision |
  | OPEN | recorded and unfixed; the ledger pins today's behavior |

  Append `, BLOCKING(<what it blocks>)` to the status of any finding that stands in the way of named future work, for example `OPEN, BLOCKING(tree page)`. This marker routes attention: before starting the work it names, confirm the finding or raise the question it points to. It is not the question protocol's freeze; only a `BLOCKING(!)` question freezes anything.
- **Columns**: status, number, one-line title, component (core / webgui-backend / webgui-frontend / packaging), and the checkpoint name that fixed it or the question number that owns it.
- **The status in the index is the status.** A verdict recorded only in a phase ledger is a verdict nobody finds. Change one, change both, in the same work step.
- **Keep the counts line at the bottom true**: totals per status, and which OPEN findings block what. It is the first thing a reader reads and the easiest thing to leave stale. The same goes for the F-range in the title.
- A core finding becomes FIXED only after the user applies its patch and the full suite passes on the result; until then it is OPEN with the question number that owns it. Any phase sets FIXED for webgui and packaging findings within its own task.

### How you document

Applies to user-facing documents, texts and code with its comments. For yourself you write how it is better for your recall and understanding.

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
- Never leave pieces of prompt context and prompt jargon in comments. BAD: "As said in the plan ...", "seed item 5", "PHASE1".
- A comment earns its place by saying something the code can't: the rationale, the constraint, the non-obvious consequence. BAD: "// loop over rows".
- Lead a non-trivial block with a short intent line, then the mechanism. Name the trap or the gotcha explicitly.

### How you code

- You write for humans, so a human maintainer feels comfortable reading (minimal cognitive load) and editing the code.
- Match the surrounding style when editing CCDB files: `ccdb.provider` and `ccdb.model` have their own naming and layout; new code inside them follows the file it lives in, not your defaults.
- Python: support the versions in pyproject.toml (`requires-python >= 3.9`, and CI runs every version of the matrix); no new runtime dependency for the core package. Web-only dependencies go in the `web` extra. The scripts under `{scripts}` follow the same rules, and pyflakes runs on them in CI.
- JavaScript: native ES modules, no build step, no globals beyond what a vendored library defines. One module per page or feature in `static/js/`, plus a shared `static/js/common.js` for theme and fetch helpers. A new vendored library goes through the vendor script like Bootstrap.
- Templates: one base layout, blocks for title, page header, content and page scripts. No CSS in `style=""` attributes beyond one-off layout tweaks; shared styles go in `static/css/ccdb.css` built on Bootstrap CSS variables so both themes work.
- You don't follow 80-character line cut-offs. If it is easier to read in one long line, do it. If a function definition reads better with each argument on its own line, use that. Decide from a human reader's point of view.
- Don't use short obscure variable names like `ac3` or `bumdbx`, but also don't make them unnecessarily long like `my_variable_to_hold_data`. Keep balance.
- Any place in the code must satisfy: if a new reader reads only this place, the variable names and comments let them understand the context and what is going on.
- A lot of import nesting is bad. Import B from A which is imported from C from D makes humans follow the whole chain and open all files. One very long file with everything is bad too. Decide on balance.
- For a single loop `i` is OK; for nested loops indexes must help understand the context: `row_i, col_i` for tables. Decide on balance.

### Git

Never commit, push, branch, stash, rebase or change the index. Never rewrite history. Never touch a branch.

Your progress lives in the working tree of {repo} plus **checkpoints** in `{space}/checkpoints/`, written by `{scripts}/checkpoint.sh` with `CCDB_SPACE={space}` and `CKPT_PLAN=<program>.md` set:

- `save <NN-name> [gate-result]` stores `git diff --binary HEAD` plus a tar of untracked, non-ignored files as `{space}/checkpoints/<NN-name>.{patch,tgz}`, and appends a line with the name, the time and the gate result to `{space}/checkpoints/INDEX.md`.
- `restore <NN-name>` returns the working tree to exactly that state: it restores tracked files with `git checkout -- .`, removes only the untracked files listed in the newest checkpoint tar, then applies the named patch and tar. The plan file and the workspace are never touched.
- Save a checkpoint after every finished work item whose gate checks pass. "Restore the last checkpoint" in this file means `restore` with the newest INDEX.md entry.
- Before the first save, check `git status`: if {repo} has changes that are not yours, **STOP** and ask; never mix them into a checkpoint or discard them. The script refuses the first save in that case too.
- At the end of each phase, the newest checkpoint patch is what the user reviews and commits. A commit by the user moves HEAD, and every checkpoint saved before it no longer applies (its patch is relative to the old HEAD): record that in STATUS.md and name the first valid checkpoint.
