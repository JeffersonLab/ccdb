// CCDB_service, the JANA2 service (jana2/src), against the database of scripts/eic/make_jana2_test_db.py.
// Built when -DCCDB_BUILD_JANA2=ON; run with CCDB_TEST_JANA2_SQLITE=<that file> ccdb_tests "[jana2]".
#include "tests/catch.hpp"

#include <JANA/JApplication.h>

#include <CCDB/CalibrationGenerator.h>

#include "CCDB_service.h"

#include <cstdlib>
#include <map>
#include <memory>
#include <string>
#include <thread>
#include <vector>

using namespace std;

namespace {

    string JanaTestConnection() {
        const char* path = getenv("CCDB_TEST_JANA2_SQLITE");
        if (!path) {
            throw runtime_error("CCDB_TEST_JANA2_SQLITE is not set: run scripts/eic/make_jana2_test_db.py and point it at the file");
        }
        return string("sqlite:///") + path;   // SQLAlchemy form: sqlite:////abs/path
    }

    /// The service as a factory sees it: provided to a JApplication with these parameters, after Initialize()
    shared_ptr<CCDB_service> StartService(JApplication& app, const map<string, string>& parameters) {
        app.SetParameterValue("jana:loglevel", "warn");
        for (const auto& parameter: parameters) {
            app.SetParameterValue(parameter.first, parameter.second);
        }
        app.ProvideService(make_shared<CCDB_service>(&app));
        app.Initialize();
        return app.GetService<CCDB_service>();
    }

    /// Restores an environment variable at the end of a test
    class ScopedEnv {
    public:
        ScopedEnv(const char* name, const char* value): mName(name) {
            const char* old = getenv(name);
            mHadValue = old != nullptr;
            if (mHadValue) mOldValue = old;
            if (value) setenv(name, value, 1); else unsetenv(name);
        }
        ~ScopedEnv() {
            if (mHadValue) setenv(mName.c_str(), mOldValue.c_str(), 1); else unsetenv(mName.c_str());
        }
    private:
        string mName;
        string mOldValue;
        bool mHadValue = false;
    };

    // The rows of /test/jana2/gains (gain, offset, channel); see make_jana2_test_db.py
    const vector<vector<double>> GAINS_OLD = {{1.0, 0.1, 1}, {2.0, 0.2, 2}};
    const vector<vector<double>> GAINS_NEW = {{1.5, 0.15, 1}, {2.5, 0.25, 2}};
    const vector<vector<double>> GAINS_RUN200 = {{3.0, 0.3, 1}, {4.0, 0.4, 2}};
}


TEST_CASE("CCDB_service/parameters", "[jana2]")
{
    SECTION("Defaults, with the connection string from CCDB_CONNECTION")
    {
        ScopedEnv connection("CCDB_CONNECTION", JanaTestConnection().c_str());
        ScopedEnv jana_url("JANA_CALIB_URL", "sqlite:///not/this/one.sqlite");
        ScopedEnv cache("XDG_CACHE_HOME", "/tmp/ccdb_jana2_cache_home");
        JApplication app;
        auto service = StartService(app, {});

        REQUIRE(service->GetUrl() == JanaTestConnection());
        REQUIRE(service->GetVariation() == "default");
        REQUIRE(service->GetTimeString().empty());
        REQUIRE(service->GetTag().empty());
        REQUIRE(service->GetCacheDir() == "/tmp/ccdb_jana2_cache_home/ccdb/resources");
        REQUIRE(app.GetParameterValue<string>("ccdb:url") == JanaTestConnection());
    }

    SECTION("JANA_CALIB_URL when CCDB_CONNECTION is not set")
    {
        ScopedEnv connection("CCDB_CONNECTION", nullptr);
        ScopedEnv jana_url("JANA_CALIB_URL", JanaTestConnection().c_str());
        JApplication app;
        REQUIRE(StartService(app, {})->GetUrl() == JanaTestConnection());
    }

    SECTION("ccdb:url wins over the environment")
    {
        ScopedEnv connection("CCDB_CONNECTION", "sqlite:///not/this/one.sqlite");
        JApplication app;
        auto service = StartService(app, {{"ccdb:url", JanaTestConnection()}, {"ccdb:variation", "jana2_child"},
                                          {"ccdb:time", "2022"}, {"ccdb:cache_dir", "/tmp/ccdb_jana2_cache"}});
        REQUIRE(service->GetUrl() == JanaTestConnection());
        REQUIRE(service->GetVariation() == "jana2_child");
        REQUIRE(service->GetTimeString() == "2022");
        REQUIRE(service->GetCacheDir() == "/tmp/ccdb_jana2_cache");
    }

    SECTION("No connection string at all fails when the application starts")
    {
        ScopedEnv connection("CCDB_CONNECTION", nullptr);
        ScopedEnv jana_url("JANA_CALIB_URL", nullptr);
        JApplication app;
        REQUIRE_THROWS_WITH(StartService(app, {}), Catch::Contains("no connection string"));
    }

    SECTION("A time that does not parse fails when the application starts")
    {
        JApplication app;
        REQUIRE_THROWS_WITH(StartService(app, {{"ccdb:url", JanaTestConnection()}, {"ccdb:time", "yesterday"}}),
                            Catch::Contains("can't read ccdb:time"));
    }
}


