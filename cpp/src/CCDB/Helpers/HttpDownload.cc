#include "CCDB/Helpers/HttpDownload.h"

#include <stdexcept>

#ifdef CCDB_HTTP

#include <curl/curl.h>

#include <cerrno>
#include <cstdio>
#include <cstring>
#include <mutex>

namespace
{
    std::once_flag curlInitialized;

    struct Transfer
    {
        CURL* curl;
        FILE* file;
        std::string errorBody;      ///< the body of an answer other than 200, for the error message
    };

    size_t OnHeader(char* buffer, size_t size, size_t count, void* data)
    {
        Transfer* transfer = static_cast<Transfer*>(data);
        if (size * count >= 5 && std::strncmp(buffer, "HTTP/", 5) == 0) {    // a new answer, after a redirect
            transfer->errorBody.clear();
        }
        return size * count;
    }

    size_t OnBody(char* buffer, size_t size, size_t count, void* data)
    {
        Transfer* transfer = static_cast<Transfer*>(data);
        size_t bytes = size * count;
        long status = 0;
        curl_easy_getinfo(transfer->curl, CURLINFO_RESPONSE_CODE, &status);
        if (status != 200) {                                 // a redirect or an error: the text, not the file
            if (transfer->errorBody.size() < 2000) transfer->errorBody.append(buffer, bytes);
            return bytes;
        }
        return std::fwrite(buffer, 1, bytes, transfer->file);   // a short write (disk full) stops the transfer
    }

    // A text body as one short line for the error message; an HTML page (a web server's own error page) says nothing
    std::string Excerpt(const std::string& body)
    {
        std::string line;
        for (size_t i = 0; i < body.size() && line.size() < 200; i++) {
            char c = body[i];
            bool space = c == ' ' || c == '\t' || c == '\r' || c == '\n';
            if (space && (line.empty() || line[line.size() - 1] == ' ')) continue;
            line += space ? ' ' : c;
        }
        if (!line.empty() && line[line.size() - 1] == ' ') line.erase(line.size() - 1);
        if (!line.empty() && line[0] == '<') return "";
        return line;
    }

    // Why the download failed, "" when it succeeded. The file is open on entry and closed on return
    std::string Perform(const std::string& url, Transfer& transfer, unsigned int timeoutSeconds)
    {
        char error[CURL_ERROR_SIZE] = "";
        curl_easy_setopt(transfer.curl, CURLOPT_URL, url.c_str());
        curl_easy_setopt(transfer.curl, CURLOPT_FOLLOWLOCATION, 1L);
        curl_easy_setopt(transfer.curl, CURLOPT_MAXREDIRS, 5L);
        curl_easy_setopt(transfer.curl, CURLOPT_TIMEOUT, static_cast<long>(timeoutSeconds));
        curl_easy_setopt(transfer.curl, CURLOPT_CONNECTTIMEOUT, static_cast<long>(timeoutSeconds != 0 && timeoutSeconds < 30 ? timeoutSeconds : 30));
        curl_easy_setopt(transfer.curl, CURLOPT_NOSIGNAL, 1L);        // timeouts without signals, for threads
        curl_easy_setopt(transfer.curl, CURLOPT_USERAGENT, "ccdb-cpp/2.5");
        curl_easy_setopt(transfer.curl, CURLOPT_ERRORBUFFER, error);
        curl_easy_setopt(transfer.curl, CURLOPT_HEADERFUNCTION, OnHeader);
        curl_easy_setopt(transfer.curl, CURLOPT_HEADERDATA, &transfer);
        curl_easy_setopt(transfer.curl, CURLOPT_WRITEFUNCTION, OnBody);
        curl_easy_setopt(transfer.curl, CURLOPT_WRITEDATA, &transfer);
#if LIBCURL_VERSION_NUM >= 0x075500
        curl_easy_setopt(transfer.curl, CURLOPT_PROTOCOLS_STR, "http,https");
        curl_easy_setopt(transfer.curl, CURLOPT_REDIR_PROTOCOLS_STR, "http,https");
#endif

        CURLcode code = curl_easy_perform(transfer.curl);
        long status = 0;
        curl_easy_getinfo(transfer.curl, CURLINFO_RESPONSE_CODE, &status);
        bool written = std::fclose(transfer.file) == 0;
        transfer.file = nullptr;

        if (code != CURLE_OK) return *error ? error : curl_easy_strerror(code);
        if (status != 200) {
            std::string body = Excerpt(transfer.errorBody);
            return "the server answered " + std::to_string(status) + (body.empty() ? "" : ": " + body);
        }
        if (!written) return std::string("writing the file failed: ") + std::strerror(errno);
        return "";
    }
}

namespace ccdb
{
bool HttpDownload::Available()
{
    return true;
}


void HttpDownload::ToFile(const std::string& url, const std::string& path, unsigned int timeoutSeconds)
{
    if (url.compare(0, 7, "http://") != 0 && url.compare(0, 8, "https://") != 0) {
        throw std::runtime_error("CCDB HTTP download: '" + url + "' is not an http:// or https:// URL");
    }
    std::call_once(curlInitialized, []() { curl_global_init(CURL_GLOBAL_DEFAULT); });

    Transfer transfer;
    transfer.curl = curl_easy_init();
    if (!transfer.curl) throw std::runtime_error("CCDB HTTP download: cannot get '" + url + "': curl_easy_init failed");
    transfer.file = std::fopen(path.c_str(), "wb");
    if (!transfer.file) {
        std::string reason = std::strerror(errno);
        curl_easy_cleanup(transfer.curl);
        throw std::runtime_error("CCDB HTTP download: cannot get '" + url + "': cannot write '" + path + "': " + reason);
    }

    std::string failure = Perform(url, transfer, timeoutSeconds);
    curl_easy_cleanup(transfer.curl);
    if (!failure.empty()) {
        std::remove(path.c_str());
        throw std::runtime_error("CCDB HTTP download: cannot get '" + url + "': " + failure);
    }
}
}

#else // no libcurl in this build

namespace ccdb
{
bool HttpDownload::Available()
{
    return false;
}


void HttpDownload::ToFile(const std::string& url, const std::string&, unsigned int)
{
    throw std::runtime_error("CCDB HTTP download: cannot get '" + url + "': this CCDB library was built without "
                             "HTTP support (libcurl; CMake option CCDB_WITH_HTTP)");
}
}

#endif // CCDB_HTTP
