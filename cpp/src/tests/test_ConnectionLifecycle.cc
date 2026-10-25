// Connection lifecycle, ownership and thread safety tests that need only SQLite
#include "catch.hpp"
#include "tests.h"

#include <atomic>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <memory>
#include <set>
#include <string>
#include <thread>
#include <vector>

#include <sqlite3.h>
#include <sys/stat.h>
#include <unistd.h>

#include "CCDB/CalibrationGenerator.h"
#include "CCDB/Helpers/EnvUtils.h"
#include "CCDB/Helpers/StringUtils.h"
#include "CCDB/Providers/SQLiteDataProvider.h"
#include "CCDB/SQLiteCalibration.h"

using namespace std;
using namespace ccdb;

namespace {

    const char* kTable = "/test/test_vars/test_table";

    /// File path of the test database, "sqlite:///" + path
    string TestDbPath() {
        return get_test_sqlite_connection().substr(string("sqlite:///").size());
    }

    string TempPath(const string& suffix) {
        static int counter = 0;
        const char* dir = getenv("TMPDIR");
        return string(dir ? dir : "/tmp") + "/ccdb_lifecycle_" + to_string(getpid()) + "_" + to_string(counter++) + suffix;
    }

    bool FileExists(const string& path) {
        struct stat st{};
        return stat(path.c_str(), &st) == 0;
    }

    /// Writable copy of the test database, removed on destruction
    struct TempDbCopy {
        string path;
        TempDbCopy(): path(TempPath(".sqlite")) {
            ifstream src(TestDbPath(), ios::binary);
            ofstream dst(path, ios::binary);
            dst << src.rdbuf();
        }
        ~TempDbCopy() { remove(path.c_str()); }
        string ConnectionString() const { return "sqlite:///" + path; }
    };

    /// Sets an environment variable for the scope and restores the previous state
    struct ScopedEnv {
        string name; bool hadValue; string oldValue;
        ScopedEnv(const string& n, const string& value): name(n) {
            const char* old = getenv(n.c_str());
            hadValue = old != nullptr;
            if(hadValue) oldValue = old;
            setenv(n.c_str(), value.c_str(), 1);
        }
        ~ScopedEnv() {
            if(hadValue) setenv(name.c_str(), oldValue.c_str(), 1);
            else unsetenv(name.c_str());
        }
    };

    /// Holds an exclusive (write) lock on a database file through an independent connection
    struct ExclusiveLock {
        sqlite3* db = nullptr;
        explicit ExclusiveLock(const string& path) {
            REQUIRE(sqlite3_open_v2(path.c_str(), &db, SQLITE_OPEN_READWRITE, nullptr) == SQLITE_OK);
            REQUIRE(sqlite3_exec(db, "BEGIN EXCLUSIVE", nullptr, nullptr, nullptr) == SQLITE_OK);
        }
        void Release() {
            if(db) {
                sqlite3_exec(db, "COMMIT", nullptr, nullptr, nullptr);
                sqlite3_close(db);
                db = nullptr;
            }
        }
        ~ExclusiveLock() { Release(); }
    };

    double SecondsSince(chrono::steady_clock::time_point start) {
        return chrono::duration<double>(chrono::steady_clock::now() - start).count();
    }
}


TEST_CASE("CCDB/Lifecycle/EnvSettings", "[lifecycle]")
{
    unsigned int value = 7;
    REQUIRE(ParsePositiveUIntSetting("10", value, 100));
    REQUIRE(value == 10);

    value = 7;
    REQUIRE_FALSE(ParsePositiveUIntSetting("", value, 100));
    REQUIRE_FALSE(ParsePositiveUIntSetting("0", value, 100));
    REQUIRE_FALSE(ParsePositiveUIntSetting("-5", value, 100));
    REQUIRE_FALSE(ParsePositiveUIntSetting("5s", value, 100));
    REQUIRE_FALSE(ParsePositiveUIntSetting(" 5", value, 100));
    REQUIRE_FALSE(ParsePositiveUIntSetting("101", value, 100));
    REQUIRE_FALSE(ParsePositiveUIntSetting("99999999999999999999", value, 100));
    REQUIRE(value == 7);    // untouched on failure

    const char* name = "CCDB_TEST_LIFECYCLE_SETTING";
    unsetenv(name);
    REQUIRE(GetEnvPositiveUInt(name, 42, 100) == 42);
    {
        ScopedEnv env(name, "17");
        REQUIRE(GetEnvPositiveUInt(name, 42, 100) == 17);
    }
    {
        ScopedEnv env(name, "abc");     // invalid => default (and a warning on stderr)
        REQUIRE(GetEnvPositiveUInt(name, 42, 100) == 42);
    }
    REQUIRE(getenv(name) == nullptr);
}