TEST_CASE("CCDB_service/typed getters return what Calibration::GetCalib returns", "[jana2]")
{
    JApplication app;
    auto service = StartService(app, {{"ccdb:url", JanaTestConnection()}});
    unique_ptr<ccdb::Calibration> direct(ccdb::CalibrationGenerator::CreateCalibration(JanaTestConnection(), 100));

    SECTION("Rows of columns")
    {
        auto gains = service->GetConstants<vector<vector<double>>>(100, "/test/jana2/gains");
        vector<vector<double>> expected;
        REQUIRE(direct->GetCalib(expected, "/test/jana2/gains"));
        REQUIRE(gains == expected);
        REQUIRE(gains == GAINS_NEW);

        auto channels = service->GetConstants<vector<vector<int>>>(100, "/test/jana2/gains");
        REQUIRE(channels[1][2] == 2);
        auto as_text = service->GetConstants<vector<vector<string>>>(100, "/test/jana2/gains");
        REQUIRE(as_text[0][1] == "0.15");
    }

    SECTION("Rows by column name")
    {
        auto rows = service->GetConstants<vector<map<string, double>>>(100, "/test/jana2/gains");
        vector<map<string, double>> expected;
        REQUIRE(direct->GetCalib(expected, "/test/jana2/gains"));
        REQUIRE(rows == expected);
        REQUIRE(rows[1].at("gain") == 2.5);
        REQUIRE(rows[1].at("channel") == 2);
    }

    SECTION("One row and one value")
    {
        auto by_name = service->GetConstants<map<string, double>>(100, "/test/jana2/pedestal");
        REQUIRE(by_name.at("value") == 100);
        auto as_vector = service->GetConstants<vector<double>>(100, "/test/jana2/pedestal");
        REQUIRE(as_vector == vector<double>{100});
        REQUIRE(service->GetConstants<double>(100, "/test/jana2/pedestal") == 100);
        REQUIRE(service->GetConstants<int>(100, "/test/jana2/pedestal") == 100);
        REQUIRE(service->GetConstants<string>(100, "/test/jana2/pedestal") == "100");

        // GetCalib(double&) fills the value but returns false (F25), so only its value is compared
        double expected = 0;
        direct->GetCalib(expected, "/test/jana2/pedestal");
        REQUIRE(service->GetConstants<double>(100, "/test/jana2/pedestal") == expected);
    }

    SECTION("A request may name its own variation and time, as with GetCalib")
    {
        REQUIRE(service->GetConstants<double>(100, "/test/jana2/pedestal::jana2_child") == 200);
        REQUIRE(service->GetConstants<vector<vector<double>>>(100, "/test/jana2/gains:::2022") == GAINS_OLD);
    }
}


