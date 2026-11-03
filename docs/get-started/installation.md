# Installation

CCDB APIs are available for different programming languages. Usually a user doesn't need every CCDB
feature, so you can install only what you need:

- [**Python** (library + `ccdb` command line tool)](#python) — the main client and management tool
- [**From source** (git clone + environment script)](#from-source)
- [**C++ API**](#c-api) — build with CMake or [use from a CMake project](#use-the-library-from-a-cmake-project)
- [**MySQL** server setup](#mysql)
- [**Test the installation**](#test-the-installation)

A Java library for CCDB and RCDB is maintained separately:
[ccdbrcdb-java](https://code.jlab.org/hallb/clas12/coatjava/ccdbrcdb-java).

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

Check that it works (using the HallD read-only database as an example; until its administrators upgrade it to
schema 6 it answers CCDB 2.4 only, `pip install "ccdb<2.5"`):

```bash
export CCDB_CONNECTION="mysql://ccdb_user@hallddb.jlab.org/ccdb"

ccdb -i          # interactive ccdb shell
ccdb ls /        # list the root directory
```

> See [Command line interface](cli.md) for the full `ccdb` command reference and
> [connection strings](concepts/concepts.md#connection-strings) for the connection string format.

## From source

If you want the full repository (C++, SQL schema, scripts) or you are developing CCDB, clone
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
- `LD_LIBRARY_PATH` — adds `$CCDB_HOME/lib`, where the C++ library lands when you install it with
  `-DCMAKE_INSTALL_PREFIX=$CCDB_HOME` (see [C++ API](#c-api))
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

The C++ API is the `ccdb` shared library. It always reads SQLite files; it also reads MySQL and
MariaDB servers when CMake finds the MySQL or MariaDB client library at configure time.

Requirements:

- CMake 3.16 or newer and a C++ compiler
- the SQLite 3 development package (`libsqlite3-dev`, `sqlite-devel`)
- optional: the MySQL or MariaDB client development package (`libmysqlclient-dev` or `libmariadb-dev`,
  `mysql-devel` or `mariadb-connector-c-devel`) for `mysql://` connections

To build the library and install it under a prefix, run from the repository root:

```bash
cmake -S cpp -B build -DCMAKE_INSTALL_PREFIX=$HOME/ccdb
cmake --build build -j8
cmake --install build
```

The prefix receives `lib/libccdb.so`, the headers in `include/CCDB/`, the CMake package in
`lib/cmake/ccdb/` and the test program `bin/ccdb_tests`. With `-DCMAKE_INSTALL_PREFIX=$CCDB_HOME`,
the library lands in `$CCDB_HOME/lib`, which `environment.bash` puts on `LD_LIBRARY_PATH`.

CMake options:

| option | default | effect |
|---|---|---|
| `CCDB_BUILD_TESTS` | `ON` | builds the Catch2 test program `ccdb_tests` and installs it to `bin` |
| `CCDB_CACHE_ON` | `OFF` | every `Calibration` starts with its in-memory cache of read assignments on; `EnableCache()` switches it at run time |
| `CCDB_BUILD_JANA2` | `OFF` | builds the [JANA2 service](apis/jana.md) `CCDB_service`; needs JANA2 |
| `CMAKE_DISABLE_FIND_PACKAGE_MySQL` | `OFF` | `ON` builds without MySQL support even when the client library is installed |

### Use the library from a CMake project

The installed library is a CMake package. To use it, find the package and link the `ccdb::ccdb`
target; the target carries the include directory and the libraries CCDB links:

```cmake
find_package(ccdb 2.5 CONFIG REQUIRED)
target_link_libraries(myapp PRIVATE ccdb::ccdb)
```

```cpp
#include <CCDB/Calibration.h>
#include <CCDB/CalibrationGenerator.h>
```

Point CMake at the prefix when you configure your project:

```bash
cmake -S . -B build -DCMAKE_PREFIX_PATH=$HOME/ccdb
```

`ccdb_WITH_MYSQL` is `TRUE` after `find_package` when the library was built with MySQL support. A
project that builds CCDB as part of its own tree uses the same target name:

```cmake
set(CCDB_BUILD_TESTS OFF)
add_subdirectory(path/to/ccdb/cpp ccdb)
target_link_libraries(myapp PRIVATE ccdb::ccdb)
```

`cpp/examples/consumer` is a complete project of this kind; it reads one table and prints it.

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
  [Development](development/development.md) section.
- The schema is defined in `python/ccdb/sql/` and documented on
  [Database schema](concepts/database-schema.md); `sql/ccdb.mysql.sql` is generated from it. The
  MySQL Workbench model `sql/ccdb_eer_diagram.mwb` does not show schema version 6.

## Test the installation

To check the `ccdb` command, create a test SQLite database and list it:

```bash
ccdb -c sqlite:///$HOME/ccdb_test.sqlite db init --init-i-am-sure
ccdb -c sqlite:///$HOME/ccdb_test.sqlite ls /test/test_vars
```

To run the C++ test program on that database (MySQL cases excluded):

```bash
CCDB_TEST_SQLITE_CONNECTION=sqlite:///$HOME/ccdb_test.sqlite $HOME/ccdb/bin/ccdb_tests "~[mysql]"
```

To start the interactive shell:

```bash
ccdb -i
```

## Distribution specific

### Fedora / RHEL

```bash
dnf install cmake gcc-c++ sqlite-devel mysql-devel python3-devel   # mysql-server for a local server
```

If you haven't configured the MySQL server:

```bash
service mysqld start
mysqladmin -u root -h <host> password 'your-password'
```

### Ubuntu / Debian

```bash
apt-get install cmake g++ libsqlite3-dev libmysqlclient-dev   # mysql-server for a local server
```
