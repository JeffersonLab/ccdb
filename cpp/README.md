
## Compilation

Requirements: CMake 3.16 or newer, a C++ compiler, the SQLite 3 development package
(`libsqlite3-dev`); for `mysql://` connections the MySQL or MariaDB client development package
(`libmysqlclient-dev` or `libmariadb-dev`), used when CMake finds it.

```bash
cmake -S $CCDB_HOME/cpp -B <build dir> -DCMAKE_INSTALL_PREFIX=<install dir>
cmake --build <build dir> -j 16
cmake --install <build dir>
```

The install directory receives `lib/libccdb.so`, the headers in `include/CCDB/`, the CMake package in
`lib/cmake/ccdb/` and the test program `bin/ccdb_tests`. Options: `-DCCDB_BUILD_TESTS=OFF` skips the
test program, `-DCMAKE_DISABLE_FIND_PACKAGE_MySQL=ON` builds without MySQL support,
`-DCCDB_CACHE_ON=ON` starts every `Calibration` with its assignment cache on.

## Use from a CMake project

```cmake
find_package(ccdb 2.5 CONFIG REQUIRED)        # configure with -DCMAKE_PREFIX_PATH=<install dir>
target_link_libraries(myapp PRIVATE ccdb::ccdb)
```

Or, with the CCDB sources inside the project: `add_subdirectory(<ccdb>/cpp ccdb)` and the same
`ccdb::ccdb` target. `examples/consumer` is a complete project.

## Tests

The Catch2 suite reads a database created by the Python CLI:

```bash
ccdb -c sqlite:///$HOME/ccdb_test.sqlite db init --init-i-am-sure
CCDB_TEST_SQLITE_CONNECTION=sqlite:///$HOME/ccdb_test.sqlite <build dir>/src/tests/ccdb_tests "~[mysql]"
```

The `[mysql]` cases need `CCDB_TEST_MYSQL_CONNECTION` pointing to a MySQL database initialized the
same way.

## Connection settings

### MySQL timeouts and reconnect

| Environment variable          | Default | Meaning                                                    |
|-------------------------------|---------|------------------------------------------------------------|
| `CCDB_MYSQL_CONNECT_TIMEOUT`  | 10      | Seconds to wait for the server when connecting             |
| `CCDB_MYSQL_READ_TIMEOUT`     | 300     | Seconds to wait for data from the server during a query    |
| `CCDB_MYSQL_WRITE_TIMEOUT`    | 300     | Seconds to wait when sending data to the server            |

Values must be positive integers. An invalid value prints a warning and the default is used.
Read/write timeouts are large because a single constant set can be tens of MB.

If the server closed the connection (`MySQL server has gone away` / `Lost connection to server`,
e.g. after `wait_timeout` in a long job), CCDB reconnects once and repeats the (read-only) query.
If that fails too, the error is thrown and `IsConnected()` returns false; the next request
tries to reconnect again (auto-reconnect).

Passwords are masked (`mysql://user:***@host`) in all error messages.

### SQLite

The file is opened read-only and is never created: a wrong path is an error that names the file.

| Environment variable        | Default | Meaning                                                              |
|-----------------------------|---------|----------------------------------------------------------------------|
| `CCDB_SQLITE_BUSY_TIMEOUT`  | 30000   | Milliseconds to wait while another process holds a write lock        |

SQLite URI file names are supported. For a snapshot on a network file system (NFS, Lustre)
where file locking is slow or not available, open it as immutable (no locking at all;
only valid if nobody modifies the file while it is used):

```
sqlite:///file:/group/halld/ccdb/ccdb.sqlite?immutable=1
```

`?mode=ro` and other [SQLite URI parameters](https://www.sqlite.org/uri.html) work the same way.
Plain paths (`sqlite:////path/to/ccdb.sqlite`) work as before.

### CalibrationGenerator ownership

`CalibrationGenerator` is thread safe. A `Calibration` returned by `MakeCalibration` may be deleted
by the caller at any time; the generator then forgets it. The generator itself does not delete
Calibrations: its destructor closes the connections of those still alive (they stay usable and
reconnect on the next request). Call `DeleteCalibrations()` to delete them when nothing else does.
