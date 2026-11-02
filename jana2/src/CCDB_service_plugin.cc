// SPDX-License-Identifier: LGPL-3.0-or-later
// Copyright (C) 2026, Jefferson Science Associates, LLC.
//
// The JANA2 plugin CCDB_service: loading it (-Pplugins=CCDB_service) provides the service to every factory

#include <JANA/JApplication.h>

#include "CCDB_service.h"

extern "C" {
void InitPlugin(JApplication* app) {
    InitJANAPlugin(app);
    app->ProvideService(std::make_shared<CCDB_service>(app));
}
}
