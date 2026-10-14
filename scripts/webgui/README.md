# Web GUI checks

Scripts that check the CCDB web GUI (`python/ccdb/webgui`) against a deterministic fixture database. CI runs them on every push (`.github/workflows/webgui-tests.yml` and `webgui-browser.yml`); agent runs use them as the ruler of every phase (`web-agents-common.md` at the repository root).

| script | what it does |
|---|---|
| `make_fixture.py` | builds the fixture database: the CCDB schema with the standard test content plus a 3600-assignment table over 6 variations, a 7-level directory chain, 1000 bulk tables, hostile names and comments, a 4-level variation chain and 2400 log records. Fixed seed and timestamps, so every build hashes the same; `--verify` builds twice and compares |
| `pages.py` | the URL list the other scripts share, with a kind per URL: page, fragment, data or edge. Paths refer to objects of the fixture, so change both files together |
| `smoke.py` | requests every URL in-process, or a live server with `--base-url`, and records status, bytes, time and SQL query count; `--check` fails on a server error or on a status outside what the kind allows |
| `golden.py` | `compute` derives what every page must show from SQL on the fixture, with no ORM in between; `compare` parses the pages and reports every mismatch, with exit code 1 on a failure |
| `browse.py` | Playwright: every page in Chromium and Firefox, light and dark, 1400×900 and 390×844; a screenshot per visit, console errors, failed requests, page weight and horizontal overflow; `--check` fails on any of them |
| `checkpoint.sh` | saves and restores working-tree checkpoints, a patch against HEAD plus a tar of untracked files, without touching git history |
| `workspace.py` | shared by the Python scripts: the `--space` convention and the repository root |

## The workspace

Every script writes into a workspace directory given as `--space DIR` or through `CCDB_SPACE`:

- `fixture/` — the database `ccdb_fixture.sqlite`
- `reports/` — JSON results and the server log
- `plots/` — screenshots

Workspaces are named `space-<name>` and stay outside version control (`.gitignore` lists `space-*/`).

## Running

From a checkout with the project environment. `uv run` resolves `ccdb` and Flask; a virtual environment with `pip install ".[web]"` works the same with plain `python`.

```bash
export CCDB_SPACE=$PWD/space-local
uv run python scripts/webgui/make_fixture.py --verify
uv run python scripts/webgui/smoke.py --label today --check
uv run python scripts/webgui/golden.py compute
uv run python scripts/webgui/golden.py compare --label today
uv run --with playwright==1.63.0 python scripts/webgui/browse.py --browser all --label today --check
```

Playwright is not a project dependency. Pin `--with playwright==<version>` to the browser builds installed with `playwright install chromium firefox`: an unpinned `--with playwright` resolves the newest release, whose browsers are not installed. On a new host, run `uv run --with playwright==1.63.0 playwright install chromium firefox` once.

Inside a program run, add `--phase N`, and `--feature NAME` for `browse.py`: the reports are then named `smoke_phase2_gate.json`, and screenshots go to `plots/phase2/<feature>/`. `smoke.py --base-url http://host:port` requests a running server instead of the in-process app, for a byte-level comparison of a wheel or a container with the checkout.

## What --check enforces

| kind | `smoke.py` | `browse.py` |
|---|---|---|
| page, fragment | 200 | 200, no console or page error, no failed request, no horizontal overflow |
| data | 200, or a 302 to the data | not opened |
| edge | anything below 500 | 4xx; its own status is the one failed response and the one Chromium console line allowed |

A status of 500 or more fails everywhere.

## Checkpoints

```bash
export CCDB_SPACE=$PWD/space-local
CKPT_PLAN=ccdb-webgui.md scripts/webgui/checkpoint.sh save 03-tree "131 tests OK, golden 120/0"
scripts/webgui/checkpoint.sh restore 03-tree
```

`save` writes `<space>/checkpoints/<name>.patch` and `.tgz` and adds a row to `INDEX.md`. The first `save` refuses when the working tree has changes other than the program plan file, so someone else's uncommitted work is never mixed in. `restore` returns the tracked files to HEAD, except the plan file and the workspace, removes the untracked files listed in the newest checkpoint, then applies the named patch and tar. A commit moves HEAD, and checkpoints saved before it no longer apply.
