# Development

## Development install (Python, uv)

The Python package is configured with a modern `pyproject.toml` at the repository root and uses
[uv](https://docs.astral.sh/uv/). To set up a development environment:

```bash
git clone https://github.com/JeffersonLab/ccdb.git
cd ccdb

# create the virtual environment and install ccdb (editable) with dev + web extras
uv sync --extra dev --extra web

# run the CLI from the project
uv run ccdb --version
uv run ccdb -i
```

`uv run ccdb` is equivalent to running the installed `ccdb` command. You can also run the CLI as a
module with `python -m ccdb`.

To build distributions (wheel + sdist) for [PyPI](https://pypi.org/project/ccdb/):

```bash
uv build          # produces dist/ccdb-<version>-py3-none-any.whl and dist/ccdb-<version>.tar.gz
```

The package version is defined in
[python/ccdb/version.py](https://github.com/JeffersonLab/ccdb/blob/v2-main/python/ccdb/version.py) and
is picked up automatically by the build (dynamic version).

## Tools

- Running
  [python/ccdbcmd.py](https://github.com/JeffersonLab/ccdb/blob/v2-main/python/ccdbcmd.py) is the same
  as running the `ccdb` command. This can be helpful for debugging, IDE setup, etc.:
  ```bash
  # same as > ccdb
  python3 $CCDB_HOME/python/ccdbcmd.py
  ```
- Running
  [python/ccdbweb.py](https://github.com/JeffersonLab/ccdb/blob/v2-main/python/ccdbweb.py) starts the
  website / GUI for CCDB with your local setup.

## Tests organization

Unit tests look for two environment variables:

1. `CCDB_TEST_MYSQL_CONNECTION` — if not found, `mysql://ccdb_user@localhost/ccdb_test` is used.
2. `CCDB_TEST_SQLITE_CONNECTION` — if not found, `sqlite:///$PWD/test.sqlite` is used.

Tests create their own SQLite database (schema + standard test data) via
`ccdb.testing.recreate_test_sqlite_db()`, which uses `ccdb.sql.sqlite_schema`.
There is no committed database file; the same schema/data can be created from
the command line with `ccdb -c sqlite:////path/to/db.sqlite db init --init-i-am-sure`.

It is assumed that, for unit tests on a MySQL database, a schema named `ccdb_test` and a user named
`ccdb_user` are used.

Create the user:

```bash
mysql -u root -p -e "CREATE USER ccdb_user@'localhost';"
```

Grant permissions to the user:

```bash
mysql -u root -p -e "GRANT ALL PRIVILEGES ON ccdb_test.* TO 'ccdb_user'@'localhost';"
```

There is a helpful command to (re)create the test database contents:

```bash
ccdb db init
```

## MySQL and SQLite databases

- The schema is defined in Python:
  [python/ccdb/sql/mysql_schema.py](https://github.com/JeffersonLab/ccdb/blob/v2-main/python/ccdb/sql/mysql_schema.py)
  for MySQL and MariaDB and
  [python/ccdb/sql/sqlite_schema.py](https://github.com/JeffersonLab/ccdb/blob/v2-main/python/ccdb/sql/sqlite_schema.py)
  for SQLite. `ccdb db init` creates a database from them. A change to the layout is made in both files,
  with an upgrade step in `python/ccdb/sql/` for existing databases.
- `sql/ccdb.mysql.sql` is generated from `mysql_schema.py`. To regenerate it, run from the repository
  root:
  ```bash
  python -m ccdb.sql.mysql_schema sql/ccdb.mysql.sql
  ```
- The MySQL Workbench model `sql/ccdb_eer_diagram.mwb` is kept as it was; it does not show schema
  version 6. The other SQL files in `sql/` are older scripts and examples; `ccdb db init` and
  `ccdb db upgrade` do not use them.

### Upgrade the CCDB database schema

Check the current schema:

```bash
# Make sure your CCDB_CONNECTION is set to the correct db, or use the -c flag
ccdb db

# or
ccdb -c mysql://ccdb_user@hallddb.jlab.org/ccdb db
```

To upgrade a database to the schema of the installed CCDB, follow
[Upgrading to CCDB 2.5](deployment/upgrade-2.5.md): it starts with a backup and a dry run, which
writes nothing:

```bash
ccdb db upgrade --dry-run
```

### Copy MySQL to a local machine

If you have a local running MySQL and would like to copy a running experiment's CCDB to your local
machine (if local MySQL is not yet created, follow the
[MySQL installation instructions](get-started/installation.md#mysql)):

```bash
# 1. Make a dump of the production MySQL database:
mysqldump -u ccdb_user -h hallddb.jlab.org ccdb > dump.mysql.sql

# 2. Import the database:
mysql -u ccdb_user -h localhost ccdb < dump.mysql.sql
```

### Convert MySQL to SQLite

> Newer, simpler-to-use projects for MySQL → SQLite conversion exist, such as
> [mysql-to-sqlite3](https://github.com/techouse/mysql-to-sqlite3).

The CCDB repository ships an old
[mysql2sqlite](https://github.com/JeffersonLab/ccdb/blob/v2-main/scripts/mysql2sqlite/mysql2sqlite)
script (Authors: @esperlu, @artemyk, @gkuenning, @dumblob) that is used for the HallD CCDB instance.
The script takes a MySQL-flavored SQL file and converts it to SQLite-flavored syntax. Using the HallD
CCDB database as an example, the complete steps to convert the database are:

```bash
# Use standard mysqldump to read the MySQL database into a file with SQL queries.
mysqldump --skip-tz-utc -u ccdb_user -h hallddb.jlab.org ccdb > dump.mysql.sql

# Convert MySQL-flavored SQL to SQLite-flavored SQL via mysql2sqlite
./mysql2sqlite dump.mysql.sql > dump.sqlite3.sql

# Create a DB out of the SQL file
sqlite3 ccdb.sqlite3.db < dump.sqlite3.sql
```

> `mysqldump` converts times to UTC by default (see
> [#100](https://github.com/JeffersonLab/ccdb/issues/100)); without `--skip-tz-utc` this would lead to
> a time shift between MySQL and SQLite (at least when using the scripts above).

## Documentation

This documentation website is generated from the Markdown files in the
[docs/](https://github.com/JeffersonLab/ccdb/tree/v2-main/docs) folder, powered by
[Docsify](https://docsify.js.org/), and deployed to GitHub Pages via the
[.github/workflows/documentation.yml](https://github.com/JeffersonLab/ccdb/blob/v2-main/.github/workflows/documentation.yml)
workflow.

Docsify renders Markdown into a website with no build step. To preview locally, serve the `docs`
folder with any static server:

```bash
# from the repository root
python3 -m http.server 3000 --directory docs
# then open http://localhost:3000
```

To add a page, create a Markdown file under `docs/` and add a link to it in `docs/_sidebar.md`. Use
lower-case-with-dashes file names and group related pages into subfolders (e.g. `concepts/`, `apis/`).
