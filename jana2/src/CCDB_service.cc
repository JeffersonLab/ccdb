// SPDX-License-Identifier: GPL-2.0-or-later
// Copyright (C) 2026, Jefferson Science Associates, LLC.

#include "CCDB_service.h"

#include <JANA/JApplication.h>
#include <JANA/JLogger.h>

#include <CCDB/Helpers/PathUtils.h>
#include <CCDB/Helpers/StringUtils.h>

#include <cstdlib>

namespace {

    std::string GetEnv(const char* name) {
        const char* value = std::getenv(name);
        return value ? value : "";
    }

    /// $CCDB_CONNECTION, then $JANA_CALIB_URL (the variable JANA's legacy calibration system reads)
    std::string DefaultUrl() {
        std::string url = GetEnv("CCDB_CONNECTION");
        return url.empty() ? GetEnv("JANA_CALIB_URL") : url;
    }

    std::string DefaultCacheDir() {
        std::string cache_home = GetEnv("XDG_CACHE_HOME");
        if (cache_home.empty()) {
            std::string home = GetEnv("HOME");
            cache_home = (home.empty() ? std::string("/tmp") : home) + "/.cache";
        }
        return cache_home + "/ccdb/resources";
    }
}


CCDB_service::~CCDB_service() {
    // The generator does not delete the Calibrations it made; the service owns them
    if (m_generator) m_generator->DeleteCalibrations();
}


void CCDB_service::Init() {
    m_url = DefaultUrl();
    m_cache_dir = DefaultCacheDir();

    m_app->SetDefaultParameter("ccdb:url", m_url,
        "CCDB connection string (mysql://, sqlite://); default $CCDB_CONNECTION, then $JANA_CALIB_URL");
    m_variation_param = m_app->SetDefaultParameter("ccdb:variation", m_variation,
        "CCDB variation of the constants");
    m_time_param = m_app->SetDefaultParameter("ccdb:time", m_time_string,
        "Newest constants as of this time, e.g. 2025 or 2025-06-30 12:00; empty = the newest");
    m_app->SetDefaultParameter("ccdb:tag", m_tag,
        "CCDB tag; it gives both the variation and the time, so it can't be set together with them");
    m_app->SetDefaultParameter("ccdb:cache_dir", m_cache_dir,
        "Directory where GetResource keeps the files it fetched");

    m_safe_url = ccdb::StringUtils::MaskPassword(m_url);

    if (m_url.empty()) {
        throw JException("CCDB_service: no connection string. Set the parameter ccdb:url "
                         "or the environment variable CCDB_CONNECTION (or JANA_CALIB_URL)");
    }

    if (!m_tag.empty()) {
        if (!ccdb::PathUtils::IsValidTagName(m_tag)) {
            throw JException("CCDB_service: ccdb:tag='%s' is not a valid tag name "
                             "(ASCII letters, digits and '_')", m_tag.c_str());
        }
        bool variation_set = m_variation_param != nullptr && !m_variation_param->IsDefault();
        bool time_set = m_time_param != nullptr && !m_time_param->IsDefault();
        if (variation_set || time_set) {
            throw JException("CCDB_service: ccdb:tag='%s' is set together with %s. A tag gives both the "
                             "variation and the time; set either the tag or the variation and time",
                             m_tag.c_str(), variation_set ? "ccdb:variation" : "ccdb:time");
        }
    }

    if (!m_time_string.empty()) {
        bool parsed = false;
        m_time = ccdb::PathUtils::ParseTime(m_time_string, &parsed);
        if (!parsed) {
            throw JException("CCDB_service: can't read ccdb:time='%s'; use the form "
                             "YYYY-MM-DD hh:mm:ss or a prefix of it (2025, 2025-06)", m_time_string.c_str());
        }
    }
}


void CCDB_service::Initialize() {
    if (!ccdb::CalibrationGenerator::CheckOpenable(m_url)) {
        throw JException("CCDB_service: CCDB can't open connection string '%s' "
                         "(it supports mysql:// and sqlite://)", m_safe_url.c_str());
    }
    m_generator = std::make_unique<ccdb::CalibrationGenerator>();

    auto& log = GetLogger();
    if (m_tag.empty()) {
        LOG_INFO(log) << "CCDB_service: " << m_safe_url << ", variation '" << m_variation << "', time '"
                      << (m_time_string.empty() ? "newest" : m_time_string) << "'" << LOG_END;
    } else {
        LOG_INFO(log) << "CCDB_service: " << m_safe_url << ", tag '" << m_tag << "'" << LOG_END;
    }
}


ccdb::Calibration* CCDB_service::GetCalibration(int run) {
    if (!m_tag.empty()) {
        throw JException("CCDB_service: GetCalibration(run) is not available with ccdb:tag='%s': a Calibration "
                         "has no default tag and would read untagged constants. Use GetConstants", m_tag.c_str());
    }
    return GetCalibrationForRun(run);
}


ccdb::Calibration* CCDB_service::GetCalibrationForRun(int run) {
    std::call_once(m_init_flag, &CCDB_service::Initialize, this);

    // The generator keeps one Calibration per (url, run, variation, time) and is thread safe.
    // Under a tag the variation and the time come from the tag, which ApplyTag puts into each request.
    try {
        return m_generator->MakeCalibration(m_url, run, m_variation, m_time);
    } catch (std::exception& ex) {
        throw JException("CCDB_service: can't connect to %s for run %d: %s", m_safe_url.c_str(), run, ex.what());
    }
}


std::string CCDB_service::ApplyTag(const std::string& request) const {
    if (m_tag.empty() || request.find('@') != std::string::npos) return request;
    return request + "@" + m_tag;
}