TEST_CASE("CCDB/Lifecycle/MaskPassword", "[lifecycle]")
{
    REQUIRE(StringUtils::MaskPassword("mysql://user:secret@host/db") == "mysql://user:***@host/db");
    REQUIRE(StringUtils::MaskPassword("mysql://user:secret@host:3306/db") == "mysql://user:***@host:3306/db");
    REQUIRE(StringUtils::MaskPassword("mysql://user:p@ss:w@host/db") == "mysql://user:***@host/db");
    REQUIRE(StringUtils::MaskPassword("MySQL://user:secret@host/db") == "MySQL://user:***@host/db");
    REQUIRE(StringUtils::MaskPassword("mysql://user@host:3306/db") == "mysql://user@host:3306/db");
    REQUIRE(StringUtils::MaskPassword("mysql://host/db") == "mysql://host/db");
    REQUIRE(StringUtils::MaskPassword("sqlite:////path/to/ccdb.sqlite") == "sqlite:////path/to/ccdb.sqlite");

    // Error messages that print a connection string must not reveal the password
    string message;
    try {
        CalibrationGenerator gen;
        gen.MakeCalibration("MySQL://ccdb_user:S3cretPw@host/ccdb", 1, "default", 0);
    }
    catch (const std::exception& ex) {
        message = ex.what();
    }
    REQUIRE_FALSE(message.empty());
    REQUIRE(message.find("S3cretPw") == string::npos);
    REQUIRE(message.find("ccdb_user:***@host") != string::npos);
}


TEST_CASE("CCDB/Lifecycle/SQLiteMissingFileIsNotCreated", "[lifecycle]")
{
    string path = TempPath("_missing.sqlite");
    REQUIRE_FALSE(FileExists(path));

    SQLiteDataProvider prov;
    string message;
    try { prov.Connect("sqlite:///" + path); }
    catch (const std::exception& ex) { message = ex.what(); }

    REQUIRE_FALSE(message.empty());
    REQUIRE(message.find(path) != string::npos);   // the path helps to diagnose farm jobs
    REQUIRE_FALSE(prov.IsConnected());
    REQUIRE_FALSE(FileExists(path));

    // Even an URI asking to create the file must not create it
    REQUIRE_THROWS(prov.Connect("sqlite:///file:" + path + "?mode=rwc"));
    REQUIRE_FALSE(FileExists(path));
}


TEST_CASE("CCDB/Lifecycle/SQLiteUriOptions", "[lifecycle]")
{
    for (const char* options: {"?immutable=1", "?mode=ro", ""})
    {
        SQLiteCalibration calib(100);
        string conStr = "sqlite:///file:" + TestDbPath() + options;
        REQUIRE_NOTHROW(calib.Connect(conStr));
        REQUIRE(calib.IsConnected());

        vector<vector<string> > values;
        REQUIRE(calib.GetCalib(values, kTable));
        REQUIRE(values.size() == 2);
    }
}


TEST_CASE("CCDB/Lifecycle/SQLiteBusyTimeout", "[lifecycle]")
{
    TempDbCopy db;

    SECTION("Read waits for the configured busy timeout and then fails")
    {
        ScopedEnv env("CCDB_SQLITE_BUSY_TIMEOUT", "300");
        SQLiteCalibration calib(100);
        calib.Connect(db.ConnectionString());

        ExclusiveLock lock(db.path);
        auto start = chrono::steady_clock::now();
        vector<vector<string> > values;
        REQUIRE_THROWS(calib.GetCalib(values, kTable));
        double elapsed = SecondsSince(start);
        REQUIRE(elapsed >= 0.25);
        REQUIRE(elapsed < 10);
    }

    SECTION("Read succeeds once the writer releases the lock")
    {
        SQLiteCalibration calib(100);
        calib.Connect(db.ConnectionString());   // default busy timeout (30 s)

        ExclusiveLock lock(db.path);
        thread releaser([&lock] {
            this_thread::sleep_for(chrono::milliseconds(300));
            lock.Release();
        });

        vector<vector<string> > values;
        bool result = false;
        REQUIRE_NOTHROW(result = calib.GetCalib(values, kTable));
        releaser.join();
        REQUIRE(result);
        REQUIRE(values.size() == 2);
    }
}


