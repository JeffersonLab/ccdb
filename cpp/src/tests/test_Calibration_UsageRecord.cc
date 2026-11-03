// Calibration::EnableUsageRecord and GetResolvedAssignments: the record of which assignment each request resolved
// to (docs/apis/cpp.md, "What a job resolved"), on the database of scripts/time/make_time_db.py
// (testdata/time/resolution.tsv: the newest default value is 105, tag_a gives 101; a value's vault is its text).
//   CCDB_TEST_TIME_SQLITE_CONNECTION  sqlite:///path of a database the script made; required under CI
//   CCDB_TEST_TIME_MYSQL_CONNECTION   the same on MySQL or MariaDB ([mysql])
#include "tests/catch.hpp"

#include "CCDB/Calibration.h"
#include "CCDB/CalibrationGenerator.h"
#include "CCDB/Helpers/Sha256.h"
#include "CCDB/Helpers/TimeUtils.h"

#include <cstdlib>
#include <memory>
#include <string>
#include <vector>

using namespace std;
using namespace ccdb;

namespace {

    const char* TABLE = "/test/time/values";

    int Value(Calibration* calib, const string& request) {
        vector<vector<int>> rows;
        REQUIRE(calib->GetCalib(rows, request));
        return rows.at(0).at(0);
    }

    void CheckUsageRecord(const string& connection, bool cache) {
        INFO("cache " << (cache ? "on" : "off"));
        unique_ptr<Calibration> calib(CalibrationGenerator::CreateCalibration(connection, 100, "default"));
        calib->EnableCache(cache);

        // off by default: nothing is recorded
        REQUIRE_FALSE(calib->IsUsageRecordEnabled());
        REQUIRE(Value(calib.get(), TABLE) == 105);
        REQUIRE(calib->GetResolvedAssignments().empty());

        calib->EnableUsageRecord(true);
        REQUIRE(calib->IsUsageRecordEnabled());
        for (int event = 0; event < 3; event++) {
            REQUIRE(Value(calib.get(), TABLE) == 105);                       // a table read per event: one entry
        }
        REQUIRE(Value(calib.get(), string(TABLE) + ":100@tag_a") == 101);
        REQUIRE(Value(calib.get(), string(TABLE) + "@tag_a") == 101);       // the same resolution spelled otherwise
        // a request time is local wall time: the whole of 2 March 2024 covers 104 in any zone, and not 105
        REQUIRE(Value(calib.get(), string(TABLE) + ":100:default:2024-03-02") == 104);

        vector<ResolvedAssignment> record = calib->GetResolvedAssignments();
        REQUIRE(record.size() == 3);

        REQUIRE(record[0].request == TABLE);
        REQUIRE(record[0].path == TABLE);
        REQUIRE(record[0].run == 100);
        REQUIRE(record[0].variation == "default");
        REQUIRE(record[0].timeMicro == 0);
        REQUIRE(record[0].tag.empty());
        REQUIRE(record[0].assignmentId > 0);
        REQUIRE(record[0].sha256 == Sha256::Of("105"));

        REQUIRE(record[1].request == string(TABLE) + ":100@tag_a");
        REQUIRE(record[1].tag == "tag_a");
        REQUIRE(record[1].variation.empty());
        REQUIRE(record[1].timeMicro == 0);
        REQUIRE(record[1].sha256 == Sha256::Of("101"));

        REQUIRE(record[2].tag.empty());
        REQUIRE(record[2].variation == "default");
        REQUIRE(record[2].timeMicro > 0);
        REQUIRE(record[2].sha256 == Sha256::Of("104"));
        REQUIRE(record[0].assignmentId != record[1].assignmentId);
        REQUIRE(record[1].assignmentId != record[2].assignmentId);

        // off again: the entries stay and nothing is added; Clear forgets them
        calib->EnableUsageRecord(false);
        REQUIRE(Value(calib.get(), string(TABLE) + ":100@tag_b") == 103);
        REQUIRE(calib->GetResolvedAssignments().size() == 3);
        calib->ClearResolvedAssignments();
        REQUIRE(calib->GetResolvedAssignments().empty());
    }

    const char* ConnectionOrSkip(const char* variable, bool requiredUnderCi) {
        const char* connection = getenv(variable);
        if (!connection) {
            if (requiredUnderCi && getenv("CI")) {
                FAIL(string(variable) + " is not set. Under CI it is required: run scripts/time/make_time_db.py");
            }
            WARN(string(variable) + " is not set: the usage record test is skipped");
        }
        return connection;
    }
}


TEST_CASE("Calibration/usage record, SQLite", "[usage]")
{
    const char* connection = ConnectionOrSkip("CCDB_TEST_TIME_SQLITE_CONNECTION", true);
    if (!connection) return;
    CheckUsageRecord(connection, true);
    CheckUsageRecord(connection, false);
}


#ifdef CCDB_MYSQL
TEST_CASE("Calibration/usage record, MySQL", "[usage][mysql]")
{
    const char* connection = ConnectionOrSkip("CCDB_TEST_TIME_MYSQL_CONNECTION", false);
    if (!connection) return;
    CheckUsageRecord(connection, true);
    CheckUsageRecord(connection, false);
}
#endif
