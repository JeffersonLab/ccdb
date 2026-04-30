# CCDB v1 → v2 Changelog

This report summarizes the user-visible changes between CCDB v1.x and the
current v2 line (`python/ccdb/version.py` → `v2.00.05`). The v2 line is marked
in history by commit `6b1a06e` ("SQLite upgrade to correct V5 (ccdb 2.0)
version", 2024-02-22), which raises the database schema version from 4 to 5.

The v1 schema is preserved under `sql/schemas_ccdb_v100/`; the v2 schema lives
in `sql/ccdb.mysql.sql` and `sql/ccdb.sqlite`.

## 1. Database schema (v1.00 / schema v4 → v2.00 / schema v5)

The v2 upgrade is additive — no v1 data is removed — and is applied via
`ccdb db upgrade` (see §3) or by running the queries in
`python/ccdb/sql/update_v5.py`.

### New columns

| Table | New columns | Purpose |
|---|---|---|
| `variations` | `lockedByUserId`, `goBackBehavior`, `goBackTime`, `isDeprecated`, `deprecatedByUserId` | Track who locked a variation, define "go back" replay behavior, and mark variations as deprecated |
| `directories` | `isDeprecated`, `deprecatedByUserId`, `isLocked`, `lockedByUserId` | Deprecation + locking on directories |
| `typeTables` | `isDeprecated`, `deprecatedByUserId`, `isLocked`, `lockedByUserId`, `lockTime` | Deprecation + locking on type tables |

`variations.isLocked` was also tightened from `INT` to `TINYINT(1)`.

### Renamed table

- `variations_has_tags` → `variationsToTags`

### `assignmentsMaterializedView`

Recreated without foreign-key constraints (v1 declared FKs to `assignments`,
`variations`, `constantSets`, `typeTables`, `runRanges`; v2 keeps the same
columns but drops the FKs to keep refreshes cheap).

### `schemaVersions`

Row `id=1` is bumped from `schemaVersion = 4` to `schemaVersion = 5`. The v2
client refuses to upgrade anything that is not exactly at v4.

## 2. New CLI subcommand: `ccdb db`

Added in `python/ccdb/cmd/commands/db.py`:

- `ccdb db` — print connection string and current schema version
- `ccdb db init --init-i-am-sure` — drop and recreate all tables
- `ccdb db upgrade --upgrade-i-am-sure` — run the v4 → v5 migration
  (`update_v5`) for both MySQL/MariaDB and SQLite
- `ccdb db stats` — print assignment and constant-set counts

## 3. Versioning and `--version`

- New module `python/ccdb/version.py` centralizes the version string
  (currently `v2.00.05`) and exposes `major`, `minor`, `patch`.
- `--version` flag added to the CLI help.

## 4. Web GUI rewrite

- The legacy site under `python/old_website/` is retired.
- A new Flask app lives in `python/ccdb/webgui/` with templates for the
  directory tree, type tables, variations, versions, and logs.
- Entry point is `python/ccdbweb.py`, refactored so the Flask `app` object
  can be served by Gunicorn.
- Connection string is taken from the `SQL_CONNECTION_STRING` env var.

## 5. Docker support (PR #102)

New `docker/` tree:

- `docker/docker-compose.yml` — `mysqldb` + `webgui` services on a shared
  bridge network with persistent MySQL volume
- `docker/mysqldb/Dockerfile` — initializes a `test_ccdb` database from
  `sql/test_user_init.sql` and `sql/ccdb.mysql.sql`
- `docker/webgui/Dockerfile` — installs `python/ccdb/webgui/requirements-web.txt`
  and serves the GUI via Gunicorn on port 5000

## 6. C++ library

- `cpp/src/CCDB/CMakeLists.txt` adds a `CCDB_CACHE_ON` CMake option
  (default OFF). When enabled it defines the `CCDB_CACHE_ON` compile macro
  on the `ccdb` target (PR #103).

## 7. Build / CI / tooling

- GitHub Actions CI added (`.github/workflows/ci.yaml`) — runs Python tests
  against a MySQL 8.3 service container; CI badge added to `README.md`.
- Removed the top-level `SConstruct` (SCons retained only under
  `cpp/`/`doc/latex/`).
- `scripts/users_create/users_create.py` ported to Python 3 and gained a
  `--test` flag.

## 8. CLI fixes and small improvements (v2 line)

- `cat` and `dump` accept relative paths in interactive mode.
- `cat` honors a user-provided default run and variation.
- `vers` prints the user that created each assignment.
- `mktbl` validates that the column types are correct.
- `mkdir` gained a help text.
- Better parse errors for run ranges and improper commands.
- Improved exception handling (`python/ccdb/errors.py`,
  `cli_manager.py`, `provider.py`) and friendlier upgrade-command reporting.
- `CCDB_USER` environment variable is honored; user name can be passed as a
  flag.
- MySQL user privileges in `sql/create_user_example.sql` updated to match
  the new tables.
- SQLAlchemy compatibility fixes for newer releases.

## 9. Migration notes

To move an existing v1 deployment to v2:

1. Back up the database.
2. Pull v2 code and install Python deps from `python/requirements.txt`.
3. Run `ccdb db` to confirm `Schema version: 4`.
4. Run `ccdb db upgrade --upgrade-i-am-sure`. This adds the lock /
   deprecation columns and bumps `schemaVersions` to 5.
5. (Optional) Stand up the new web GUI via `docker/docker-compose.yml` or
   by running `python/ccdbweb.py` with `SQL_CONNECTION_STRING` set.

For brand-new SQLite installs, copy `sql/ccdb.sqlite` (already at v5) or run
`ccdb db init --init-i-am-sure` against an empty database.
