// SPDX-License-Identifier: LGPL-3.0-or-later
// Copyright (C) 2026, Jefferson Science Associates, LLC.
//
// ccdb_epic_demo: a standalone JANA2 application that reads ePIC-shaped calibration tables through CCDB_service
// (docs/get-started/demo.md). An event source emits two events of run 500 and two of run 1500; at each run change a
// processor reads the barrel TOF calibration and the hadron calorimeter ADC constants and prints them. Run it once by
// variation and time, once by a campaign tag:
//
//     ccdb_epic_demo sqlite:////path/epic_demo.sqlite
//     ccdb_epic_demo mysql://ccdb_user@127.0.0.1:3306/ccdb_demo campaign_demo
//
// The tables come from scripts/demo/make_epic_tables.py. Exit code 0 when every read succeeds.
#include <JANA/JApplication.h>
#include <JANA/JEventProcessor.h>
#include <JANA/JEventSource.h>

#include "CCDB_service.h"

#include <cstdio>
#include <iostream>
#include <map>
#include <memory>
#include <mutex>
#include <string>
#include <vector>

namespace {

    /// Four events: two of run 500, then two of run 1500
    class TwoRunSource : public JEventSource {
    public:
        TwoRunSource() {
            SetTypeName("TwoRunSource");
            SetCallbackStyle(CallbackStyle::ExpertMode);
        }

        Result Emit(JEvent& event) override {
            if (m_emitted == 4) return Result::FailureFinished;
            event.SetEventNumber(m_emitted + 1);
            event.SetRunNumber(m_emitted < 2 ? 500 : 1500);
            m_emitted++;
            return Result::Success;
        }

    private:
        int m_emitted = 0;
    };

    /// Reads and prints the tables once per run, as a factory's ChangeRun would
    class CalibrationPrinter : public JEventProcessor {
    public:
        explicit CalibrationPrinter(std::shared_ptr<CCDB_service> service) : m_service(std::move(service)) {
            SetTypeName("CalibrationPrinter");
            SetCallbackStyle(CallbackStyle::ExpertMode);
        }

        void ProcessSequential(const JEvent& event) override {
            const int run = static_cast<int>(event.GetRunNumber());
            if (run == m_last_run) return;
            m_last_run = run;

            auto tof = m_service->GetConstants<std::map<std::string, double>>(run, "/epic/TOFBarrel/lgad_calibration");
            std::printf("run %d  /epic/TOFBarrel/lgad_calibration  cSlope=%.10g  tSlope=%.10g  tIntercept=%.10g\n",
                        run, tof["cSlope"], tof["tSlope"], tof["tIntercept"]);

            auto hcal = m_service->GetConstants<std::vector<std::map<std::string, std::string>>>(run, "/epic/HCal/adc_calib");
            for (auto& row: hcal) {
                std::printf("run %d  /epic/HCal/adc_calib  %-18s sampFrac=%s\n", run, row["detector"].c_str(), row["sampFrac"].c_str());
            }
        }

    private:
        std::shared_ptr<CCDB_service> m_service;
        int m_last_run = -1;
    };
}


int main(int argc, char* argv[]) {
    if (argc < 2) {
        std::cerr << "Usage: ccdb_epic_demo <connection string> [tag]" << std::endl;
        return 2;
    }
    JApplication app;
    app.SetParameterValue("jana:loglevel", "warn");
    app.SetParameterValue("nthreads", 1);
    app.SetParameterValue("ccdb:url", std::string(argv[1]));
    if (argc > 2) app.SetParameterValue("ccdb:tag", std::string(argv[2]));

    auto service = std::make_shared<CCDB_service>(&app);
    app.ProvideService(service);
    app.Add(new TwoRunSource());
    app.Add(new CalibrationPrinter(service));
    std::printf("ccdb_epic_demo: %s%s\n", argv[1], argc > 2 ? (std::string(", tag ") + argv[2]).c_str() : ", variation default, newest");
    app.Run();
    return app.GetExitCode();
}