TEST_CASE("CCDB_service/one Calibration per run", "[jana2]")
{
    JApplication app;
    auto service = StartService(app, {{"ccdb:url", JanaTestConnection()}});

    ccdb::Calibration* run100 = service->GetCalibration(100);
    REQUIRE(run100 != nullptr);
    REQUIRE(service->GetCalibration(100) == run100);
    REQUIRE(service->GetCalibration(250) != run100);
    REQUIRE(run100->GetDefaultRun() == 100);

    REQUIRE(service->GetConstants<vector<vector<double>>>(100, "/test/jana2/gains") == GAINS_NEW);
    REQUIRE(service->GetConstants<vector<vector<double>>>(250, "/test/jana2/gains") == GAINS_RUN200);
    REQUIRE(service->GetConstants<vector<vector<double>>>(300, "/test/jana2/gains") == GAINS_NEW);
}


TEST_CASE("CCDB_service/ccdb:time", "[jana2]")
{
    JApplication app;
    auto service = StartService(app, {{"ccdb:url", JanaTestConnection()}, {"ccdb:time", "2022"}});

    // 2022 is before the "new" gains (2024) and after the "old" ones (2020)
    REQUIRE(service->GetConstants<vector<vector<double>>>(100, "/test/jana2/gains") == GAINS_OLD);
    REQUIRE(service->GetConstants<vector<vector<double>>>(250, "/test/jana2/gains") == GAINS_OLD);
}


TEST_CASE("CCDB_service/ccdb:tag", "[jana2]")
{
    SECTION("The tag gives the variation and the time")
    {
        JApplication app;
        auto service = StartService(app, {{"ccdb:url", JanaTestConnection()}, {"ccdb:tag", "jana2_campaign"}});

        // jana2_campaign is variation default at 2022-01-01
        REQUIRE(service->GetConstants<vector<vector<double>>>(100, "/test/jana2/gains") == GAINS_OLD);
        REQUIRE(service->GetConstants<vector<vector<double>>>(250, "/test/jana2/gains") == GAINS_OLD);
        REQUIRE(service->GetConstants<double>(100, "/test/jana2/pedestal") == 100);

        // The Calibration of the run reads through the tag too (Calibration::SetTag)
        ccdb::Calibration* calib = service->GetCalibration(100);
        REQUIRE(calib->GetDefaultTag() == "jana2_campaign");
        vector<vector<double>> gains;
        REQUIRE(calib->GetCalib(gains, "/test/jana2/gains"));
        REQUIRE(gains == GAINS_OLD);
        // A request that names a variation under a tag would mix the tag with other constants: an error
        REQUIRE_THROWS_WITH(service->GetConstants<double>(100, "/test/jana2/pedestal::jana2_child"),
                            Catch::Contains("may not name a variation"));
    }

    SECTION("A tag together with a time is a configuration error")
    {
        JApplication app;
        REQUIRE_THROWS_WITH(StartService(app, {{"ccdb:url", JanaTestConnection()}, {"ccdb:tag", "jana2_campaign"},
                                               {"ccdb:time", "2022"}}),
                            Catch::Contains("set together with ccdb:time"));
    }

    SECTION("A tag together with a variation is a configuration error, even the default one")
    {
        JApplication app;
        REQUIRE_THROWS_WITH(StartService(app, {{"ccdb:url", JanaTestConnection()}, {"ccdb:tag", "jana2_campaign"},
                                               {"ccdb:variation", "default"}}),
                            Catch::Contains("set together with ccdb:variation"));
    }

    SECTION("An unknown tag fails on the request")
    {
        JApplication app;
        auto service = StartService(app, {{"ccdb:url", JanaTestConnection()}, {"ccdb:tag", "no_such_tag"}});
        REQUIRE_THROWS_WITH(service->GetConstants<double>(100, "/test/jana2/pedestal"), Catch::Contains("no_such_tag"));
    }
}


TEST_CASE("CCDB_service/variation inheritance", "[jana2]")
{
    JApplication app;
    auto service = StartService(app, {{"ccdb:url", JanaTestConnection()}, {"ccdb:variation", "jana2_child"}});

    // The child variation has its own pedestal and inherits the gains of its parent, default
    REQUIRE(service->GetConstants<double>(100, "/test/jana2/pedestal") == 200);
    REQUIRE(service->GetConstants<vector<vector<double>>>(100, "/test/jana2/gains") == GAINS_NEW);
}


