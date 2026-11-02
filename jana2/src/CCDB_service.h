// SPDX-License-Identifier: GPL-2.0-or-later
// Copyright (C) 2026, Jefferson Science Associates, LLC.
//
// CCDB_service: calibration constants from CCDB for JANA2 factories, in the EICrecon service style
// (a JService that takes the application, declares its parameters under one prefix and connects once,
// on first use). A factory reads the constants for the run in ChangeRun():
//
//     Service<CCDB_service> m_ccdb{this};
//     void ChangeRun(int32_t run) {
//         auto gains = m_ccdb->GetConstants<std::vector<std::vector<double>>>(run, "/calorimeter/gains");
//     }
//
// Parameters (all under "ccdb:"):
//     ccdb:url        connection string; default $CCDB_CONNECTION, then $JANA_CALIB_URL
//     ccdb:variation  variation of the constants; default "default"
//     ccdb:time       newest constants as of this time ("2025", "2025-06-30 12:00"); default empty = newest
//     ccdb:tag        a CCDB tag: it gives both variation and time, so it can't be set with them
//     ccdb:cache_dir  where GetResource keeps fetched files; default $XDG_CACHE_HOME/ccdb/resources
//                     or $HOME/.cache/ccdb/resources

#pragma once

#include <JANA/JApplicationFwd.h>
#include <JANA/JServiceFwd.h>
#include <JANA/JException.h>

#include <CCDB/Calibration.h>
#include <CCDB/CalibrationGenerator.h>
#include <CCDB/Helpers/StringUtils.h>

#include <ctime>
#include <map>
#include <memory>
#include <mutex>
#include <string>

class JParameter;

class CCDB_service : public JService {
public:
    explicit CCDB_service(JApplication* app) : m_app(app) {}
    ~CCDB_service() override;

    /// The constants of a table for a run, as Calibration::GetCalib gives them under this service's
    /// variation and time, or under its tag.
    ///
    /// T is any type Calibration::GetCalib fills: vector<vector<double|int|string>> (rows of columns),
    /// vector<map<string, double|int|string>> (rows by column name), map<string, ...> and vector<...>
    /// (one row), double, int or string (the first value). The request is a CCDB request; it may name
    /// its own run, variation or time ("/path/to/table:100:mc"), as with GetCalib.
    /// Throws JException when the table or its constants for the run don't exist.
    template <typename T>
    T GetConstants(int run, const std::string& request) {
        T values;
        const std::string full_request = ApplyTag(request);
        bool found = false;
        try {
            found = GetCalibrationForRun(run)->GetCalib(values, full_request);
        } catch (std::exception& ex) {
            throw JException("CCDB_service: request '%s' for run %d failed: %s", full_request.c_str(), run, ex.what());
        }
        if (!found) {
            throw JException("CCDB_service: no constants for request '%s' and run %d in %s",
                             full_request.c_str(), run, m_safe_url.c_str());
        }
        return values;
    }

    /// The Calibration of a run under ccdb:variation and ccdb:time: one object per run, created on first use
    /// and owned by the service. It is for code that wants the CCDB C++ API itself (GetAssignment, the
    /// listing calls). With ccdb:tag set this throws: a Calibration has no default tag, so its GetCalib
    /// would silently read the newest constants of the default variation. Use GetConstants then.
    ccdb::Calibration* GetCalibration(int run);

    /// A file that a resources table points to, fetched into ccdb:cache_dir and verified, as a local path.
    ///
    /// The table has one row with the columns url, sha256 (64 hex characters) and size (bytes); CCDB holds
    /// these, not the file itself (model weights, field maps). The file is fetched once: the path is
    /// <cache_dir>/<sha256>/<file name of the url>, so jobs that share a cache directory share the file, and a
    /// file already there is checked against the hash once per service and fetched again when it differs.
    /// A fetched file with another hash or size is removed and is an error. URLs: file:///path and plain
    /// absolute paths; http(s) is not supported yet (ccdb-2.5 Q52).
    std::string GetResource(int run, const std::string& table);

    /// The values of the service's parameters after JANA applied the user's settings
    const std::string& GetUrl() const { return m_url; }
    const std::string& GetVariation() const { return m_variation; }
    const std::string& GetTimeString() const { return m_time_string; }
    const std::string& GetTag() const { return m_tag; }
    const std::string& GetCacheDir() const { return m_cache_dir; }

protected:
    /// Declares the parameters and checks them, so a wrong setting fails when the application starts
    void Init() override;

private:
    CCDB_service() = default;

    /// Connects once, on the first request: validates the parameters and creates the generator
    void Initialize();

    ccdb::Calibration* GetCalibrationForRun(int run);

    /// "/path" -> "/path@tag" when ccdb:tag is set and the request names no tag itself
    std::string ApplyTag(const std::string& request) const;

    std::once_flag m_init_flag;
    JApplication* m_app = nullptr;

    std::string m_url;
    std::string m_safe_url;          ///< m_url with the password masked, for log lines and errors
    std::string m_variation = "default";
    std::string m_time_string;
    std::string m_tag;
    std::string m_cache_dir;
    time_t m_time = 0;               ///< m_time_string parsed; 0 = newest

    JParameter* m_variation_param = nullptr;   ///< kept to know whether the user set it (a tag excludes it)
    JParameter* m_time_param = nullptr;

    std::unique_ptr<ccdb::CalibrationGenerator> m_generator;

    std::mutex m_resources_mutex;                         ///< one fetch at a time per service
    std::map<std::string, std::string> m_verified_resources;  ///< sha256 -> path checked by this service
};


// Calibration::GetCalib(double&) and GetCalib(int&) fill the value but return false (CCDB up to 2.5.0, finding
// F25), so a single number is read as text and converted the way those two functions convert it
template <>
inline double CCDB_service::GetConstants<double>(int run, const std::string& request) {
    return ccdb::StringUtils::ParseDouble(GetConstants<std::string>(run, request));
}

template <>
inline int CCDB_service::GetConstants<int>(int run, const std::string& request) {
    return ccdb::StringUtils::ParseInt(GetConstants<std::string>(run, request));
}