TEST_CASE("CCDB/Lifecycle/DisconnectNeverConnected", "[lifecycle]")
{
    SQLiteCalibration calib(100);
    REQUIRE_FALSE(calib.IsConnected());
    REQUIRE_NOTHROW(calib.Disconnect());
    REQUIRE_NOTHROW(calib.Disconnect());
    REQUIRE_FALSE(calib.IsConnected());

    // A request without any connection is a clear error, not a crash
    vector<vector<string> > values;
    REQUIRE_THROWS_AS(calib.GetCalib(values, kTable), std::logic_error);

    SQLiteDataProvider prov;
    REQUIRE_NOTHROW(prov.Disconnect());
    REQUIRE_FALSE(prov.IsConnected());
}


TEST_CASE("CCDB/Lifecycle/GeneratorOwnership", "[lifecycle]")
{
    auto conStr = get_test_sqlite_connection();

    SECTION("Generator destruction closes connections but leaves objects usable")
    {
        auto gen = new CalibrationGenerator();
        Calibration* calib = gen->MakeCalibration(conStr, 100, "default", 0);
        REQUIRE(calib->IsConnected());

        delete gen;
        REQUIRE_FALSE(calib->IsConnected());

        // The object is still valid: it reconnects on request and can be deleted by its user
        vector<vector<string> > values;
        REQUIRE(calib->GetCalib(values, kTable));
        delete calib;
    }

    SECTION("A deleted calibration is never returned again")
    {
        CalibrationGenerator gen;
        Calibration* first = gen.MakeCalibration(conStr, 100, "default", 0);
        REQUIRE(gen.MakeCalibration(conStr, 100, "default", 0) == first);
        delete first;

        Calibration* second = gen.MakeCalibration(conStr, 100, "default", 0);
        vector<vector<string> > values;
        REQUIRE(second->GetCalib(values, kTable));
        REQUIRE(values.size() == 2);
        delete second;
    }

    SECTION("DeleteCalibrations deletes the calibrations still alive")
    {
        CalibrationGenerator gen;
        Calibration* kept = gen.MakeCalibration(conStr, 100, "default", 0);
        Calibration* deletedByUser = gen.MakeCalibration(conStr, 101, "default", 0);
        delete deletedByUser;           // must not be deleted again by the generator
        REQUIRE(kept->IsConnected());

        gen.DeleteCalibrations();       // deletes 'kept' (checked by AddressSanitizer)

        Calibration* fresh = gen.MakeCalibration(conStr, 100, "default", 0);
        vector<vector<string> > values;
        REQUIRE(fresh->GetCalib(values, kTable));
        gen.DeleteCalibrations();
    }

    SECTION("Failed connect does not register a calibration")
    {
        CalibrationGenerator gen;
        string missing = "sqlite:///" + TempPath("_missing.sqlite");
        REQUIRE_THROWS(gen.MakeCalibration(missing, 100, "default", 0));
        REQUIRE_THROWS(gen.MakeCalibration(missing, 100, "default", 0));
    }
}


TEST_CASE("CCDB/Lifecycle/GeneratorHashSeparation", "[lifecycle]")
{
    CalibrationGenerator gen;
    REQUIRE(gen.GetCalibrationHash("sqlite:///a", 12, "3x", 0) != gen.GetCalibrationHash("sqlite:///a", 123, "x", 0));
    REQUIRE(gen.GetCalibrationHash("sqlite:///a1", 23, "x", 0) != gen.GetCalibrationHash("sqlite:///a", 123, "x", 0));

    auto conStr = get_test_sqlite_connection();
    Calibration* a = gen.MakeCalibration(conStr, 12, "3x", 0);
    Calibration* b = gen.MakeCalibration(conStr, 123, "x", 0);
    REQUIRE(a != b);
    REQUIRE(b->GetDefaultRun() == 123);
    delete a;
    delete b;
}


