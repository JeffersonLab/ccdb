// CCDB_service::GetResource and its SHA-256 (jana2/src), against the resources tables of
// scripts/eic/make_jana2_test_db.py: a file:// URL with the true hash, the same file with a wrong hash,
// a missing file and an https URL. With CCDB_TEST_JANA2_HTTP_RESOURCE_BASE set (scripts/eic/jana2_tests.sh
// serves the resource directory with python's http.server), also the http:// tables: a download, the cache
// hit, a wrong hash, a file the server does not have and a port nothing listens on.
#include "tests/catch.hpp"

#include <JANA/JApplication.h>

#include <CCDB/Helpers/HttpDownload.h>

#include "CCDB_service.h"
#include "Sha256.h"

#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <map>
#include <memory>
#include <string>
#include <vector>

using namespace std;
namespace fs = std::filesystem;

namespace {

    string TestDatabasePath() {
        const char* path = getenv("CCDB_TEST_JANA2_SQLITE");
        if (!path) throw runtime_error("CCDB_TEST_JANA2_SQLITE is not set: run scripts/eic/make_jana2_test_db.py");
        return path;
    }

    /// The file the resources tables point at (make_jana2_test_db.py writes it next to the database)
    string ResourceSourcePath() { return TestDatabasePath() + ".resource/weights.bin"; }

    /// The http.server on the resource directory (jana2_tests.sh), "" when none is running
    string HttpResourceBase() {
        const char* base = getenv("CCDB_TEST_JANA2_HTTP_RESOURCE_BASE");
        return base ? base : "";
    }

    bool HttpResourcesServed() {
        if (!HttpResourceBase().empty()) return true;
        WARN("CCDB_TEST_JANA2_HTTP_RESOURCE_BASE is not set: the http(s) resource tests are skipped (scripts/eic/jana2_tests.sh serves the resources)");
        return false;
    }

    size_t RegularFilesUnder(const string& directory) {
        size_t files = 0;
        for (const auto& entry: fs::recursive_directory_iterator(directory)) {
            if (entry.is_regular_file()) files++;
        }
        return files;
    }

    string ReadFile(const string& path) {
        ifstream file(path, ios::binary);
        return string(istreambuf_iterator<char>(file), istreambuf_iterator<char>());
    }

    /// A fresh cache directory per test, removed at the end
    class TempCacheDir {
    public:
        TempCacheDir() {
            string pattern = (fs::temp_directory_path() / "ccdb_jana2_cache_XXXXXX").string();
            mPath = mkdtemp(&pattern[0]);
        }
        ~TempCacheDir() { std::error_code error; fs::remove_all(mPath, error); }
        const string& Path() const { return mPath; }
    private:
        string mPath;
    };

    shared_ptr<CCDB_service> StartService(JApplication& app, const string& cache_dir) {
        app.SetParameterValue("jana:loglevel", "warn");
        app.SetParameterValue("ccdb:url", "sqlite:///" + TestDatabasePath());
        app.SetParameterValue("ccdb:cache_dir", cache_dir);
        app.ProvideService(make_shared<CCDB_service>(&app));
        app.Initialize();
        return app.GetService<CCDB_service>();
    }
}


