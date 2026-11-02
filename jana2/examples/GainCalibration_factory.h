// SPDX-License-Identifier: LGPL-3.0-or-later
// Copyright (C) 2026, Jefferson Science Associates, LLC.
//
// The example of a factory that takes its constants from CCDB, in the EICrecon factory layout:
// ChangeRun() reads the table of the new run through CCDB_service and pushes the values into the
// algorithm's configuration; Execute() only uses them. The table path is a factory parameter
// (<factory tag>:table), so a job can point the factory at another table without a rebuild.

#pragma once

#include <JANA/Components/JOmniFactory.h>
#include <JANA/JLogger.h>

#include "CCDB_service.h"
#include "GainCalibration.h"

#include <map>
#include <memory>
#include <string>
#include <vector>

namespace ccdb_example {

class GainCalibration_factory : public JOmniFactory<GainCalibration_factory, GainCalibrationConfig> {
private:
    GainCalibration m_algo;

    Input<RawHit> m_raw_hits_input{this};
    jana::components::Output<CalibratedHit> m_calibrated_hits_output{this};

    ParameterRef<std::string> m_table{this, "table", config().table, "CCDB table with the columns gain, offset, channel"};

    Service<CCDB_service> m_ccdb{this};

public:
    void Configure() {
        m_algo.applyConfig(config());
    }

    void ChangeRun(int32_t run_number) override {
        // One row per channel. The service returns the constants of this run under the job's
        // variation and time, or its tag (ccdb:variation, ccdb:time, ccdb:tag)
        auto rows = m_ccdb->GetConstants<std::vector<std::map<std::string, double>>>(run_number, config().table);

        config().gains.clear();
        config().offsets.clear();
        for (const auto& row: rows) {
            int channel = static_cast<int>(row.at("channel"));
            config().gains[channel] = row.at("gain");
            config().offsets[channel] = row.at("offset");
        }
        m_algo.applyConfig(config());
        LOG_DEBUG(logger()) << "Run " << run_number << ": " << rows.size() << " channels from " << config().table << LOG_END;
    }

    void Execute(int32_t /* run_number */, uint64_t /* event_number */) {
        m_algo.process(m_raw_hits_input(), m_calibrated_hits_output());
    }
};

} // namespace ccdb_example
