#ifndef CCDB_HTTP_DOWNLOAD_H
#define CCDB_HTTP_DOWNLOAD_H

#include <string>

namespace ccdb
{
/** @brief One HTTP(S) download into a file, with the libcurl the library's HTTP provider uses.
 *
 * For consumers that keep files outside CCDB and record their URLs in it (the JANA2 service's resources
 * tables): they need no HTTP stack of their own. The library has the functions always; they work when
 * it was built with libcurl (CMake option CCDB_WITH_HTTP), and Available() tells.
 */
class HttpDownload
{
public:
    /** @brief True when this build of the library can download (it was built with libcurl) */
    static bool Available();

    /** @brief Downloads url (http:// or https://) into the file at path.
     *
     * The body is streamed into the file, never kept in memory; redirects are followed (at most 5).
     * The whole transfer must finish within timeoutSeconds (0 = no limit); connecting gives up after
     * 30 s at most. The file is written only by a 200 answer. On any failure (not Available(), the file
     * can't be written, a network error, a timeout, an answer other than 200) the file is removed and
     * std::runtime_error names the URL and the reason.
     */
    static void ToFile(const std::string& url, const std::string& path, unsigned int timeoutSeconds = 300);
};
}

#endif // CCDB_HTTP_DOWNLOAD_H
