// The HTTP provider (CCDB/Providers/HTTPDataProvider.h): constants read through the API's run bundle equal those read
// from the database file directly, by time and by tag, on the database of scripts/time/make_time_db.py
// (testdata/time/resolution.tsv). cpp/src/tests/http_harness.py starts the API and runs them; without its settings
// (CCDB_TEST_HTTP_URL) they are skipped. Hidden, so a plain ccdb_tests run lists them apart.
//   [http]        the API is running:
//                 CCDB_TEST_HTTP_URL        the API on the time database, http://127.0.0.1:<port>/api/v1
//                 CCDB_TEST_HTTP_BAD_URL    the same API with a wrong X-CCDB-SHA256 header
//                 CCDB_TEST_TIME_SQLITE_CONNECTION  the time database itself
//                 CCDB_HTTP_CACHE_DIR       the cache directory, shared with the [http_cache] run
//   [http_cache]  the API is stopped: the bundles the [http] run left in the cache are read again
#include "tests/catch.hpp"

#include "CCDB/Calibration.h"
#include "CCDB/CalibrationGenerator.h"
#include "CCDB/Helpers/TimeUtils.h"
#include "CCDB/Providers/HTTPDataProvider.h"

#include <cstdlib>
#include <dirent.h>
#include <sys/stat.h>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>

using namespace std;
using namespace ccdb;

namespace {

    const char* TABLE = "/test/time/values";
    const int RUN = 100;

    string Setting(const char* name) {
        const char* value = getenv(name);
        if (!value) FAIL(string(name) + " is not set; run these tests through cpp/src/tests/http_harness.py");
        return value;
    }

    /// False, with a warning, when the harness did not start the API
    bool HarnessRunning() {
        if (getenv("CCDB_TEST_HTTP_URL")) return true;
        WARN("CCDB_TEST_HTTP_URL is not set: the HTTP provider test is skipped (cpp/src/tests/http_harness.py runs it)");
        return false;
    }

    int64_t Utc(const string& text) {
        int64_t micro = 0;
        REQUIRE(TimeUtils::ParseUtc(text, micro));
        return micro;
    }

    /// The table's value for the calibration's run, or -1 when no assignment resolves
    int Value(Calibration* calib) {
        try {
            vector<vector<int>> rows;
            if (!calib->GetCalib(rows, TABLE) || rows.empty() || rows[0].empty()) return -1;
            return rows[0][0];
        }
        catch (std::exception&) {
            return -1;
        }
    }

    /// The message of the exception that making a calibration throws, "" when it does not throw
    template <typename Make> string Failure(Make make) {
        try {
            unique_ptr<Calibration> calib(make());
        }
        catch (std::exception& error) {
            return error.what();
        }
        return "";
    }

    /// Files of a directory whose names end with suffix
    vector<string> Files(const string& directory, const string& suffix) {
        vector<string> names;
        DIR* listing = opendir(directory.c_str());
        if (!listing) return names;
        while (dirent* entry = readdir(listing)) {
            string name = entry->d_name;
            if (name.size() >= suffix.size() && name.compare(name.size() - suffix.size(), suffix.size(), suffix) == 0) {
                names.push_back(name);
            }
        }
        closedir(listing);
        return names;
    }

    /// Sets CCDB_HTTP_CACHE_DIR for one scope
    struct CacheDir {
        string saved;
        explicit CacheDir(const string& path): saved(Setting("CCDB_HTTP_CACHE_DIR")) { setenv("CCDB_HTTP_CACHE_DIR", path.c_str(), 1); }
        ~CacheDir() { setenv("CCDB_HTTP_CACHE_DIR", saved.c_str(), 1); }
    };

    struct TimeCase { const char* variation; const char* time; int expected; };

    // Each limit of testdata/time/resolution.tsv around the assignments of run 100; "" is the newest
    const TimeCase TIME_CASES[] = {
        {"default", "2024-03-01 12:00:00.099999", -1},
        {"default", "2024-03-01 12:00:00.100000", 101},
        {"default", "2024-03-01 12:00:00.599999", 101},
        {"default", "2024-03-01 12:00:00.600000", 103},
        {"default", "2024-03-01 12:00:01.000000", 104},
        {"default", "2024-07-01 00:00:00.000000", 105},
        {"default", "", 105},
        {"child", "2024-03-01 12:00:00.299999", 101},
        {"child", "2024-03-01 12:00:00.300000", 201},
    };

    const char* TAGS[] = {"tag_a", "tag_b", "tag_c", "tag_d", "tag_e"};
}


TEST_CASE("HTTP provider/by time, equal to the database file", "[.][http]")
{
    if (!HarnessRunning()) return;
    string url = Setting("CCDB_TEST_HTTP_URL");
    string file = Setting("CCDB_TEST_TIME_SQLITE_CONNECTION");
    for (const TimeCase& each : TIME_CASES) {
        INFO("variation " << each.variation << ", time '" << each.time << "'");
        int64_t time = *each.time ? Utc(each.time) : 0;
        unique_ptr<Calibration> http(CalibrationGenerator::CreateCalibrationMicro(url, RUN, each.variation, time));
        unique_ptr<Calibration> direct(CalibrationGenerator::CreateCalibrationMicro(file, RUN, each.variation, time));
        REQUIRE(Value(http.get()) == each.expected);
        REQUIRE(Value(direct.get()) == each.expected);

        HTTPDataProvider* provider = dynamic_cast<HTTPDataProvider*>(http->GetProvider());
        REQUIRE(provider != nullptr);
        REQUIRE(provider->GetConnectionString() == url);
        REQUIRE(provider->GetBundlePath().find(Setting("CCDB_HTTP_CACHE_DIR")) == 0);
        if (!*each.time) {
            // the newest: the server's redirect names the newest creation time, and so does the cached file
            REQUIRE(provider->GetBundlePath().find("run100_default_20240701T000000000000Z.sqlite") != string::npos);
        }
    }

    // the newest again: the server's redirect names a bundle that is in the cache, which is not downloaded again
    // (a download would replace the file, and with it its inode)
    unique_ptr<Calibration> first(CalibrationGenerator::CreateCalibrationMicro(url, RUN, "default", 0));
    string path = dynamic_cast<HTTPDataProvider*>(first->GetProvider())->GetBundlePath();
    struct stat before, after;
    REQUIRE(stat(path.c_str(), &before) == 0);
    unique_ptr<Calibration> second(CalibrationGenerator::CreateCalibrationMicro(url, RUN, "default", 0));
    REQUIRE(dynamic_cast<HTTPDataProvider*>(second->GetProvider())->GetBundlePath() == path);
    REQUIRE(stat(path.c_str(), &after) == 0);
    REQUIRE(before.st_ino == after.st_ino);
    REQUIRE(Value(second.get()) == 105);
}


