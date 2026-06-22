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
2. `CCDB_TEST_SQLITE_CONNECTION` — if not found, `sqlite:///$CCDB_HOME/sql/ccdb.sqlite` is used.

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

- The authoritative source of the MySQL schema is the
  [MySQL Workbench](https://www.mysql.com/products/workbench/) project
  [ccdb_eer_diagram.mwb](https://github.com/JeffersonLab/ccdb/blob/v2-main/sql/ccdb_eer_diagram.mwb).
  Every change to the database layout is made here first, then propagated to scripts and SQLite.
- The Python `ccdb` library has SQL scripts embedded in
  [python/ccdb/sql](https://github.com/JeffersonLab/ccdb/tree/v2-main/python/ccdb/sql). After a
  `ccdb_eer_diagram.mwb` change they must be synchronized there too.
- There are SQL scripts in the `sql` directory, but they are obsolete and will be removed in future
  versions.

### Upgrade the CCDB database schema

Check the current schema:

```bash
# Make sure your CCDB_CONNECTION is set to the correct db, or use the -c flag
ccdb db

# or
ccdb -c mysql://ccdb_user@hallddb.jlab.org/ccdb db
```

To update (**NEVER DO THIS ON A PRODUCTION SERVER WITHOUT PRIOR PROPER CHECKS**):

```bash
ccdb db update
# follow the prompt
```

### Copy MySQL to a local machine

If you have a local running MySQL and would like to copy a running experiment's CCDB to your local
machine (if local MySQL is not yet created, follow the
[MySQL installation instructions](../get-started/installation.md#mysql)):

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
