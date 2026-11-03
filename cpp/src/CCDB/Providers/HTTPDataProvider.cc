#include "CCDB/Providers/HTTPDataProvider.h"

#include "CCDB/Helpers/EnvUtils.h"
#include "CCDB/Helpers/Sha256.h"
#include "CCDB/Helpers/TimeUtils.h"

#include <curl/curl.h>

#include <atomic>
#include <cctype>
#include <cerrno>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <mutex>
#include <stdexcept>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

using namespace std;

namespace
{
    const char* SHA256_HEADER = "x-ccdb-sha256";
    const unsigned int DEFAULT_TIMEOUT_S = 300;
    std::once_flag curlInitialized;
    std::atomic<unsigned int> partCounter(0);

    bool IsUnreserved(unsigned char c)
    {
        return (c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') ||
               c == '-' || c == '_' || c == '.' || c == '~';
    }

    // Percent-encoding with the unreserved characters as they are; keep lists characters that also stay
    string Escape(const string& text, const char* keep = "")
    {
        static const char digits[] = "0123456789ABCDEF";
        string result;
        for (size_t i = 0; i < text.size(); i++) {
            unsigned char c = static_cast<unsigned char>(text[i]);
            if (IsUnreserved(c) || (c != 0 && strchr(keep, c))) {
                result += static_cast<char>(c);
            } else {
                result += '%';
                result += digits[c >> 4];
                result += digits[c & 0xf];
            }
        }
        return result;
    }

    // A file or directory name made from any text: letters, digits and '.-_~' as they are, any other byte
    // as +XX, so two texts never give one name
    string CacheName(const string& text)
    {
        string name = Escape(text);
        for (size_t i = 0; i < name.size(); i++) {
            if (name[i] == '%') name[i] = '+';
        }
        return name;
    }

    // A bundle time in a file name, as the API names its own files: 20240301T120000600000Z
    string CompactTime(const string& text)
    {
        string compact;
        for (size_t i = 0; i < text.size(); i++) {
            if (isalnum(static_cast<unsigned char>(text[i]))) compact += text[i];
        }
        return compact + "Z";
    }

    int HexValue(char c)
    {
        if (c >= '0' && c <= '9') return c - '0';
        if (c >= 'a' && c <= 'f') return c - 'a' + 10;
        if (c >= 'A' && c <= 'F') return c - 'A' + 10;
        return -1;
    }

    // The decoded value of one query parameter of a URL, "" when it is absent
    string QueryParameter(const string& url, const string& name)
    {
        size_t query = url.find('?');
        if (query == string::npos) return "";
        string rest = url.substr(query + 1);
        size_t start = 0;
        while (start <= rest.size()) {
            size_t end = rest.find('&', start);
            if (end == string::npos) end = rest.size();
            string pair = rest.substr(start, end - start);
            size_t equals = pair.find('=');
            if (equals != string::npos && pair.substr(0, equals) == name) {
                string value = pair.substr(equals + 1), decoded;
                for (size_t i = 0; i < value.size(); i++) {
                    if (value[i] == '%' && i + 2 < value.size() && HexValue(value[i + 1]) >= 0 && HexValue(value[i + 2]) >= 0) {
                        decoded += static_cast<char>(HexValue(value[i + 1]) * 16 + HexValue(value[i + 2]));
                        i += 2;
                    } else {
                        decoded += value[i] == '+' ? ' ' : value[i];
                    }
                }
                return decoded;
            }
            start = end + 1;
        }
        return "";
    }

    // The time of a bundle URL as the API reads it: UTC, YYYY-MM-DDThh:mm:ss.ffffff
    string TimeText(int64_t micro)
    {
        string text = ccdb::TimeUtils::FormatUtc(micro);
        if (text.size() > 10) text[10] = 'T';
        return text;
    }

    void MakeDirectories(const string& path)
    {
        for (size_t slash = path.find('/', 1); ; slash = path.find('/', slash + 1)) {
            string part = slash == string::npos ? path : path.substr(0, slash);
            if (!part.empty() && mkdir(part.c_str(), 0755) != 0 && errno != EEXIST) {
                throw runtime_error("CCDB HTTP: cannot create the cache directory '" + part + "': " + strerror(errno) +
                                    ". Set CCDB_HTTP_CACHE_DIR to a writable directory");
            }
            if (slash == string::npos) break;
        }
        struct stat info;
        if (stat(path.c_str(), &info) != 0 || !S_ISDIR(info.st_mode) || access(path.c_str(), W_OK) != 0) {
            throw runtime_error("CCDB HTTP: the cache directory '" + path + "' is not a writable directory. "
                                "Set CCDB_HTTP_CACHE_DIR to a writable directory");
        }
    }

    bool FileExists(const string& path)
    {
        struct stat info;
        return stat(path.c_str(), &info) == 0 && S_ISREG(info.st_mode);
    }

    string Trim(const string& text)
    {
        size_t begin = text.find_first_not_of(" \t\r\n");
        if (begin == string::npos) return "";
        return text.substr(begin, text.find_last_not_of(" \t\r\n") - begin + 1);
    }

    struct Download
    {
        CURL* curl;
        FILE* file;
        ccdb::Sha256 hash;
        string sha256Header;
        string errorBody;
    };

    size_t OnHeader(char* buffer, size_t size, size_t count, void* data)
    {
        Download* download = static_cast<Download*>(data);
        string line(buffer, size * count);
        if (line.compare(0, 5, "HTTP/") == 0) {             // a new response, after a redirect
            download->sha256Header.clear();
            download->errorBody.clear();
        }
        size_t colon = line.find(':');
        if (colon != string::npos) {
            string name = Trim(line.substr(0, colon));
            for (size_t i = 0; i < name.size(); i++) name[i] = static_cast<char>(tolower(name[i]));
            if (name == SHA256_HEADER) download->sha256Header = Trim(line.substr(colon + 1));
        }
        return size * count;
    }

    size_t OnBody(char* buffer, size_t size, size_t count, void* data)
    {
        Download* download = static_cast<Download*>(data);
        size_t bytes = size * count;
        long status = 0;
        curl_easy_getinfo(download->curl, CURLINFO_RESPONSE_CODE, &status);
        if (status != 200 || download->file == nullptr) {    // a redirect or an error: the text, not the file
            if (download->errorBody.size() < 2000) download->errorBody.append(buffer, bytes);
            return bytes;
        }
        download->hash.Update(buffer, bytes);
        return fwrite(buffer, 1, bytes, download->file);     // a short write (disk full) stops the transfer
    }

    struct Response
    {
        long status;
        string redirect;      ///< the Location of a redirect, resolved
        string failure;       ///< why the answer is not a good bundle (or redirect); empty when it is
    };

    // One GET. With a file, redirects are followed, and the 200 answer's body goes to the file, whose SHA-256 must
    // equal the X-CCDB-SHA256 header; without one, the redirect is not followed and is the only good answer
    Response Get(const string& url, const string& file)
    {
        std::call_once(curlInitialized, []() { curl_global_init(CURL_GLOBAL_DEFAULT); });
        Response response;
        response.status = 0;
        Download download;
        download.curl = curl_easy_init();
        download.file = file.empty() ? nullptr : fopen(file.c_str(), "wb");
        if (!download.curl || (!file.empty() && !download.file)) {
            response.failure = download.curl ? "cannot write '" + file + "': " + strerror(errno) : "curl_easy_init failed";
            if (download.curl) curl_easy_cleanup(download.curl);
            if (download.file) fclose(download.file);
            return response;
        }

        unsigned int timeout = ccdb::GetEnvPositiveUInt("CCDB_HTTP_TIMEOUT", DEFAULT_TIMEOUT_S, 86400);
        char error[CURL_ERROR_SIZE] = "";
        curl_easy_setopt(download.curl, CURLOPT_URL, url.c_str());
        curl_easy_setopt(download.curl, CURLOPT_FOLLOWLOCATION, file.empty() ? 0L : 1L);
        curl_easy_setopt(download.curl, CURLOPT_MAXREDIRS, 5L);
        curl_easy_setopt(download.curl, CURLOPT_TIMEOUT, static_cast<long>(timeout));
        curl_easy_setopt(download.curl, CURLOPT_CONNECTTIMEOUT, static_cast<long>(timeout < 30 ? timeout : 30));
        curl_easy_setopt(download.curl, CURLOPT_NOSIGNAL, 1L);        // timeouts without signals, for threads
        curl_easy_setopt(download.curl, CURLOPT_USERAGENT, "ccdb-cpp/2.5");
        curl_easy_setopt(download.curl, CURLOPT_ERRORBUFFER, error);
        curl_easy_setopt(download.curl, CURLOPT_HEADERFUNCTION, OnHeader);
        curl_easy_setopt(download.curl, CURLOPT_HEADERDATA, &download);
        curl_easy_setopt(download.curl, CURLOPT_WRITEFUNCTION, OnBody);
        curl_easy_setopt(download.curl, CURLOPT_WRITEDATA, &download);

        CURLcode code = curl_easy_perform(download.curl);
        char* redirect = nullptr;
        curl_easy_getinfo(download.curl, CURLINFO_RESPONSE_CODE, &response.status);
        curl_easy_getinfo(download.curl, CURLINFO_REDIRECT_URL, &redirect);
        if (redirect) response.redirect = redirect;
        curl_easy_cleanup(download.curl);
        bool written = download.file == nullptr || fclose(download.file) == 0;

        if (code != CURLE_OK) {
            response.failure = *error ? error : curl_easy_strerror(code);
        } else if (file.empty()) {
            if (response.redirect.empty()) response.failure = "the server answered " + to_string(response.status) + ": " + Trim(download.errorBody);
        } else if (response.status != 200) {
            response.failure = "the server answered " + to_string(response.status) + ": " + Trim(download.errorBody);
        } else if (!written) {
            response.failure = "writing '" + file + "' failed";
        } else if (download.sha256Header.empty()) {
            response.failure = "the server sent no X-CCDB-SHA256 header";
        } else {
            string actual = download.hash.HexDigest();
            if (actual != download.sha256Header) {
                response.failure = "SHA-256 mismatch: the server sent " + download.sha256Header + ", the file has " + actual + "; the file is not kept";
            }
        }
        return response;
    }
}

namespace ccdb
{
HTTPDataProvider::HTTPDataProvider(int run, const std::string& variation, int64_t timeMicro, const std::string& tag):
    mRun(run), mVariation(variation.empty() ? "default" : variation), mTimeMicro(timeMicro), mTag(tag)
{
}


bool HTTPDataProvider::IsHttpUrl(const std::string& connectionString)
{
    return connectionString.compare(0, 7, "http://") == 0 || connectionString.compare(0, 8, "https://") == 0;
}


void HTTPDataProvider::Connect(const std::string& url)
{
    if (IsConnected()) {
        if (url == mConnectionString) return;
        throw runtime_error("CCDB HTTP: the provider is already connected to " + mConnectionString);
    }
    if (!IsHttpUrl(url)) {
        throw runtime_error("CCDB HTTP: the connection string must start with http:// or https://: " + url);
    }
    string path = FetchBundle(url);

    // A bundle never changes once it is in the cache: immutable spares SQLite its locks (network file systems)
    SQLiteDataProvider::Connect("sqlite:///file:" + Escape(path, "/") + "?immutable=1");
    mBundlePath = path;
    mConnectionString = url;
}


std::string HTTPDataProvider::FetchBundle(const std::string& url)
{
    string base = url;
    while (!base.empty() && base[base.size() - 1] == '/') base.erase(base.size() - 1);

    const char* cacheSetting = getenv("CCDB_HTTP_CACHE_DIR");
    const char* home = getenv("HOME");
    string cacheRoot;
    if (cacheSetting && *cacheSetting) cacheRoot = cacheSetting;
    else if (home && *home) cacheRoot = string(home) + "/.cache/ccdb";
    else throw runtime_error("CCDB HTTP: neither CCDB_HTTP_CACHE_DIR nor HOME is set, so there is no cache directory");
    string directory = cacheRoot + "/" + CacheName(base.substr(base.find("://") + 3));
    MakeDirectories(directory);

    string query = "run=" + to_string(mRun);
    string name = "run" + to_string(mRun) + "_";
    bool named = true;                                        // the request names one set of constants
    if (!mTag.empty()) {
        query += "&tag=" + Escape(mTag);
        name += "tag_" + CacheName(mTag);
    } else {
        query += "&variation=" + Escape(mVariation);
        name += CacheName(mVariation) + "_";
        if (mTimeMicro != 0) {
            string time = TimeText(mTimeMicro);
            query += "&time=" + Escape(time);          // %3A, as the API's own redirect writes it: one URL for caches
            name += CompactTime(time);
        } else {
            named = false;
        }
    }

    string request = base + "/bundle?" + query;
    string path = directory + "/" + name + ".sqlite";
    if (named && FileExists(path)) return path;

    if (!named) {
        // The newest: the server redirects to the explicit time, and that bundle may be in the cache already. Other
        // redirects (http to https, a moved server) come first
        for (int hop = 0; hop < 5 && QueryParameter(request, "time").empty(); hop++) {
            Response answer = Get(request, "");
            if (!answer.failure.empty()) {
                throw runtime_error("CCDB HTTP: cannot get the run bundle " + request + ": " + answer.failure +
                                    ". The newest constants need the server; a bundle by time or by tag is read from the cache when it is there");
            }
            request = answer.redirect;
        }
        string time = QueryParameter(request, "time");
        if (time.empty()) throw runtime_error("CCDB HTTP: the server did not redirect " + base + "/bundle?" + query + " to an explicit time");
        path = directory + "/" + name + CompactTime(time) + ".sqlite";
        if (FileExists(path)) return path;
    }

    string part = directory + "/." + name + ".part." + to_string(getpid()) + "." + to_string(partCounter++);
    Response answer = Get(request, part);
    if (!answer.failure.empty()) {
        remove(part.c_str());
        throw runtime_error("CCDB HTTP: cannot get the run bundle " + request + ": " + answer.failure);
    }
    if (rename(part.c_str(), path.c_str()) != 0) {           // atomic: a reader sees no file or the whole file
        string reason = strerror(errno);
        remove(part.c_str());
        throw runtime_error("CCDB HTTP: cannot move the bundle to '" + path + "': " + reason);
    }
    return path;
}
}
