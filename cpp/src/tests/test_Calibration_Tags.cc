// Calibration's request path for tags (CCDB 2.5), with a provider that records the calls instead of a database
#include "tests/catch.hpp"

#include <string>
#include <vector>

#include "CCDB/SQLiteCalibration.h"
#include "CCDB/Providers/DataProvider.h"
#include "CCDB/Model/Assignment.h"

using namespace std;
using namespace ccdb;

namespace {

    /** Answers every request with a new assignment and remembers how it was asked */
    class RecordingProvider: public DataProvider
    {
    public:
        struct Call {
            bool byTag;
            int run;
            string path;
            time_t time;
            string variation;
            string tag;
        };
        vector<Call> calls;

        void Connect(const string& connectionString) override { mConnectionString = connectionString; }
        void Disconnect() override {}
        bool IsConnected() override { return true; }
        void LoadDirectories() override {}
        ConstantsTypeTable* GetConstantsTypeTable(const string&, Directory*, bool) override { return nullptr; }
        vector<ConstantsTypeTable*> GetAllConstantsTypeTables(bool) override { return {}; }
        Variation* GetVariation(const string&) override { return nullptr; }

        Assignment* GetAssignmentShort(int run, const string& path, time_t time, const string& variation, bool) override
        {
            calls.push_back({false, run, path, time, variation, ""});
            return NewAssignment();
        }

        Assignment* GetAssignmentShortByTag(int run, const string& path, const string& tagName, bool) override
        {
            calls.push_back({true, run, path, 0, "", tagName});
            return NewAssignment();
        }

    private:
        Assignment* NewAssignment()
        {
            Assignment* assignment = new Assignment();
            assignment->SetId(calls.size());
            return assignment;
        }
    };
}


TEST_CASE("CCDB/Calibration/Tags", "Calibration passes the tag to the provider by its own argument")
{
    RecordingProvider provider;
    provider.Connect("recording://test");

    SECTION("Tag requests", "/path@tag, /path:run@tag, /path:run:@tag")
    {
        SQLiteCalibration calib(100, "default", 0);
        calib.UseProvider(&provider, /*lockProvider*/ true);
        calib.EnableCache(true);

        Assignment* tagged = calib.GetAssignment("/a/b@mytag");
        REQUIRE(tagged != nullptr);
        REQUIRE(provider.calls.size() == 1);
        REQUIRE(provider.calls[0].byTag);
        REQUIRE(provider.calls[0].run == 100);
        REQUIRE(provider.calls[0].path == "/a/b");
        REQUIRE(provider.calls[0].tag == "mytag");

        Assignment* taggedRun = calib.GetAssignment("a/b:5:@mytag");
        REQUIRE(taggedRun != nullptr);
        REQUIRE(provider.calls.size() == 2);
        REQUIRE(provider.calls[1].byTag);
        REQUIRE(provider.calls[1].run == 5);
        REQUIRE(provider.calls[1].path == "/a/b");
        REQUIRE(provider.calls[1].tag == "mytag");

        // The same tag request comes from the cache
        REQUIRE(calib.GetAssignment("/a/b@mytag") == tagged);
        REQUIRE(provider.calls.size() == 2);

        // The untagged request and another tag don't share the tag's cache entry
        Assignment* untagged = calib.GetAssignment("/a/b");
        REQUIRE(untagged != nullptr);
        REQUIRE(untagged != tagged);
        REQUIRE(provider.calls.size() == 3);
        REQUIRE_FALSE(provider.calls[2].byTag);
        REQUIRE(provider.calls[2].variation == "default");

        Assignment* otherTag = calib.GetAssignment("/a/b@other");
        REQUIRE(otherTag != tagged);
        REQUIRE(provider.calls.size() == 4);
        REQUIRE(provider.calls[3].byTag);
        REQUIRE(provider.calls[3].tag == "other");

        // A tag with a variation or a time never reaches the provider
        REQUIRE_THROWS_AS(calib.GetAssignment("/a/b:5:mc@mytag"), std::invalid_argument);
        REQUIRE_THROWS_AS(calib.GetAssignment("/a/b@my-tag"), std::invalid_argument);
        REQUIRE(provider.calls.size() == 4);
    }

    SECTION("Requests without a tag", "Variation and time go to GetAssignmentShort as before")
    {
        SQLiteCalibration calib(100, "mc", 1000);
        calib.UseProvider(&provider, /*lockProvider*/ true);
        calib.EnableCache(false);

        Assignment* assignment = calib.GetAssignment("/a/b");
        REQUIRE(provider.calls.size() == 1);
        REQUIRE_FALSE(provider.calls[0].byTag);
        REQUIRE(provider.calls[0].run == 100);
        REQUIRE(provider.calls[0].variation == "mc");
        REQUIRE(provider.calls[0].time == 1000);
        delete assignment;

        assignment = calib.GetAssignment("/a/b:7:default:2029");
        REQUIRE(provider.calls.size() == 2);
        REQUIRE_FALSE(provider.calls[1].byTag);
        REQUIRE(provider.calls[1].run == 7);
        REQUIRE(provider.calls[1].variation == "default");
        REQUIRE(provider.calls[1].time > 1000);
        delete assignment;

        // The tag ignores the default variation and time
        assignment = calib.GetAssignment("/a/b@mytag");
        REQUIRE(provider.calls.size() == 3);
        REQUIRE(provider.calls[2].byTag);
        REQUIRE(provider.calls[2].tag == "mytag");
        delete assignment;
    }

    SECTION("A default variation is not a tag", "Calibration made for the variation '@mytag'")
    {
        // The providers have no variation '@mytag', so they fail such a request; it must not become a tag request
        SQLiteCalibration calib(100, "@mytag", 0);
        calib.UseProvider(&provider, /*lockProvider*/ true);
        calib.EnableCache(false);

        Assignment* assignment = calib.GetAssignment("/a/b");
        REQUIRE(provider.calls.size() == 1);
        REQUIRE_FALSE(provider.calls[0].byTag);
        REQUIRE(provider.calls[0].variation == "@mytag");
        delete assignment;
    }
}
