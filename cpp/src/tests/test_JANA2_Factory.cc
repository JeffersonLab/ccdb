// The CCDB_service example factory (jana2/examples) in a JANA2 job: a dummy source emits events of two runs,
// GainCalibration_factory reads its gains for each run in ChangeRun(), a processor collects what it made.
// The gains differ between run 100 and run 250 (make_jana2_test_db.py), so the energies show the switch.
#include "tests/catch.hpp"

#include <JANA/JApplication.h>
#include <JANA/JEventProcessor.h>
#include <JANA/JEventSource.h>
#include <JANA/Components/JOmniFactoryGeneratorT.h>

#include "CCDB_service.h"
#include "GainCalibration_factory.h"

#include <cstdlib>
#include <iostream>
#include <memory>
#include <mutex>
#include <sstream>
#include <string>
#include <vector>

using namespace std;
using ccdb_example::CalibratedHit;
using ccdb_example::RawHit;

namespace {

    /// Four events: two of run 100, then two of run 250; each has channel 1 and channel 2 at adc 10
    class TwoRunSource : public JEventSource {
    public:
        TwoRunSource() {
            SetTypeName("TwoRunSource");
            SetCallbackStyle(CallbackStyle::ExpertMode);
        }

        Result Emit(JEvent& event) override {
            if (m_emitted == 4) return Result::FailureFinished;
            event.SetEventNumber(m_emitted + 1);
            event.SetRunNumber(m_emitted < 2 ? 100 : 250);
            event.Insert(vector<RawHit*>{new RawHit{1, 10.0}, new RawHit{2, 10.0}}, "raw_hits");
            m_emitted++;
            return Result::Success;
        }

    private:
        int m_emitted = 0;
    };

    struct CollectedHit {
        int run;
        uint64_t event;
        int channel;
        double energy;
    };

    class HitCollector : public JEventProcessor {
    public:
        HitCollector() {
            SetTypeName("HitCollector");
            SetCallbackStyle(CallbackStyle::ExpertMode);
        }

        void ProcessSequential(const JEvent& event) override {
            for (const CalibratedHit* hit: event.Get<CalibratedHit>("calibrated_hits")) {
                hits.push_back({event.GetRunNumber(), event.GetEventNumber(), hit->channel, hit->energy});
            }
        }

        vector<CollectedHit> hits;
    };

    string JanaTestConnection() {
        const char* path = getenv("CCDB_TEST_JANA2_SQLITE");
        if (!path) throw runtime_error("CCDB_TEST_JANA2_SQLITE is not set: run scripts/eic/make_jana2_test_db.py");
        return string("sqlite:///") + path;
    }

    /// Runs the job; the factory comes from the example plugin or is added directly
    vector<CollectedHit> RunJob(const map<string, string>& parameters, bool factory_from_plugin) {
        JApplication app;
        app.SetParameterValue("jana:loglevel", "warn");
        app.SetParameterValue("nthreads", 1);
        app.SetParameterValue("ccdb:url", JanaTestConnection());
        for (const auto& parameter: parameters) app.SetParameterValue(parameter.first, parameter.second);

        if (factory_from_plugin) {
            app.AddPluginPath(CCDB_JANA2_PLUGIN_DIR);
            app.AddPlugin("CCDB_service");
            app.AddPlugin("ccdb_jana2_example");
        } else {
            app.ProvideService(make_shared<CCDB_service>(&app));
            app.Add(new JOmniFactoryGeneratorT<ccdb_example::GainCalibration_factory>(
                "calibrated_hits", {"raw_hits"}, {"calibrated_hits"}));
        }
        app.Add(new TwoRunSource());
        auto collector = new HitCollector();
        app.Add(collector);
        app.Run();
        return collector->hits;   // JANA2 owns the processor until the application goes; copy the hits out
    }

    string Describe(const vector<CollectedHit>& hits) {
        ostringstream text;
        for (const auto& hit: hits) {
            text << "run " << hit.run << " event " << hit.event << " channel " << hit.channel << " energy " << hit.energy << "\n";
        }
        return text.str();
    }
}


TEST_CASE("CCDB_service/example factory switches constants with the run", "[jana2]")
{
    // gains (gain, offset) by run: run 100 -> 1.5, 0.15 | 2.5, 0.25; run 250 -> 3.0, 0.3 | 4.0, 0.4
    const vector<double> expected_energies = {15.15, 25.25, 15.15, 25.25, 30.3, 40.4, 30.3, 40.4};

    for (bool factory_from_plugin: {false, true}) {
        SECTION(factory_from_plugin ? "Factory and service from their plugins" : "Factory and service added in code") {
            auto hits = RunJob({}, factory_from_plugin);
            INFO(Describe(hits));
            cout << "example factory, " << (factory_from_plugin ? "plugins" : "in code") << ":\n" << Describe(hits);

            REQUIRE(hits.size() == expected_energies.size());
            for (size_t hit_i = 0; hit_i < hits.size(); hit_i++) {
                REQUIRE(hits[hit_i].run == (hit_i < 4 ? 100 : 250));
                REQUIRE(hits[hit_i].energy == Approx(expected_energies[hit_i]));
            }
        }
    }

    SECTION("Under the campaign tag both runs get the 2022 gains")
    {
        // jana2_campaign is default at 2022-01-01: gains 1.0, 0.1 | 2.0, 0.2 for every run
        auto hits = RunJob({{"ccdb:tag", "jana2_campaign"}}, false);
        INFO(Describe(hits));
        REQUIRE(hits.size() == 8);
        for (size_t hit_i = 0; hit_i < hits.size(); hit_i++) {
            REQUIRE(hits[hit_i].energy == Approx(hit_i % 2 == 0 ? 10.1 : 20.2));
        }
    }
}