TEST_CASE("CCDB/Lifecycle/GeneratorThreadSafety", "[lifecycle]")
{
    auto conStr = get_test_sqlite_connection();
    CalibrationGenerator gen;

    const int threadCount = 8;
    const int runCount = 20;
    vector<vector<Calibration*> > seen(threadCount);
    atomic<int> errors(0);

    vector<thread> threads;
    for (int t = 0; t < threadCount; t++) {
        threads.emplace_back([&, t] {
            for (int i = 0; i < 100; i++) {
                try {
                    Calibration* calib = gen.MakeCalibration(conStr, (i % runCount) + 1, "default", 0);
                    vector<vector<string> > values;
                    if(!calib->GetCalib(values, kTable) || values.size() != 2) errors++;
                    seen[t].push_back(calib);
                }
                catch (...) { errors++; }
            }
        });
    }
    for (auto& thread: threads) thread.join();

    REQUIRE(errors == 0);

    // Exactly one calibration per key, shared by all threads
    set<Calibration*> unique;
    for (auto& list: seen) unique.insert(list.begin(), list.end());
    REQUIRE(unique.size() == runCount);

    for (auto calib: unique) delete calib;
}


TEST_CASE("CCDB/Lifecycle/ConcurrentDisconnect", "[lifecycle]")
{
    SQLiteCalibration calib(100);
    calib.Connect(get_test_sqlite_connection());

    atomic<bool> stop(false);
    atomic<int> errors(0);

    vector<thread> readers;
    for (int t = 0; t < 4; t++) {
        readers.emplace_back([&] {
            while (!stop) {
                try {
                    vector<vector<string> > values;
                    if(!calib.GetCalib(values, kTable)) errors++;
                }
                catch (...) { errors++; }
            }
        });
    }

    // Disconnect concurrently with reads: auto-reconnect must make this invisible to readers
    for (int i = 0; i < 200; i++) {
        calib.Disconnect();
        this_thread::yield();
    }
    stop = true;
    for (auto& reader: readers) reader.join();

    REQUIRE(errors == 0);
}


TEST_CASE("CCDB/Lifecycle/CacheKeyIncludesConnection", "[lifecycle]")
{
    TempDbCopy changed;
    {
        sqlite3* db = nullptr;
        REQUIRE(sqlite3_open_v2(changed.path.c_str(), &db, SQLITE_OPEN_READWRITE, nullptr) == SQLITE_OK);
        REQUIRE(sqlite3_exec(db, "UPDATE constantSets SET vault='99|99|99|99|99|99'", nullptr, nullptr, nullptr) == SQLITE_OK);
        sqlite3_close(db);
    }

    SQLiteCalibration original(100);
    original.EnableCache(true);
    original.Connect(get_test_sqlite_connection());

    SQLiteCalibration modified(100);
    modified.EnableCache(true);
    modified.Connect(changed.ConnectionString());

    for (int repeat = 0; repeat < 2; repeat++) {     // second pass is served from the caches
        vector<vector<string> > originalValues, modifiedValues;
        REQUIRE(original.GetCalib(originalValues, kTable));
        REQUIRE(modified.GetCalib(modifiedValues, kTable));
        REQUIRE(modifiedValues[0][0] == "99");
        REQUIRE(originalValues[0][0] != "99");
    }

    // Cached assignments are owned by the calibration and must stay valid between calls
    Assignment* first = original.GetAssignment(kTable);
    Assignment* second = original.GetAssignment(kTable);
    REQUIRE(first == second);
}


TEST_CASE("CCDB/Lifecycle/UseProviderReplacesOwnedProvider", "[lifecycle]")
{
    // The provider created by Connect is owned by the calibration; replacing it must free it
    // (checked by LeakSanitizer in sanitizer builds) and the locked one must not be deleted
    auto conStr = get_test_sqlite_connection();
    SQLiteDataProvider shared;
    shared.Connect(conStr);

    {
        SQLiteCalibration calib(100);
        calib.Connect(conStr);
        calib.UseProvider(&shared, /*lockProvider*/ true);
        REQUIRE(calib.GetProviderIsLocked());

        vector<vector<string> > values;
        REQUIRE(calib.GetCalib(values, kTable));
        REQUIRE_THROWS_AS(calib.Disconnect(), std::logic_error);
    }

    REQUIRE(shared.IsConnected());
}
