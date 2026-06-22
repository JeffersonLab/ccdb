# Installation

CCDB APIs are available for different programming languages. Usually a user doesn't need every CCDB
feature, so you can install only what you need:

- [**Python** (library + `ccdb` command line tool)](#python) — the main client and management tool
- [**From source** (git clone + environment script)](#from-source)
- [**C++ API**](#c-api)
- [**MySQL** server setup](#mysql)
- [**Test the installation**](#test-the-installation)

## Python

The `ccdb` command and the Python API are published on [PyPI](https://pypi.org/project/ccdb/).
The recommended way is `pip` (or [`uv`](https://docs.astral.sh/uv/)):

```bash
# with pip
python -m pip install --upgrade ccdb

# or with uv
uv pip install ccdb
```

After installation you have:

- the `ccdb` Python library,
- the `ccdb` command, to work with CCDB in a terminal,
- `python -m ccdb`, which is equivalent to the `ccdb` command.

Optional extras:

```bash
# local web GUI (the `ccdb gui` command)
python -m pip install "ccdb[web]"
```

Check that it works (using the HallD read-only database as an example):

```bash
export CCDB_CONNECTION="mysql://ccdb_user@hallddb.jlab.org/ccdb"

ccdb -i          # interactive ccdb shell
ccdb ls /        # list the root directory
```

> See [Command line interface](../cli.md) for the full `ccdb` command reference and
> [connection strings](../concepts/concepts.md#connection-strings) for the connection string format.

## From source

If you want the full repository (C++, Java, SQL schema, scripts) or you are developing CCDB, clone
the repository and source the environment script:

```bash
git clone https://github.com/JeffersonLab/ccdb.git ccdb
source ccdb/environment.bash

# That's it! Check that it works
ccdb -i
```

`environment.bash` does the following:

- `CCDB_HOME` — set to where `environment.bash` is located
- `PATH` — adds `$CCDB_HOME/bin`
- `LD_LIBRARY_PATH` — adds `$CCDB_HOME/lib`
- `PYTHONPATH` — adds `$CCDB_HOME/python`

### Manual environment setup

Add to your `.bashrc`:

```bash
# set CCDB environment
export CCDB_HOME=/path/to/ccdb/home/directory

export LD_LIBRARY_PATH="$CCDB_HOME/lib":$LD_LIBRARY_PATH
export PYTHONPATH="$CCDB_HOME/python":$PYTHONPATH
export PATH="$CCDB_HOME/bin":$PATH
```

In order to log changes, it is **highly** desirable to let CCDB know your user name. If your login is
not the same as the `$USER` variable, define the `CCDB_USER` environment variable:

```bash
export CCDB_USER=<your login>
```

## C++ API

The C++ API is provided by the ccdb library. There are two configurations to choose from:

1. With SQLite **and** MySQL support (default)
2. With SQLite support **only** (no external dependencies except pthread)

The C++ API is built with CMake:

```bash
cd $CCDB_HOME
cmake -S . -B build
cmake --build build
```

> Older versions of CCDB used SCons. CMake is now the supported build system. See the
> [C++ API](../apis/cpp.md) page for details.

## MySQL

> **(!) SKIP this step if you are NOT going to install a MySQL CCDB database on YOUR server.**
> Usually this is not needed for users. To evaluate CCDB, open-for-read MySQL JLab servers
> (e.g. `hallddb`) and SQLite for write operations can be used instead.

To install a MySQL database on the local machine, create the database first. By default it is called
`ccdb`. By default CCDB connects with the `ccdb_user` user name and no password:

```sql
mysql -u root -p
    CREATE USER ccdb_user;
    CREATE SCHEMA IF NOT EXISTS `ccdb`;
    GRANT ALL PRIVILEGES ON ccdb.* TO 'ccdb_user'@'localhost';
    exit;
```

Now initialize the tables and default values:

```bash
ccdb db init
# You will need to add the `init-i-am-sure` flag. Just follow the prompt
```

You might need to increase the MySQL `max_allowed_packet` value (e.g. 32M) in order to get large
data tables from CCDB. Add to the `[mysqld]` section of `/etc/my.cnf`:

```ini
[mysqld]
max_allowed_packet=32M
```

More on the MySQL database:

- How to make a copy of a MySQL database to your local server is in the
  [Development](../development/development.md) section.
- A [MySQL Workbench](https://www.mysql.com/products/workbench/) project with the correct schema,
  [ccdb_eer_diagram.mwb](https://github.com/JeffersonLab/ccdb/blob/v2-main/sql/ccdb_eer_diagram.mwb),
  is located in `sql/`.

## Test the installation

To test that CCDB is installed correctly, run the unit tests:

```bash
. $CCDB_HOME/bin/test_ccdb_lib
. $CCDB_HOME/bin/test_ccdb_python3
```

You should see the CCDB unit tests run and complete successfully.

To check that the Python CLI works, start the interactive shell:

```bash
ccdb -i
```

## Distribution specific

### Fedora / RHEL

```bash
yum install cmake mysql-server mysql-devel python3-devel
```

If you haven't configured the MySQL server:

```bash
service mysqld start
mysqladmin -u root -h <host> password 'your-password'
```

### Ubuntu / Debian

```bash
apt-get install mysql-server cmake libmysqlclient-dev
```
