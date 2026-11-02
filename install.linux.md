# Installing CCDB on Linux

The full guide, with every option, is the documentation page
[Installation](https://jeffersonlab.github.io/ccdb/#/get-started/installation); its source is
`docs/get-started/installation.md` in this repository. This file is the short form.

## Python library and the `ccdb` command

```bash
python -m pip install ccdb            # add the web GUI with "ccdb[web]"
```

Or, from this repository without installing: `source environment.bash`. It sets `CCDB_HOME`
and adds `$CCDB_HOME/bin` to `PATH`, `$CCDB_HOME/python` to `PYTHONPATH` and `$CCDB_HOME/lib` to
`LD_LIBRARY_PATH`.

To log changes under your name, set `CCDB_USER` when your login differs from `$USER`.

## C++ library

Requirements: CMake 3.16 or newer, a C++ compiler, the SQLite 3 development package; for MySQL
connections the MySQL or MariaDB client development package.

```bash
# Debian, Ubuntu
apt-get install cmake g++ libsqlite3-dev libmysqlclient-dev
# Fedora, RHEL, AlmaLinux
dnf install cmake gcc-c++ sqlite-devel mysql-devel
```

To build and install the library into `$CCDB_HOME` (`lib`, `include`, `bin`), run:

```bash
cd $CCDB_HOME
cmake -S cpp -B build -DCMAKE_INSTALL_PREFIX=$CCDB_HOME
cmake --build build -j8
cmake --install build
```

Without the MySQL client package, or with `-DCMAKE_DISABLE_FIND_PACKAGE_MySQL=ON`, the library reads
SQLite only. Other projects use it with `find_package(ccdb 2.5 CONFIG REQUIRED)` and the target
`ccdb::ccdb`; `cpp/README.md` has the details.

## MySQL database

Skip this section unless you run your own CCDB server. Create the database and a user, then create
the CCDB tables with the `ccdb` command:

```sql
CREATE DATABASE ccdb;
CREATE USER 'ccdb_user'@'localhost';
GRANT ALL PRIVILEGES ON ccdb.* TO 'ccdb_user'@'localhost';
```

```bash
ccdb -c mysql://ccdb_user@localhost/ccdb db init --init-i-am-sure
```

Large tables need a larger `max_allowed_packet`, for example `max_allowed_packet=32M` in the `[mysqld]`
section of `/etc/my.cnf`.

## Check the installation

```bash
ccdb -c sqlite:///$HOME/ccdb_test.sqlite db init --init-i-am-sure
ccdb -c sqlite:///$HOME/ccdb_test.sqlite ls /test/test_vars
CCDB_TEST_SQLITE_CONNECTION=sqlite:///$HOME/ccdb_test.sqlite $CCDB_HOME/bin/ccdb_tests "~[mysql]"
```