TEST_CASE("CCDB_service/errors", "[jana2]")
{
    JApplication app;
    auto service = StartService(app, {{"ccdb:url", JanaTestConnection()}});

    REQUIRE_THROWS_AS(service->GetConstants<vector<vector<double>>>(100, "/test/jana2/no_such_table"), JException);
    REQUIRE_THROWS_WITH(service->GetConstants<vector<vector<double>>>(100, "/test/jana2/no_such_table"),
                        Catch::Contains("/test/jana2/no_such_table"));
    // The gains cover runs 0-999 only
    REQUIRE_THROWS_WITH(service->GetConstants<vector<vector<double>>>(5000, "/test/jana2/gains"),
                        Catch::Contains("run 5000"));
}


TEST_CASE("CCDB_service/thread safety", "[jana2]")
{
    JApplication app;
    auto service = StartService(app, {{"ccdb:url", JanaTestConnection()}});

    // Threads ask for two runs at once, the way JANA2 worker threads call factories
    const int thread_count = 8;
    vector<int> wrong_answers(thread_count, 0);
    vector<thread> threads;
    for (int thread_i = 0; thread_i < thread_count; thread_i++) {
        threads.emplace_back([&, thread_i]() {
            for (int request_i = 0; request_i < 50; request_i++) {
                int run = (request_i + thread_i) % 2 == 0 ? 100 : 250;
                auto gains = service->GetConstants<vector<vector<double>>>(run, "/test/jana2/gains");
                if (gains != (run == 100 ? GAINS_NEW : GAINS_RUN200)) wrong_answers[thread_i]++;
            }
        });
    }
    for (auto& worker: threads) worker.join();
    for (int wrong: wrong_answers) REQUIRE(wrong == 0);
}


TEST_CASE("CCDB_service/loaded as a plugin", "[jana2]")
{
    // What a JANA2 job does: -Pplugins=CCDB_service, the plugin provides the service
    JApplication app;
    app.SetParameterValue("jana:loglevel", "warn");
    app.SetParameterValue("ccdb:url", JanaTestConnection());
    app.AddPluginPath(CCDB_JANA2_PLUGIN_DIR);
    app.AddPlugin("CCDB_service");
    app.Initialize();

    auto service = app.GetService<CCDB_service>();
    REQUIRE(service->GetConstants<double>(100, "/test/jana2/pedestal") == 100);
}


// The service through the HTTP API: CCDB_TEST_JANA2_HTTP_URL is the API on the demo tables of
// scripts/demo/make_epic_tables.py (jana2_tests.sh says how to start it); unset, the case is skipped.
TEST_CASE("CCDB_service/HTTP API", "[jana2][http]")
{
    const char* url = getenv("CCDB_TEST_JANA2_HTTP_URL");
    if (!url) {
        WARN("CCDB_TEST_JANA2_HTTP_URL is not set: the HTTP case is skipped");
        return;
    }
    REQUIRE(ccdb::CalibrationGenerator::CheckOpenable(url));
    const string table = "/epic/TOFBarrel/lgad_calibration";

    SECTION("ccdb:url, the newest constants of two runs")
    {
        JApplication app;
        auto service = StartService(app, {{"ccdb:url", url}});
        REQUIRE(service->GetConstants<map<string, double>>(500, table).at("tIntercept") == 0.04314);
        REQUIRE(service->GetConstants<map<string, double>>(1500, table).at("tIntercept") == 0.05114);
    }

    SECTION("JANA_CALIB_URL with the campaign tag, before the late correction")
    {
        ScopedEnv connection("CCDB_CONNECTION", nullptr);
        ScopedEnv jana_url("JANA_CALIB_URL", url);
        JApplication app;
        auto service = StartService(app, {{"ccdb:tag", "campaign_demo"}});
        REQUIRE(service->GetUrl() == url);
        REQUIRE(service->GetConstants<map<string, double>>(1500, table).at("tIntercept") == 0.04314);
    }
}
