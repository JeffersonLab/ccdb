// MySQL, MariaDB and SQLite resolve times alike, to the microsecond, in the C++ library as in Python
// (docs/concepts/time.md). The database comes from scripts/time/make_time_db.py, which writes the data of
// testdata/time/resolution.tsv; every query of that file must give its expected value in the zone the file names.
//   CCDB_TEST_TIME_SQLITE_CONNECTION  sqlite:///path of a database the script made; required under CI
//   CCDB_TEST_TIME_MYSQL_CONNECTION   the same on MySQL or MariaDB ([mysql])
#include "tests/catch.hpp"

#include "CCDB/Calibration.h"
#include "CCDB/CalibrationGenerator.h"

#include <cstdlib>
#include <fstream>
#include <memory>
#include <string>
#include <vector>

using namespace std;
using namespace ccdb;

namespace {

    struct TimeQuery {
        string zone;
        string request;
        bool expectNone;
        int expected;
    };

    vector<TimeQuery> ReadQueries() {
        ifstream file(string(CCDB_TESTDATA_DIR) + "/time/resolution.tsv");
        REQUIRE(file.good());
        vector<TimeQuery> queries;
        string line;
        while (getline(file, line)) {
            if (line.compare(0, 6, "query\t") != 0) continue;
            vector<string> fields;
            size_t start = 6, tab;
            while ((tab = line.find('\t', start)) != string::npos) {
                fields.push_back(line.substr(start, tab - start));
                start = tab + 1;
            }
            fields.push_back(line.substr(start));
            REQUIRE(fields.size() == 3);
            bool none = fields[2] == "NONE";
            queries.push_back({fields[0], fields[1], none, none ? 0 : atoi(fields[2].c_str())});
        }
        return queries;
    }

    /// The value a request resolves to, or false when no assignment resolves
    bool Resolve(Calibration* calib, const string& request, int& value) {
        try {
            vector<vector<int>> rows;
            if (!calib->GetCalib(rows, request) || rows.empty() || rows[0].empty()) return false;
            value = rows[0][0];
            return true;
        }
        catch (std::exception&) {
            return false;
        }
    }

    void CheckQueries(const string& connection) {
        const char* savedZone = getenv("TZ");
        string saved = savedZone ? savedZone : "";
        unique_ptr<Calibration> calib(CalibrationGenerator::CreateCalibration(connection));
        vector<TimeQuery> queries = ReadQueries();
        REQUIRE(queries.size() >= 30);
        for (const TimeQuery& query: queries) {
            setenv("TZ", query.zone.c_str(), 1);
            tzset();
            int value = 0;
            bool found = Resolve(calib.get(), query.request, value);
            INFO("zone " << query.zone << ", request '" << query.request << "'");
            if (query.expectNone) {
                CHECK_FALSE(found);
            }
            else {
                CHECK(found);
                CHECK(value == query.expected);
            }
        }
        if (savedZone) setenv("TZ", saved.c_str(), 1); else unsetenv("TZ");
        tzset();
    }
}


TEST_CASE("Time/resolution cases shared with Python, SQLite", "[time]")
{
    const char* connection = getenv("CCDB_TEST_TIME_SQLITE_CONNECTION");
    if (!connection) {
        if (getenv("CI")) {
            FAIL("CCDB_TEST_TIME_SQLITE_CONNECTION is not set. Under CI it is required: run "
                 "scripts/time/make_time_db.py sqlite:///<file> and export CCDB_TEST_TIME_SQLITE_CONNECTION=sqlite:///<file>");
        }
        WARN("CCDB_TEST_TIME_SQLITE_CONNECTION is not set: the time resolution test is skipped");
        return;
    }
    CheckQueries(connection);
}


#ifdef CCDB_MYSQL
TEST_CASE("Time/resolution cases shared with Python, MySQL", "[time][mysql]")
{
    const char* connection = getenv("CCDB_TEST_TIME_MYSQL_CONNECTION");
    if (!connection) {
        WARN("CCDB_TEST_TIME_MYSQL_CONNECTION is not set: the MySQL time resolution test is skipped");
        return;
    }
    CheckQueries(connection);
}
#endif
