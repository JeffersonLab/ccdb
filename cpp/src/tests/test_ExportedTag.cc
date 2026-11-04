// A tag exported by `ccdb export tag` (python/ccdb/tag_export.py) is a CCDB database the C++ library opens like any
// other: tag_b of the database of scripts/time/make_time_db.py gives 103, through the tag and as the newest value of
// the file, whose only assignments are those the tag sees.
//   CCDB_TEST_EXPORT_SQLITE  the path of tag_b.sqlite from `ccdb -c <time database> export tag @tag_b -o DIR`;
//                            required under CI
#include "tests/catch.hpp"

#include "CCDB/Calibration.h"
#include "CCDB/CalibrationGenerator.h"

#include <cstdlib>
#include <memory>
#include <string>
#include <vector>

using namespace std;
using namespace ccdb;

TEST_CASE("Exported tag/opened by the C++ library", "[export]")
{
    const char* path = getenv("CCDB_TEST_EXPORT_SQLITE");
    if (!path) {
        if (getenv("CI")) FAIL("CCDB_TEST_EXPORT_SQLITE is not set. Under CI it is required: export tag_b of the time database");
        WARN("CCDB_TEST_EXPORT_SQLITE is not set: the exported tag test is skipped");
        return;
    }
    unique_ptr<Calibration> calib(CalibrationGenerator::CreateCalibration(string("sqlite:///") + path, 100, "default"));
    vector<vector<int>> rows;
    REQUIRE(calib->GetCalib(rows, "/test/time/values@tag_b"));
    REQUIRE(rows.at(0).at(0) == 103);
    REQUIRE(calib->GetCalib(rows, "/test/time/values:5000@tag_b"));    // every run
    REQUIRE(rows.at(0).at(0) == 103);
    REQUIRE(calib->GetCalib(rows, "/test/time/values"));               // the newest the file holds is the tag's
    REQUIRE(rows.at(0).at(0) == 103);
}
