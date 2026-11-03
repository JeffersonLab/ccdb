#ifndef _HTTPDataProvider_
#define _HTTPDataProvider_

#include <stdint.h>
#include <string>

#include "CCDB/Providers/SQLiteDataProvider.h"

namespace ccdb
{
/** @brief Reads constants through the CCDB HTTP API (docs/apis/http.md): http://host/api/v1 or https://….
 *
 * Connect downloads the run bundle of one run, a SQLite file with the constants of that run, by variation and
 * time or by tag, and every read is then the SQLite provider's on that file. The file goes to the cache directory
 * (CCDB_HTTP_CACHE_DIR, default $HOME/.cache/ccdb) and is kept only when its SHA-256 equals the X-CCDB-SHA256
 * header the API sends. A bundle by time or by tag names one set of constants, so a cached one is used without
 * asking the server; the newest constants (time 0) need the server, which redirects to the explicit time.
 * CCDB_HTTP_TIMEOUT limits a download, in seconds (default 300).
 *
 * The bundle holds one run: a request for another run finds no constants. CalibrationGenerator creates this
 * provider for an http:// or https:// connection string.
 */
class HTTPDataProvider: public SQLiteDataProvider
{
public:
    /** @param run, variation, timeMicro the bundle by time (timeMicro UTC microseconds, 0 the newest)
     *  @param tag the bundle by tag instead, when not empty (the variation and time are then the tag's) */
    HTTPDataProvider(int run, const std::string& variation, int64_t timeMicro, const std::string& tag = "");

    /** @brief Downloads the bundle, or finds it in the cache, and opens it. url is the API base, http(s)://host/api/v1 */
    void Connect(const std::string& url) override;

    /** @brief The local file of the bundle, after Connect */
    const std::string& GetBundlePath() const { return mBundlePath; }

    /** @brief True for an http:// or https:// connection string */
    static bool IsHttpUrl(const std::string& connectionString);

private:
    std::string FetchBundle(const std::string& url);

    int mRun;
    std::string mVariation;
    int64_t mTimeMicro;
    std::string mTag;
    std::string mBundlePath;
};
}

#endif // _HTTPDataProvider_
