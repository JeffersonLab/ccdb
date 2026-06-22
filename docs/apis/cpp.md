# C++ API

```
 +------------------+      +------------------+
 |   C++ User API   |  --  |     JANA API     |
 +------------------+      +------------------+
           |
+----------------------+
| Internal C++ Library |
+----------------------+
```

The CCDB C++ implementation consists of separate levels (see the figure above):

- **C++ User API** — This level is **most probably what any user** who is not bound to JANA **needs**.
  The API provides simple functionality to get constants. It automates the number of connections,
  multi-threading, data source selection, etc.

- **JANA API** — This level integrates CCDB and the [JANA framework](https://www.jlab.org/JANA/about.php).
  The JANA API is now shipped with the JANA framework. Architecturally it is based on the C++ User API.
  See [JANA API](jana.md).

- **Internal C++ Library** — This level is considered internal and should only be of interest for
  those contributing to further development of CCDB. Application developers should not use classes from
  this library directly.

  The internal library is subject to change for better CCDB performance or maintainability. In
  general, changes in this library will not affect code that uses the higher-level APIs. That is why
  the internal library should be kept separate and used only inside the higher CCDB levels.

> See [Installation → C++ API](../get-started/installation.md#c-api) for how to build the library.

## User API in a nutshell

```cpp
// The generator can automatically determine whether it is MySQL or SQLite
// depending on the connection string.
// Parameters:
//   connectionString
//   run
//   variation
//   time = 0   // 0 = now
// Example for run 1500, default variation, using the latest constants:
CalibrationGenerator generator;
auto calib = generator.MakeCalibration("mysql://...", 1500, "default", 0);

// CCDB automatically reconnects to the DB
calib->GetCalib("/constants/path");

// (!!!) In the current implementation, if CalibrationGenerator::MakeCalibration
// is used, do NOT delete the connections manually (with delete)
auto calib = generator.MakeCalibration("<connection string>");
delete calib;  // <== DON'T DO THIS
calib = generator.MakeCalibration("<SAME connection string>");  // Problem: deleted pointer.
```

## Connection to the database

The [ccdb::Calibration](https://github.com/JeffersonLab/ccdb/blob/v2-main/cpp/include/CCDB/Calibration.h)
class is responsible for holding a connection with the DB.

- [ccdb::MySQLCalibration](https://github.com/JeffersonLab/ccdb/blob/v2-main/cpp/include/CCDB/MySQLCalibration.h) and
- [ccdb::SQLiteCalibration](https://github.com/JeffersonLab/ccdb/blob/v2-main/cpp/include/CCDB/SQLiteCalibration.h)

inherit from `Calibration` to provide concrete implementations for MySQL and SQLite.

[ccdb::CalibrationGenerator](https://github.com/JeffersonLab/ccdb/blob/v2-main/cpp/include/CCDB/CalibrationGenerator.h)
can be used to automatically instantiate the right `Calibration` type according to the connection
parameter:

```cpp
// MySQLCalibration is created according to the "mysql://..." connection string
auto calib = CalibrationGenerator::CreateCalibration("mysql://ccdb@hallddb.jlab.org", ...);
```

## Connection management

In general a MySQL connection is a limited resource, and that is how CCDB treats it. There are two
general ways to manage a CCDB connection: manually, or by using `CalibrationGenerator`.

### Managing MySQLCalibration manually

When the connection is really established:

```cpp
// The connection is established when using the CreateCalibration static method:
auto calib = CalibrationGenerator::CreateCalibration("<connection string>", ...);

// Using the direct constructor doesn't establish the connection.
auto calib = new MySqlConnection(...);

// 2 ways to establish the connection:
calib->Connect("<connection string>");   // makes a database connection
calib->Reconnect();                      // makes a database connection if none exists
                                         // (Reconnect fails if the connection string is not set)

// If the connection string is set but Calibration is not connected,
// CCDB automatically establishes the connection when required:
auto data = calib->GetCalib(...);        // connection is opened/reopened here
```

Suspend the connection during inactivity:

```cpp
// Calibration tracks the last time it retrieved data from the DB.
// GetLastActivityTime() can be used to check the inactivity time.
// CCDB has no automatic timer. The user is responsible (!) for doing something like:
if (time_now - calib->GetLastActivityTime() > TIME_THRESHOLD) {   // TIME_THRESHOLD set by user
    calib->Disconnect();   // really closes the connection
}

// After you closed the connection...
auto data = calib->GetCalib(...);      // the connection is reopened/opened
```

Disconnect from the DB:

```cpp
calib->Disconnect();               // close connection with the DB
auto data = calib->GetCalib(...);  // the connection is reopened/opened
delete calib;                      // RAII closes the connection too
```

Check the connection:

```cpp
calib->IsConnected();  // check the connection status
```

### Managing Calibration with CalibrationGenerator

```cpp
// The generator can automatically check the inactivity of all
// connections it spawned with the MakeCalibration method.
CalibrationGenerator generator;
auto calib = generator.MakeCalibration("<connection string>", ...);

// To automatically close inactive connections, periodically call
// UpdateInactivity() (CCDB does not use an internal timer).
generator.UpdateInactivity();   // call it periodically

// If the connection is closed and data is requested afterwards,
// CCDB automatically reconnects to the DB
calib->GetCalib(<request>);  // <= OK, ccdb will reconnect
```

```cpp
// You may control when CalibrationGenerator disconnects:
time_t GetMaxInactiveTime() const;
void SetMaxInactiveTime(time_t val);  // if 0, inactivity isn't checked by UpdateInactivity
```

The connection class is built around the usage assumption of an *intensive beginning, idle during
event processing*. At the start of work, analysis software has an initialization phase during which a
lot of requests are made to the DB. During event processing, requests are rare or absent.

## Performance profiling

CCDB may be built with a performance profiling flag. The outputs of running CCDB can then be analyzed
with
[python/ccdb_cpp_perf.py](https://github.com/JeffersonLab/ccdb/blob/v2-main/python/ccdb_cpp_perf.py).

This allows evaluating the performance and behavior of the C++ CCDB API in working applications. The
C++ API must be compiled with the perflog flag (it defines `CCDB_PERFLOG_ON` in C++).

With this flag, whenever any constant is requested, CCDB writes performance info to `std::cout`.
Example of one record:

```
CCDB_PERF_LOG:{"thread_id":139771280078592,"descr":"Calibration::GetAssignment=>/PHOTON_BEAM/endpoint_energy","start_stamp":1498647171590502,"elapsed":1558,"t_units":"us"}
```

Save all output to a file and provide its path to `ccdb_cpp_perf.py`:

```bash
<analysing_soft> ... > ccdb_perf.log
python $CCDB_HOME/python/ccdb_cpp_perf.py ccdb_perf.log
```

### Troubleshooting

If you don't see `CCDB_PERF_LOG:...` messages and you are sure that ccdb is called at all, check with
`ldd` that the right copy of `ccdb.so` is loaded.