TEST_CASE("HTTP provider/by tag, equal to the database file", "[.][http]")
{
    if (!HarnessRunning()) return;
    string url = Setting("CCDB_TEST_HTTP_URL");
    string file = Setting("CCDB_TEST_TIME_SQLITE_CONNECTION");
    CalibrationGenerator generator;
    for (const char* tag : TAGS) {
        INFO("tag " << tag);
        Calibration* http = generator.MakeCalibrationForTag(url, RUN, tag);
        Calibration* direct = generator.MakeCalibrationForTag(file, RUN, tag);
        REQUIRE(Value(http) == Value(direct));
        REQUIRE(http->GetDefaultTag() == tag);
        REQUIRE(http->GetDefaultVariation() == direct->GetDefaultVariation());
        REQUIRE(http->GetDefaultTimeMicro() == direct->GetDefaultTimeMicro());
        REQUIRE(generator.MakeCalibrationForTag(url, RUN, tag) == http);
    }
    REQUIRE(Value(generator.MakeCalibrationForTag(url, RUN, "tag_b")) == 103);
    REQUIRE(Value(generator.MakeCalibrationForTag(url, RUN, "tag_e")) == 201);
    generator.DeleteCalibrations();
}


TEST_CASE("HTTP provider/failures", "[.][http]")
{
    if (!HarnessRunning()) return;
    string cache = Setting("CCDB_HTTP_CACHE_DIR");
    int64_t time = Utc("2024-03-01 12:00:00.600000");

    SECTION("a wrong SHA-256 is rejected and nothing is kept") {
        string directory = cache + "/bad_hash";
        CacheDir scope(directory);
        string url = Setting("CCDB_TEST_HTTP_BAD_URL");
        string message = Failure([&]() { return CalibrationGenerator::CreateCalibrationMicro(url, RUN, "default", time); });
        REQUIRE(message.find("SHA-256 mismatch") != string::npos);
        string server = url.substr(url.find("://") + 3);
        for (size_t i = 0; i < server.size(); i++) if (server[i] == ':') server.replace(i, 1, "+3A");
        for (size_t i = 0; i < server.size(); i++) if (server[i] == '/') server.replace(i, 1, "+2F");
        REQUIRE(Files(directory + "/" + server, "").size() == 2);      // . and .., no bundle, no partial file
    }

    SECTION("no server and no cached bundle") {
        CacheDir scope(cache + "/no_server");
        string message = Failure([&]() { return CalibrationGenerator::CreateCalibrationMicro("http://127.0.0.1:1/api/v1", RUN, "default", time); });
        REQUIRE(message.find("cannot get the run bundle") != string::npos);
    }

    SECTION("a cache directory that cannot be written") {
        CacheDir scope("/proc/ccdb_cache");
        string message = Failure([&]() { return CalibrationGenerator::CreateCalibrationMicro(Setting("CCDB_TEST_HTTP_URL"), RUN, "default", time); });
        REQUIRE(message.find("CCDB_HTTP_CACHE_DIR") != string::npos);
    }

    SECTION("an unknown tag and an unknown variation") {
        CalibrationGenerator generator;
        string url = Setting("CCDB_TEST_HTTP_URL");
        string message = Failure([&]() { return generator.MakeCalibrationForTag(url, RUN, "no_such_tag"); });
        REQUIRE(message.find("404") != string::npos);
        message = Failure([&]() { return CalibrationGenerator::CreateCalibrationMicro(url, RUN, "no_such_variation", time); });
        REQUIRE(message.find("404") != string::npos);
    }
}


TEST_CASE("HTTP provider/the server stopped, bundles from the cache", "[.][http_cache]")
{
    if (!HarnessRunning()) return;
    string url = Setting("CCDB_TEST_HTTP_URL");
    for (const TimeCase& each : TIME_CASES) {
        if (!*each.time) continue;
        INFO("variation " << each.variation << ", time '" << each.time << "'");
        unique_ptr<Calibration> http(CalibrationGenerator::CreateCalibrationMicro(url, RUN, each.variation, Utc(each.time)));
        REQUIRE(Value(http.get()) == each.expected);
    }

    CalibrationGenerator generator;
    REQUIRE(Value(generator.MakeCalibrationForTag(url, RUN, "tag_b")) == 103);
    REQUIRE(Value(generator.MakeCalibrationForTag(url, RUN, "tag_e")) == 201);
    generator.DeleteCalibrations();

    // the newest constants are whatever the server says now
    string message = Failure([&]() { return CalibrationGenerator::CreateCalibrationMicro(url, RUN, "default", 0); });
    REQUIRE(message.find("The newest constants need the server") != string::npos);
}
