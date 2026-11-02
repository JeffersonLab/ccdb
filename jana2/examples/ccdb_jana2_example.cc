// SPDX-License-Identifier: GPL-2.0-or-later
// Copyright (C) 2026, Jefferson Science Associates, LLC.
//
// The plugin of the CCDB_service example: GainCalibration_factory turns "raw_hits" into "calibrated_hits".
// Load it together with the service: -Pplugins=CCDB_service,ccdb_jana2_example

#include <JANA/JApplication.h>
#include <JANA/Components/JOmniFactoryGeneratorT.h>

#include "GainCalibration_factory.h"

extern "C" {
void InitPlugin(JApplication* app) {
    InitJANAPlugin(app);
    app->Add(new JOmniFactoryGeneratorT<ccdb_example::GainCalibration_factory>(
        "calibrated_hits", {"raw_hits"}, {"calibrated_hits"}));
}
}
