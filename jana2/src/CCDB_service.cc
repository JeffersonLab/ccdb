// SPDX-License-Identifier: LGPL-3.0-or-later
// Copyright (C) 2026, Jefferson Science Associates, LLC.

#include "CCDB_service.h"

#include <JANA/JApplication.h>
#include <JANA/JLogger.h>

#include <CCDB/Helpers/EnvUtils.h>
#include <CCDB/Helpers/HttpDownload.h>
#include <CCDB/Helpers/PathUtils.h>
#include <CCDB/Helpers/StringUtils.h>
#include <CCDB/Helpers/TimeUtils.h>

#include "Sha256.h"

#include <cstdlib>
#include <filesystem>
#include <map>
#include <unistd.h>
#include <vector>

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
        "CCDB connection string (mysql://, sqlite://, http(s):// of the HTTP API); default $CCDB_CONNECTION, then $JANA_CALIB_URL");
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
        // local wall time to the UTC instant, to the microsecond; a prefix is the latest moment it covers
        m_time = ccdb::TimeUtils::ParseLocalTime(m_time_string, &parsed);
        if (!parsed) {
            throw JException("CCDB_service: can't read ccdb:time='%s'; use the form "
                             "YYYY-MM-DD hh:mm:ss.ffffff or a prefix of it (2025, 2025-06)", m_time_string.c_str());
        }
    }
}


