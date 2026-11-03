# JANA2 service

`CCDB_service` gives [JANA2](https://github.com/JeffersonLab/JANA2) factories the calibration constants
of the run they process. It is a JANA2 service in the style of the EICrecon services: a factory declares
it as a member, reads its tables in `ChangeRun()`, and the job chooses the database, the variation and
the time, or one tag, with parameters. The service depends on JANA2 and the CCDB C++ library only.

## Build

The service lives in the `jana2/` directory of the CCDB repository and builds with the C++ library when
the CMake option `CCDB_BUILD_JANA2` is on. CMake must find JANA2 (`find_package(JANA)`); in the ePIC
`eic-shell` environment it does. To build and install it, run from the repository root:

```bash
cmake -S cpp -B build -DCCDB_BUILD_JANA2=ON -DCMAKE_INSTALL_PREFIX=$HOME/ccdb
cmake --build build -j8
cmake --install build
```

Besides the C++ library, the prefix receives:

| file | what it is |
|---|---|
| `lib/libccdb_jana2.so` | the library with the class `CCDB_service`; link it to use the class |
| `lib/CCDB/plugins/CCDB_service.so` | the plugin that provides the service to a job |
| `include/CCDB/JANA2/CCDB_service.h` | the header |
| `lib/cmake/ccdb/ccdbJana2Targets.cmake` | the CMake component `jana2` with the target `ccdb::ccdb_jana2` |

## Load the service in a job

To make the plugin visible, add its directory to `JANA_PLUGIN_PATH`. Then load it and give the
connection string:

```bash
export JANA_PLUGIN_PATH=$HOME/ccdb/lib/CCDB/plugins:$JANA_PLUGIN_PATH
jana -Pplugins=CCDB_service,myplugin \
     -Pccdb:url=sqlite:////cvmfs/example.org/ccdb/ccdb.sqlite \
     -Pccdb:tag=calib_2026_pass1 \
     run_1000.root
```

The parameters:

| parameter | default | meaning |
|---|---|---|
| `ccdb:url` | `$CCDB_CONNECTION`, then `$JANA_CALIB_URL` | connection string: `mysql://user@host/ccdb`, `sqlite:////path/ccdb.sqlite`, or the [HTTP API](apis/cpp.md#http-api) `https://host/api/v1` |
| `ccdb:variation` | `default` | variation of the constants; a variation without a table inherits it from its parent |
| `ccdb:time` | empty: the newest constants | the newest constants as of this local time: `2026`, `2026-03`, `2026-03-01 12:00:00`, `2026-03-01 12:00:00.250`; a partial time is the latest moment it covers ([Time](concepts/time.md)) |
| `ccdb:tag` | empty | a tag gives both the variation and the time; it can't be set together with `ccdb:variation` or `ccdb:time` |
| `ccdb:cache_dir` | `$XDG_CACHE_HOME/ccdb/resources`, else `$HOME/.cache/ccdb/resources` | where `GetResource` keeps the files it fetched |
| `ccdb:provenance` | empty: no record | a file; the service records which version every request resolved to and writes the record there when it ends ([below](#what-a-job-used)) |

The service checks the parameters when the application starts: a missing connection string, a time it
can't read, an invalid tag name or a tag set together with a variation or a time stops the job with a
message that names the parameter. At startup it logs the connection string (without the password) with
the variation and the time, or the tag; with neither a time nor a tag it warns that the job reads the
newest constants, which its parameters can't repeat later. It connects to the database on the first
request.

For a production campaign, give one tag (`-Pccdb:tag=calib_2026_pass1`): every job of the campaign
then reads the same constants, whatever calibrators add while it runs, and the campaign can be repeated
later. [Tags](concepts/tags.md) describes how to create one with `ccdb tag`.

## Read constants in a factory

`GetConstants<T>(run, request)` returns the constants of a table for a run, as
`Calibration::GetCalib` of the [C++ API](apis/cpp.md) gives them, under the job's variation and time
or its tag. A factory reads them in `ChangeRun()`, which JANA2 calls when the run changes, and hands the
values to its algorithm; `Process()` (`Execute()` in a JANA2 omnifactory) only uses them:

```cpp
#include <JANA/Components/JOmniFactory.h>
#include "CCDB_service.h"

class GainCalibration_factory : public JOmniFactory<GainCalibration_factory, GainCalibrationConfig> {
    Input<RawHit> m_raw_hits_input{this};
    jana::components::Output<CalibratedHit> m_calibrated_hits_output{this};
    ParameterRef<std::string> m_table{this, "table", config().table};
    Service<CCDB_service> m_ccdb{this};
    GainCalibration m_algo;

public:
    void Configure() { m_algo.applyConfig(config()); }

    void ChangeRun(int32_t run_number) override {
        // one row per channel: columns gain, offset, channel
        auto rows = m_ccdb->GetConstants<std::vector<std::map<std::string, double>>>(run_number, config().table);
        for (const auto& row: rows) {
            int channel = static_cast<int>(row.at("channel"));
            config().gains[channel] = row.at("gain");
            config().offsets[channel] = row.at("offset");
        }
        m_algo.applyConfig(config());
    }

    void Execute(int32_t, uint64_t) { m_algo.process(m_raw_hits_input(), m_calibrated_hits_output()); }
};
```

The complete example, with its algorithm and plugin, is in `jana2/examples/`.

The type `T` chooses the form of the result:

| `T` | result |
|---|---|
| `std::vector<std::vector<double>>` (or `int`, `std::string`) | rows of columns |
| `std::vector<std::map<std::string, double>>` (or `int`, `std::string`) | rows, each by column name |
| `std::map<std::string, double>`, `std::vector<double>` (and the `int`, `std::string` forms) | the one row of a one-row table |
| `double`, `int`, `std::string` | the first value of a one-row table |

The request is a CCDB request and may name its own run, variation or time
(`/calorimeter/gains:1000:mc`), as with `GetCalib`; under a tag a request that names a variation or a
time is an error, and one that names another tag (`@NAME`) reads that tag. A table that does not exist, or has no constants for the run, raises a `JException`
that names the request and the run.

The service keeps one `ccdb::Calibration` per run and is thread safe, so factories in all worker threads
share it. `GetCalibration(run)` returns that object for code that wants the C++ API itself. With
`ccdb:tag` set, that Calibration reads every request through the tag (`Calibration::SetTag`), as
`GetConstants` does.

## Files from a resources table

Files that are too large for a table, such as ONNX model weights or field maps, stay on a file system,
CVMFS or a web server; a CCDB table records where they are. `GetResource(run, table)` reads a one-row
table with the columns `url`, `sha256` and `size`, fetches the file into `ccdb:cache_dir`, checks its
size and SHA-256, and returns the local path:

```cpp
std::string weights = m_ccdb->GetResource(run_number, "/tracking/ml/seed_model");
```

The file is fetched once: it lands in `<cache_dir>/<sha256>/<file name>`, and jobs that share the cache
directory share the file. A cached file is checked against the hash once per job and fetched again if it
differs. A file whose size or hash differs from the table is not kept and is an error. The `url` is a
`file://` URL or an absolute path, which is copied, or an `http://` or `https://` URL, which is
downloaded with the libcurl of the CCDB library (built with `CCDB_WITH_HTTP`, the default when CMake
finds libcurl; a library without it reports that clearly). `CCDB_HTTP_TIMEOUT` bounds one download in
seconds (default 300), as for the [HTTP API connection](apis/cpp.md#http-api). The download goes to a
temporary name next to the target and is checked before it is moved into place, so a job that shares
the cache never reads half a file.

To make a resources table, create it with three columns and add one row per run range:

```bash
ccdb mktbl /tracking/ml/seed_model -r 1 url=string sha256=string size=int "#seed finder weights"
ccdb add /tracking/ml/seed_model -r 1000-1999 seed_model.txt
```

## What a job used

A job's constants follow from its run, its variation and its time or tag; the library resolves each request
to one version of one table. With `ccdb:provenance=PATH` the service records those resolutions and writes
them to `PATH` when it ends, so an output file can be matched to its constants years later without the
launch configuration:

```bash
jana -Pplugins=CCDB_service,myplugin -Pccdb:url=https://ccdb.example.org/api/v1 -Pccdb:tag=ver03 \
     -Pccdb:provenance=run_031000.ccdb.json run_031000.evio
```

```json
{
 "ccdb_version": "2.5.0",
 "connection": "https://ccdb.example.org/api/v1",
 "variation": "",
 "time": "",
 "tag": "ver03",
 "generated": "2026-11-03T19:02:11.483120Z",
 "resolved": [
  {"request": "/FCAL/gains", "path": "/FCAL/gains", "run": 31000, "variation": "", "time": "", "tag": "ver03", "assignment_id": 812211, "sha256": "55d35b501c1a…"},
  {"request": "/BCAL/timing_offsets", "path": "/BCAL/timing_offsets", "run": 31000, "variation": "", "time": "", "tag": "ver03", "assignment_id": 815004, "sha256": "b2ceb52d6aa9…"}
 ]
}
```

The record holds, per run, every distinct resolution in the order the job first made it: a table read for
every event is one entry. Each entry names the table, the run, the variation and time or the tag it resolved
under, the version id, and the SHA-256 of the data the job received. The file is written whole and then
renamed, so a reader never sees half of it; a processor that wants it earlier calls `WriteUsageRecord()`
from its `Finish()`.

`ccdb provenance FILE` checks every entry against a database and names the tags that give the same
constants ([CLI](cli.md#what-a-job-used)). The script that submits the job (a launch script, MCwrapper) can
attach the file to the job's output as metadata.

Without the parameter the service records nothing. The same record is available in code:
`EnableUsageRecord(true)` and `GetResolvedAssignments()` in the [C++ library](apis/cpp.md#what-a-job-resolved),
`usage_record_enabled` and `resolved_assignments` in [Python](apis/python.md#what-a-program-resolved).

## Use the service in EICrecon

1. Build and install CCDB with `-DCCDB_BUILD_JANA2=ON` in the same environment as EICrecon, so both
   use the same JANA2.
2. In the CMake file of the plugin whose factories read constants, find the component and link its
   target with EICrecon's plugin macros:

   ```cmake
   find_package(ccdb 2.5 CONFIG REQUIRED COMPONENTS jana2)
   plugin_link_libraries(${PLUGIN_NAME} ccdb::ccdb_jana2)
   ```

   Configure EICrecon with `-DCMAKE_PREFIX_PATH=$HOME/ccdb`. A project that builds CCDB in its own tree
   sets the option and adds the directory instead:

   ```cmake
   set(CCDB_BUILD_JANA2 ON)
   set(CCDB_BUILD_TESTS OFF)
   add_subdirectory(path/to/ccdb/cpp ccdb)
   plugin_link_libraries(${PLUGIN_NAME} ccdb::ccdb_jana2)
   ```

3. In the factory, declare `Service<CCDB_service> m_ccdb{this};` and read the tables in `ChangeRun()`,
   as above.
4. Run with the plugin loaded: `eicrecon -Pplugins=CCDB_service -Pccdb:url=... -Pccdb:tag=...`.

## JANA's own calibration classes

JANA ships `JCalibrationCCDB`, which reads CCDB through JANA's calibration manager with the variables
`JANA_CALIB_URL` and `JANA_CALIB_CONTEXT`. That path is part of JANA, not of this service. `CCDB_service` reads `JANA_CALIB_URL` when `CCDB_CONNECTION` is not set, so a job
set up for JANA's calibration system finds the same database.
