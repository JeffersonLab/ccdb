#include "CCDB/Helpers/TimeUtils.h"

#include <cstdio>
#include <vector>

#ifdef _MSC_VER
// MSVC has localtime_s instead, with the arguments swapped and an error code returned
static inline struct tm* localtime_r(const time_t* timep, struct tm* result)
{
    return localtime_s(result, timep) == 0 ? result : nullptr;
}
#endif

using namespace std;

namespace
{
    bool IsLeapYear(int year)
    {
        return (year % 4 == 0 && year % 100 != 0) || year % 400 == 0;
    }

    int DaysInMonth(int year, int month)
    {
        static const int days[] = {31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31};
        return (month == 2 && IsLeapYear(year)) ? 29 : days[month - 1];
    }

    /// Days since 1970-01-01 of a proleptic Gregorian date (Howard Hinnant's days_from_civil)
    int64_t DaysFromCivil(int64_t year, int month, int day)
    {
        year -= month <= 2 ? 1 : 0;
        const int64_t era = (year >= 0 ? year : year - 399) / 400;
        const int64_t yearOfEra = year - era * 400;
        const int64_t dayOfYear = (153 * (month + (month > 2 ? -3 : 9)) + 2) / 5 + day - 1;
        const int64_t dayOfEra = yearOfEra * 365 + yearOfEra / 4 - yearOfEra / 100 + dayOfYear;
        return era * 146097 + dayOfEra - 719468;
    }

    /// The local wall time of a UTC second, as CivilToSeconds of its fields
    int64_t LocalWall(time_t utc)
    {
        struct tm local;
        localtime_r(&utc, &local);
        return ccdb::TimeUtils::CivilToSeconds(local.tm_year + 1900, local.tm_mon + 1, local.tm_mday,
                                               local.tm_hour, local.tm_min, local.tm_sec);
    }
}


int64_t ccdb::TimeUtils::EndOfSecond(time_t seconds)
{
    if (seconds == 0) return 0;
    return static_cast<int64_t>(seconds) * MicrosecondsPerSecond + (MicrosecondsPerSecond - 1);
}


time_t ccdb::TimeUtils::ToSeconds(int64_t micro)
{
    int64_t seconds = micro / MicrosecondsPerSecond;
    if (micro % MicrosecondsPerSecond < 0) seconds--;
    return static_cast<time_t>(seconds);
}


int64_t ccdb::TimeUtils::CivilToSeconds(int year, int month, int day, int hour, int minute, int second)
{
    return DaysFromCivil(year, month, day) * 86400 + hour * 3600 + minute * 60 + second;
}


time_t ccdb::TimeUtils::LocalWallToUtc(int64_t wallSeconds)
{
    // CPython's datetime local() inversion for a naive time with fold=0 (Lib/datetime.py, _mktime)
    const int64_t maxFoldSeconds = 24 * 3600;
    const int64_t t = wallSeconds;
    const int64_t a = LocalWall(static_cast<time_t>(t)) - t;
    const int64_t u1 = t - a;
    const int64_t t1 = LocalWall(static_cast<time_t>(u1));
    int64_t b;
    if (t1 == t) {
        // u1 is a solution, but there may be another one (a repeated hour): look one day back (fold=0)
        const int64_t u2 = u1 - maxFoldSeconds;
        b = LocalWall(static_cast<time_t>(u2)) - u2;
        if (a == b) return static_cast<time_t>(u1);
    }
    else {
        b = t1 - u1;
    }
    const int64_t u2 = t - b;
    const int64_t t2 = LocalWall(static_cast<time_t>(u2));
    if (t2 == t) return static_cast<time_t>(u2);
    if (t1 == t) return static_cast<time_t>(u1);
    // Neither offset gives the wall time back: it lies in a skipped hour; fold=0 takes the later instant
    return static_cast<time_t>(u1 > u2 ? u1 : u2);
}


string ccdb::TimeUtils::FormatUtc(int64_t micro)
{
    const time_t seconds = ToSeconds(micro);
    const int fraction = static_cast<int>(micro - static_cast<int64_t>(seconds) * MicrosecondsPerSecond);
    struct tm utc;
    gmtime_r(&seconds, &utc);
    char buffer[40];
    snprintf(buffer, sizeof(buffer), "%04d-%02d-%02d %02d:%02d:%02d.%06d", utc.tm_year + 1900, utc.tm_mon + 1,
             utc.tm_mday, utc.tm_hour, utc.tm_min, utc.tm_sec, fraction);
    return string(buffer);
}


bool ccdb::TimeUtils::ParseUtc(const string& text, int64_t& micro)
{
    int year, month, day, hour, minute, second;
    char fractionText[16] = "";
    const int read = sscanf(text.c_str(), "%4d-%2d-%2d %2d:%2d:%2d.%15[0-9]", &year, &month, &day, &hour, &minute,
                            &second, fractionText);
    if (read < 6) return false;
    string fraction(fractionText);
    if (fraction.size() > 6) return false;
    fraction.append(6 - fraction.size(), '0');
    micro = CivilToSeconds(year, month, day, hour, minute, second) * MicrosecondsPerSecond + atoi(fraction.c_str());
    return true;
}


int64_t ccdb::TimeUtils::ParseLocalTime(const string& text, bool* success)
{
    if (success) *success = false;

    // Split into digit groups; between two groups exactly one non-digit character
    vector<string> groups;
    string current;
    size_t separatorLength = 0;
    for (size_t i = 0; i < text.size(); i++) {
        const char symbol = text[i];
        if (symbol >= '0' && symbol <= '9') {
            if (!groups.empty() && current.empty() && separatorLength != 1) return 0;
            current.push_back(symbol);
            separatorLength = 0;
        }
        else {
            if (current.empty() && groups.empty()) return 0;    // the text starts with a non-digit
            if (!current.empty()) {
                groups.push_back(current);
                current.clear();
            }
            separatorLength++;
        }
    }
    if (current.empty()) return 0;                              // empty, or ends with a separator
    groups.push_back(current);
    if (groups.size() > 7) return 0;

    static const size_t lengths[] = {4, 2, 2, 2, 2, 2};
    for (size_t i = 0; i < groups.size() && i < 6; i++) {
        if (groups[i].size() != lengths[i]) return 0;
    }
    if (groups.size() == 7 && groups[6].size() > 6) return 0;

    const int year = atoi(groups[0].c_str());
    const int month = groups.size() > 1 ? atoi(groups[1].c_str()) : 12;
    if (month < 1 || month > 12) return 0;
    const int day = groups.size() > 2 ? atoi(groups[2].c_str()) : DaysInMonth(year, month);
    const int hour = groups.size() > 3 ? atoi(groups[3].c_str()) : 23;
    const int minute = groups.size() > 4 ? atoi(groups[4].c_str()) : 59;
    const int second = groups.size() > 5 ? atoi(groups[5].c_str()) : 59;
    if (day < 1 || day > DaysInMonth(year, month) || hour > 23 || minute > 59 || second > 59) return 0;

    // The fraction is the latest microsecond it covers: "5" is .599999
    string fraction = groups.size() == 7 ? groups[6] : string();
    fraction.append(6 - fraction.size(), '9');

    const time_t utc = LocalWallToUtc(CivilToSeconds(year, month, day, hour, minute, second));
    if (success) *success = true;
    return static_cast<int64_t>(utc) * MicrosecondsPerSecond + atoi(fraction.c_str());
}