void CCDB_service::Initialize() {
    if (!ccdb::CalibrationGenerator::CheckOpenable(m_url)) {
        if (m_url.rfind("mysql://", 0) == 0) {
            // eic-shell, for one, has no MySQL client library: a SQLite file is the way there
            throw JException("CCDB_service: '%s' is a MySQL connection string, and this CCDB library was built without "
                             "MySQL support. Use a SQLite file (sqlite:////path/ccdb.sqlite), or build CCDB where CMake "
                             "finds a MySQL or MariaDB client library", m_safe_url.c_str());
        }
        throw JException("CCDB_service: CCDB can't open connection string '%s' "
                         "(it supports mysql://, sqlite:// and, when built with libcurl, http(s):// of the HTTP API)", m_safe_url.c_str());
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
    return GetCalibrationForRun(run);
}


ccdb::Calibration* CCDB_service::GetCalibrationForRun(int run) {
    std::call_once(m_init_flag, &CCDB_service::Initialize, this);

    // The generator keeps one Calibration per (url, run, variation, time) or (url, run, tag) and is thread safe.
    // Under a tag the Calibration reads every request through it (Calibration::SetTag).
    try {
        if (!m_tag.empty()) return m_generator->MakeCalibrationForTag(m_url, run, m_tag);
        return m_generator->MakeCalibrationMicro(m_url, run, m_variation, m_time);
    } catch (std::exception& ex) {
        throw JException("CCDB_service: can't connect to %s for run %d: %s", m_safe_url.c_str(), run, ex.what());
    }
}


std::string CCDB_service::GetResource(int run, const std::string& table) {
    auto rows = GetConstants<std::vector<std::map<std::string, std::string>>>(run, table);
    if (rows.size() != 1) {
        throw JException("CCDB_service: resources table '%s' has %d rows for run %d; it must have one",
                         table.c_str(), (int)rows.size(), run);
    }
    const auto& row = rows[0];
    for (const char* column: {"url", "sha256", "size"}) {
        if (row.find(column) == row.end()) {
            throw JException("CCDB_service: resources table '%s' has no column '%s' (it needs url, sha256, size)", table.c_str(), column);
        }
    }
    const std::string& url = row.at("url");
    const std::string& expected_sha256 = row.at("sha256");
    bool size_parsed = false;
    long long expected_size = -1;
    try {
        size_t parsed_chars = 0;
        expected_size = std::stoll(row.at("size"), &parsed_chars);
        size_parsed = parsed_chars == row.at("size").size() && expected_size >= 0;
    } catch (std::exception&) {}
    if (!size_parsed) {
        throw JException("CCDB_service: resources table '%s': size '%s' is not a byte count", table.c_str(), row.at("size").c_str());
    }
    if (expected_sha256.size() != 64 || expected_sha256.find_first_not_of("0123456789abcdef") != std::string::npos) {
        throw JException("CCDB_service: resources table '%s': sha256 '%s' is not 64 lower-case hex characters",
                         table.c_str(), expected_sha256.c_str());
    }

    // Where the file comes from: file:///path or /path to copy, http(s)://host/path to download
    std::string source_path;
    bool is_http = url.rfind("http://", 0) == 0 || url.rfind("https://", 0) == 0;
    if (is_http) {
        source_path = url.substr(0, url.find_first_of("?#"));      // the file name comes from the path part
    } else if (url.rfind("file://", 0) == 0) {
        source_path = url.substr(7);
    } else if (!url.empty() && url[0] == '/') {
        source_path = url;
    } else {
        throw JException("CCDB_service: resource '%s' of table '%s': the url must be file:///path, an absolute "
                         "path, or http(s)://host/path", url.c_str(), table.c_str());
    }

    namespace fs = std::filesystem;
    std::string file_name = fs::path(source_path).filename().string();
    if (file_name.empty()) file_name = "resource";
    fs::path target = fs::path(m_cache_dir) / expected_sha256 / file_name;

    std::lock_guard<std::mutex> lock(m_resources_mutex);
    auto verified = m_verified_resources.find(expected_sha256);
    if (verified != m_verified_resources.end() && fs::exists(verified->second)) return verified->second;

    auto& log = GetLogger();
    std::error_code error;
    if (fs::exists(target, error)) {
        if ((long long)fs::file_size(target, error) == expected_size && ccdb_jana2::Sha256::OfFile(target.string()) == expected_sha256) {
            m_verified_resources[expected_sha256] = target.string();
            return target.string();
        }
        LOG_WARN(log) << "CCDB_service: cached " << target.string() << " does not match its sha256; fetching it again" << LOG_END;
        fs::remove(target, error);
    }

    // Checked after the cache: a build without libcurl still serves a cache that other jobs filled
    if (is_http && !ccdb::HttpDownload::Available()) {
        throw JException("CCDB_service: can't fetch resource '%s' of table '%s': this CCDB library was built without "
                         "HTTP support. Build CCDB where CMake finds libcurl (option CCDB_WITH_HTTP), or point the "
                         "table at a file:// URL", url.c_str(), table.c_str());
    }

    // Copy or download next to the target under a temporary name, check, then rename: a reader never sees half a file
    fs::create_directories(target.parent_path(), error);
    if (error) {
        throw JException("CCDB_service: can't create the cache directory '%s': %s", target.parent_path().string().c_str(), error.message().c_str());
    }
    fs::path partial = target;
    partial += ".part." + std::to_string(::getpid());
    if (is_http) {
        // CCDB_HTTP_TIMEOUT, the setting of the library's HTTP provider (docs/apis/cpp.md), bounds one download
        unsigned int timeout = ccdb::GetEnvPositiveUInt("CCDB_HTTP_TIMEOUT", 300, 86400);
        try {
            ccdb::HttpDownload::ToFile(url, partial.string(), timeout);
        } catch (std::exception& ex) {
            fs::remove(partial, error);
            throw JException("CCDB_service: can't fetch resource '%s' of table '%s' for run %d: %s",
                             url.c_str(), table.c_str(), run, ex.what());
        }
    } else {
        fs::copy_file(source_path, partial, fs::copy_options::overwrite_existing, error);
        if (error) {
            fs::remove(partial, error);
            throw JException("CCDB_service: can't fetch resource '%s' of table '%s' for run %d: %s",
                             url.c_str(), table.c_str(), run, error.message().c_str());
        }
    }

    long long actual_size = (long long)fs::file_size(partial, error);
    std::string actual_sha256 = ccdb_jana2::Sha256::OfFile(partial.string());
    if (actual_sha256 != expected_sha256 || actual_size != expected_size) {
        fs::remove(partial, error);
        throw JException("CCDB_service: resource '%s' of table '%s' does not match the table: sha256 %s, %lld bytes; "
                         "the table says sha256 %s, %lld bytes. The file is not kept",
                         url.c_str(), table.c_str(), actual_sha256.c_str(), actual_size, expected_sha256.c_str(), expected_size);
    }
    fs::rename(partial, target, error);
    if (error) {
        fs::remove(partial, error);
        throw JException("CCDB_service: can't move the fetched resource to '%s'", target.string().c_str());
    }

    LOG_INFO(log) << "CCDB_service: fetched " << url << " into " << target.string() << LOG_END;
    m_verified_resources[expected_sha256] = target.string();
    return target.string();
}