TEST_CASE("CCDB_service/SHA-256 test vectors", "[jana2]")
{
    using ccdb_jana2::Sha256;
    // FIPS 180-4 examples, and Python's hashlib for the multi-block one
    REQUIRE(Sha256::OfString("") == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855");
    REQUIRE(Sha256::OfString("abc") == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad");
    REQUIRE(Sha256::OfString("abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq") ==
            "248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1");
    REQUIRE(Sha256::OfString(string(1000000, 'a')) == "cdc76e5c9914fb9281a1c7e284d73e67f1809a48a497200e046d39ccc7112cd0");

    // Fed in pieces that cross block boundaries
    Sha256 pieces;
    string text(200, 'x');
    pieces.Update(text.data(), 63);
    pieces.Update(text.data() + 63, 2);
    pieces.Update(text.data() + 65, 135);
    REQUIRE(pieces.HexDigest() == Sha256::OfString(text));
}


TEST_CASE("CCDB_service/GetResource", "[jana2]")
{
    TempCacheDir cache;

    SECTION("A file:// resource is copied into the cache once and returned by path")
    {
        JApplication app;
        auto service = StartService(app, cache.Path());

        string path = service->GetResource(100, "/test/jana2/model");
        REQUIRE(path.rfind(cache.Path(), 0) == 0);
        REQUIRE(fs::path(path).filename() == "weights.bin");
        REQUIRE(ReadFile(path) == ReadFile(ResourceSourcePath()));
        // the directory is the hash the table holds
        REQUIRE(fs::path(path).parent_path().filename().string() == ccdb_jana2::Sha256::OfFile(ResourceSourcePath()));

        auto written = fs::last_write_time(path);
        REQUIRE(service->GetResource(250, "/test/jana2/model") == path);
        REQUIRE(fs::last_write_time(path) == written);
    }

    SECTION("A cached file is used by a later job, and fetched again when it was changed")
    {
        string path;
        {
            JApplication app;
            path = StartService(app, cache.Path())->GetResource(100, "/test/jana2/model");
        }
        {
            JApplication app;
            auto written = fs::last_write_time(path);
            REQUIRE(StartService(app, cache.Path())->GetResource(100, "/test/jana2/model") == path);
            REQUIRE(fs::last_write_time(path) == written);
        }
        {
            ofstream(path, ios::binary | ios::trunc) << "damaged";
            JApplication app;
            REQUIRE(StartService(app, cache.Path())->GetResource(100, "/test/jana2/model") == path);
            REQUIRE(ReadFile(path) == ReadFile(ResourceSourcePath()));
        }
    }

    SECTION("A wrong hash is an error and leaves nothing in the cache")
    {
        JApplication app;
        auto service = StartService(app, cache.Path());
        REQUIRE_THROWS_WITH(service->GetResource(100, "/test/jana2/model_bad_hash"),
                            Catch::Contains("does not match the table") && Catch::Contains("not kept"));
        REQUIRE(RegularFilesUnder(cache.Path()) == 0);
    }

    SECTION("A missing file and an https URL nobody serves are errors that name the URL")
    {
        JApplication app;
        auto service = StartService(app, cache.Path());
        REQUIRE_THROWS_WITH(service->GetResource(100, "/test/jana2/model_missing"), Catch::Contains("weights.bin.missing"));
        if (HttpResourceBase().empty()) {
            // Without the test server the table points at https://example.org; the error names the URL whether
            // this build downloads (and gets no file there) or has no HTTP support
            REQUIRE_THROWS_WITH(service->GetResource(100, "/test/jana2/model_http"), Catch::Contains("https://example.org"));
        }
    }

    SECTION("A table that is not a resources table is an error")
    {
        JApplication app;
        auto service = StartService(app, cache.Path());
        REQUIRE_THROWS_WITH(service->GetResource(100, "/test/jana2/gains"), Catch::Contains("must have one"));
        REQUIRE_THROWS_WITH(service->GetResource(100, "/test/jana2/pedestal"), Catch::Contains("no column 'url'"));
    }
}


TEST_CASE("CCDB_service/GetResource over HTTP", "[jana2]")
{
    if (!HttpResourcesServed()) return;
    // eic-shell has libcurl, so the library there downloads; a build without it makes GetResource say so
    REQUIRE(ccdb::HttpDownload::Available());

    TempCacheDir cache;
    string base = HttpResourceBase();

    SECTION("An http:// resource is downloaded into the cache once and gives the file's bytes")
    {
        JApplication app;
        auto service = StartService(app, cache.Path());

        string path = service->GetResource(100, "/test/jana2/model_http");
        REQUIRE(path.rfind(cache.Path(), 0) == 0);
        REQUIRE(fs::path(path).filename() == "weights.bin");
        REQUIRE(ReadFile(path) == ReadFile(ResourceSourcePath()));
        REQUIRE(fs::path(path).parent_path().filename().string() == ccdb_jana2::Sha256::OfFile(ResourceSourcePath()));
        REQUIRE(RegularFilesUnder(cache.Path()) == 1);     // no .part file left behind

        // the same service: the verified path, no second download (a download would give a newer file)
        auto written = fs::last_write_time(path);
        REQUIRE(service->GetResource(250, "/test/jana2/model_http") == path);
        REQUIRE(fs::last_write_time(path) == written);
    }

    SECTION("A later job uses the downloaded file without downloading it again")
    {
        string path;
        {
            JApplication app;
            path = StartService(app, cache.Path())->GetResource(100, "/test/jana2/model_http");
        }
        auto written = fs::last_write_time(path);
        {
            JApplication app;
            REQUIRE(StartService(app, cache.Path())->GetResource(100, "/test/jana2/model_http") == path);
        }
        REQUIRE(fs::last_write_time(path) == written);
        REQUIRE(RegularFilesUnder(cache.Path()) == 1);
    }

    SECTION("A download whose hash differs from the table is an error and leaves nothing in the cache")
    {
        JApplication app;
        auto service = StartService(app, cache.Path());
        REQUIRE_THROWS_WITH(service->GetResource(100, "/test/jana2/model_http_bad_hash"),
                            Catch::Contains("does not match the table") && Catch::Contains("not kept"));
        REQUIRE(RegularFilesUnder(cache.Path()) == 0);
    }

    SECTION("A URL the server does not have is an error that names the URL and the answer")
    {
        JApplication app;
        auto service = StartService(app, cache.Path());
        REQUIRE_THROWS_WITH(service->GetResource(100, "/test/jana2/model_http_missing"),
                            Catch::Contains(base + "/missing.bin") && Catch::Contains("404"));
        REQUIRE(RegularFilesUnder(cache.Path()) == 0);
    }

    SECTION("A server that can't be reached is an error that names the URL and the connection")
    {
        JApplication app;
        auto service = StartService(app, cache.Path());
        // the table's URL has a loopback port nothing listens on; curl: "Failed to connect to ... Could not connect to server"
        string url = service->GetConstants<vector<map<string, string>>>(100, "/test/jana2/model_http_unreachable")[0].at("url");
        REQUIRE(url.rfind("http://127.0.0.1:", 0) == 0);
        REQUIRE_THROWS_WITH(service->GetResource(100, "/test/jana2/model_http_unreachable"),
                            Catch::Contains(url) && Catch::Contains("connect", Catch::CaseSensitive::No));
        REQUIRE(RegularFilesUnder(cache.Path()) == 0);
    }
}
