// SPDX-License-Identifier: LGPL-3.0-or-later
// Copyright (C) 2026, Jefferson Science Associates, LLC.
//
// The algorithm of the CCDB_service example: energy = gain * adc + offset per channel. Like an EICrecon
// algorithm it knows nothing about JANA2 or CCDB; its factory fills the configuration (GainCalibration_factory.h).

#pragma once

#include <map>
#include <stdexcept>
#include <string>
#include <vector>

namespace ccdb_example {

struct RawHit {
    int channel;
    double adc;
};

struct CalibratedHit {
    int channel;
    double energy;
};

struct GainCalibrationConfig {
    std::string table = "/test/jana2/gains";   ///< CCDB table with the columns gain, offset and channel
    std::map<int, double> gains;               ///< by channel; filled from the table for each run
    std::map<int, double> offsets;
};

class GainCalibration {
public:
    void applyConfig(const GainCalibrationConfig& config) { m_config = config; }

    void process(const std::vector<const RawHit*>& raw_hits, std::vector<CalibratedHit*>& calibrated_hits) const {
        for (const RawHit* hit: raw_hits) {
            auto gain = m_config.gains.find(hit->channel);
            if (gain == m_config.gains.end()) {
                throw std::runtime_error("GainCalibration: no gain for channel " + std::to_string(hit->channel) +
                                         " in " + m_config.table);
            }
            double energy = gain->second * hit->adc + m_config.offsets.at(hit->channel);
            calibrated_hits.push_back(new CalibratedHit{hit->channel, energy});
        }
    }

private:
    GainCalibrationConfig m_config;
};

} // namespace ccdb_example
