// The time parser of the schema 6 time model (docs/concepts/time.md) against testdata/time/parse_cases.tsv,
// the case table Python's unit_test_time_parse.py runs too: both languages must give the same UTC instant
// for every input and zone, or both must refuse it.
#include "tests/catch.hpp"

#include "CCDB/Helpers/PathUtils.h"
#include "CCDB/Helpers/TimeUtils.h"

#include <cstdlib>
#include <fstream>
#include <string>
#include <vector>

using namespace std;
using namespace ccdb;

namespace {

    struct ParseCase {
        string zone;
        string input;
        string expected;
    };

    vector<ParseCase> ReadParseCases() {
        ifstream file(string(CCDB_TESTDATA_DIR) + "/time/parse_cases.tsv");
        REQUIRE(file.good());
        vector<ParseCase> cases;
        string line;
        while (getline(file, line)) {
            if (line.empty() || line[0] == '#') continue;
            size_t first = line.find('\t');
            size_t second = line.find('\t', first + 1);
            cases.push_back({line.substr(0, first), line.substr(first + 1, second - first - 1), line.substr(second + 1)});
        }
        return cases;
    }

    /// Sets TZ for the process and restores it when the test ends
    class ZoneGuard {
    public:
        ZoneGuard() {
            const char* saved = getenv("TZ");
            mHadZone = saved != nullptr;
            if (mHadZone) mSaved = saved;
        }
        ~ZoneGuard() {
            if (mHadZone) setenv("TZ", mSaved.c_str(), 1); else unsetenv("TZ");
            tzset();
        }
        void Set(const string& zone) {
            setenv("TZ", zone.c_str(), 1);
            tzset();
        }
    private:
        bool mHadZone;
        string mSaved;
    };
}


TEST_CASE("Time/parse cases shared with Python", "[time]")
{
    ZoneGuard zone;
    vector<ParseCase> cases = ReadParseCases();
    REQUIRE(cases.size() > 50);
    for (const ParseCase& each: cases) {
        zone.Set(each.zone);
        bool success = false;
        int64_t micro = TimeUtils::ParseLocalTime(each.input, &success);
        string got = success ? TimeUtils::FormatUtc(micro) : "ERROR";
        INFO("zone " << each.zone << ", input '" << each.input << "'");
        CHECK(got == each.expected);
    }
}


TEST_CASE("Time/ParseTime keeps its signature and gives the whole second", "[time]")
{
    ZoneGuard zone;
    zone.Set("UTC");
    bool success = false;

    // F27: partial months end on the last day of the month
    time_t april = PathUtils::ParseTime("2024-04", &success);
    REQUIRE(success);
    REQUIRE(TimeUtils::FormatUtc(april * TimeUtils::MicrosecondsPerSecond) == "2024-04-30 23:59:59.000000");
    time_t february = PathUtils::ParseTime("2024-02", &success);
    REQUIRE(TimeUtils::FormatUtc(february * TimeUtils::MicrosecondsPerSecond) == "2024-02-29 23:59:59.000000");

    // a fraction is parsed, ParseTime keeps the second
    time_t withFraction = PathUtils::ParseTime("2024-03-01 12:30:15.5", &success);
    REQUIRE(success);
    REQUIRE(TimeUtils::FormatUtc(withFraction * TimeUtils::MicrosecondsPerSecond) == "2024-03-01 12:30:15.000000");

    PathUtils::ParseTime("2024-02-30", &success);
    REQUIRE_FALSE(success);
}


TEST_CASE("Time/requests and contexts carry microseconds", "[time]")
{
    ZoneGuard zone;
    zone.Set("UTC");

    RequestParseResult request = PathUtils::ParseRequest("/test/table:100:default:2024-03-01 12:30:15.25");
    REQUIRE(request.WasParsedTime);
    REQUIRE(TimeUtils::FormatUtc(request.TimeMicro) == "2024-03-01 12:30:15.259999");
    REQUIRE(request.Time == TimeUtils::ToSeconds(request.TimeMicro));

    ContextParseResult context = PathUtils::ParseContext("variation=default calibtime=2024-02");
    REQUIRE(context.ConstantsTimeIsParsed);
    REQUIRE(TimeUtils::FormatUtc(context.ConstantsTimeMicro) == "2024-02-29 23:59:59.999999");
}


TEST_CASE("Time/whole seconds and stored text", "[time]")
{
    // 0 is "no time limit" in both forms
    REQUIRE(TimeUtils::EndOfSecond(0) == 0);
    REQUIRE(TimeUtils::EndOfSecond(1709296215) == 1709296215999999LL);
    REQUIRE(TimeUtils::ToSeconds(1709296215999999LL) == 1709296215);
    REQUIRE(TimeUtils::ToSeconds(-1) == -1);

    int64_t micro = 0;
    REQUIRE(TimeUtils::ParseUtc("2024-03-01 12:30:15.250000", micro));
    REQUIRE(TimeUtils::FormatUtc(micro) == "2024-03-01 12:30:15.250000");
    REQUIRE(TimeUtils::ParseUtc("2024-03-01 12:30:15", micro));
    REQUIRE(TimeUtils::FormatUtc(micro) == "2024-03-01 12:30:15.000000");
    REQUIRE(TimeUtils::ParseUtc("2024-03-01 12:30:15.5", micro));
    REQUIRE(TimeUtils::FormatUtc(micro) == "2024-03-01 12:30:15.500000");
    REQUIRE_FALSE(TimeUtils::ParseUtc("yesterday", micro));
}
