// Calibration::SetTag and CalibrationGenerator::MakeCalibrationForTag: a Calibration that reads every request
// through a tag (docs/concepts/tags.md), on the database of scripts/time/make_time_db.py (testdata/time/resolution.tsv:
// tag_b at 12:00:00.600000 gives value 103, tag_a gives 101, tag_e of variation child gives 201).
//   CCDB_TEST_TIME_SQLITE_CONNECTION  sqlite:///path of a database the script made; required under CI
//   CCDB_TEST_TIME_MYSQL_CONNECTION   the same on MySQL or MariaDB ([mysql])
#include "tests/catch.hpp"

#include "CCDB/Calibration.h"
#include "CCDB/CalibrationGenerator.h"
#include "CCDB/Helpers/PathUtils.h"
#include "CCDB/Helpers/TimeUtils.h"

#include <cstdlib>
#include <memory>
#include <stdexcept>
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

    void CheckSetTag(const string& connection) {
        unique_ptr<Calibration> calib(CalibrationGenerator::CreateCalibration(connection));
        REQUIRE(calib->GetDefaultTag().empty());
        REQUIRE(Value(calib.get(), TABLE) == 105);          // the newest, before any tag

        calib->SetTag("tag_b");
        REQUIRE(calib->GetDefaultTag() == "tag_b");
        REQUIRE(calib->GetDefaultVariation() == "default");
        REQUIRE(TimeUtils::FormatUtc(calib->GetDefaultTimeMicro()) == "2024-03-01 12:00:00.600000");
        REQUIRE(Value(calib.get(), TABLE) == 103);
        REQUIRE(Value(calib.get(), string(TABLE) + ":100") == 103);

        // another tag in the request reads that tag
        REQUIRE(Value(calib.get(), string(TABLE) + ":100@tag_a") == 101);

        // a variation or a time would mix the tag with other constants
        vector<vector<int>> rows;
        REQUIRE_THROWS_AS(calib->GetCalib(rows, string(TABLE) + ":100:default"), std::invalid_argument);
        REQUIRE_THROWS_AS(calib->GetCalib(rows, string(TABLE) + ":100::2024"), std::invalid_argument);

        // the tag's variation, with the fallback to its parent
        calib->SetTag("tag_e");
        REQUIRE(calib->GetDefaultVariation() == "child");
        REQUIRE(Value(calib.get(), TABLE) == 201);
        calib->SetTag("tag_c");
        REQUIRE(Value(calib.get(), TABLE) == 101);

        // a wrong name fails at once and changes nothing
        REQUIRE_THROWS_AS(calib->SetTag("no_such_tag"), std::runtime_error);
        REQUIRE(calib->GetDefaultTag() == "tag_c");
        REQUIRE_THROWS(calib->SetTag("bad-name"));
    }

    void CheckGenerator(const string& connection) {
        CalibrationGenerator generator;
        Calibration* tagged = generator.MakeCalibrationForTag(connection, 100, "tag_b");
        REQUIRE(tagged->GetDefaultTag() == "tag_b");
        REQUIRE(Value(tagged, TABLE) == 103);
        REQUIRE(generator.MakeCalibrationForTag(connection, 100, "tag_b") == tagged);
        Calibration* untagged = generator.MakeCalibrationMicro(connection, 100, "default", 0);
        REQUIRE(untagged != tagged);
        REQUIRE(Value(untagged, TABLE) == 105);
        REQUIRE(generator.MakeCalibrationForTag(connection, 100, "tag_a") != tagged);
        REQUIRE_THROWS(generator.MakeCalibrationForTag(connection, 100, "no_such_tag"));
        generator.DeleteCalibrations();
    }

    const char* ConnectionOrSkip(const char* variable, bool requiredUnderCi) {
        const char* connection = getenv(variable);
        if (!connection) {
            if (requiredUnderCi && getenv("CI")) {
                FAIL(string(variable) + " is not set. Under CI it is required: run scripts/time/make_time_db.py");
            }
            WARN(string(variable) + " is not set: the SetTag test is skipped");
        }
        return connection;
    }
}


TEST_CASE("Calibration/SetTag, SQLite", "[tags]")
{
    const char* connection = ConnectionOrSkip("CCDB_TEST_TIME_SQLITE_CONNECTION", true);
    if (!connection) return;
    CheckSetTag(connection);
    CheckGenerator(connection);
}


#ifdef CCDB_MYSQL
TEST_CASE("Calibration/SetTag, MySQL", "[tags][mysql]")
{
    const char* connection = ConnectionOrSkip("CCDB_TEST_TIME_MYSQL_CONNECTION", false);
    if (!connection) return;
    CheckSetTag(connection);
    CheckGenerator(connection);
}
#endif


TEST_CASE("Calibration/tag in a context string", "[tags]")
{
    ContextParseResult context = PathUtils::ParseContext("tag=pass1 run=100");
    REQUIRE(context.TagIsParsed);
    REQUIRE(context.Tag == "pass1");
    REQUIRE(context.RunNumber == 100);
    REQUIRE_FALSE(PathUtils::ParseContext("variation=mc").TagIsParsed);
    REQUIRE_THROWS_AS(PathUtils::ParseContext("tag=pass1 variation=mc"), std::invalid_argument);
    REQUIRE_THROWS_AS(PathUtils::ParseContext("calibtime=2024 tag=pass1"), std::invalid_argument);
    REQUIRE_THROWS_AS(PathUtils::ParseContext("tag=bad-name"), std::invalid_argument);
}
