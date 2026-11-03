#ifndef _TimeUtils_
#define _TimeUtils_

#include <stdint.h>
#include <string>
#include <time.h>

namespace ccdb
{
/** @brief Times of the schema 6 time model (docs/concepts/time.md): every stored time is a UTC instant,
 * the times that resolve constants carry microseconds, and a time a person types is local wall time.
 *
 * An instant is int64_t microseconds since 1970-01-01 00:00:00 UTC. The functions here are the C++ side of
 * the rules that Python implements in ccdb.path_utils; both run the cases of testdata/time/parse_cases.tsv.
 */
class TimeUtils
{
public:
    static const int64_t MicrosecondsPerSecond = 1000000;

    /** @brief The latest microsecond of a whole second: T.999999. 0 stays 0, "no time limit" (R6) */
    static int64_t EndOfSecond(time_t seconds);

    /** @brief The whole second that holds an instant (floor, also before 1970) */
    static time_t ToSeconds(int64_t micro);

    /** @brief Seconds since 1970-01-01 of a proleptic Gregorian date and time read as UTC, no normalization */
    static int64_t CivilToSeconds(int year, int month, int day, int hour, int minute, int second);

    /** @brief The UTC second of a local wall time, given as CivilToSeconds of its fields
     *
     * A wall time that occurs twice (the hour after daylight saving ends) or never (the hour skipped when it
     * starts) is read with the UTC offset in effect before the transition, as Python reads a naive datetime
     * with fold=0 (PEP 495): the repeated hour means its first occurrence, a skipped time moves forward by the
     * gap. The algorithm is CPython's datetime local-to-UTC conversion, on localtime_r, so both languages agree.
     */
    static time_t LocalWallToUtc(int64_t wallSeconds);

    /** @brief 'YYYY-MM-DD HH:MM:SS.ffffff' (26 characters) of an instant in UTC: the SQLite storage form */
    static std::string FormatUtc(int64_t micro);

    /** @brief Reads 'YYYY-MM-DD HH:MM:SS[.f…]' as a UTC instant (stored times); false on another shape */
    static bool ParseUtc(const std::string& text, int64_t& micro);

    /** @brief Parses a time a person types into a UTC instant (rules R3 and R4 of the time model)
     *
     * Groups of digits separated by exactly one non-digit character: YYYY, MM, DD, hh, mm, ss and a fraction of
     * 1 to 6 digits. A partial time is the latest moment it covers: "2011" is 2011-12-31 23:59:59.999999,
     * "12:00:00" is 12:00:00.999999, "12:00:00.5" is 12:00:00.599999. Months have their real lengths. The fields
     * are local wall time, converted by LocalWallToUtc.
     *
     * @param [out] success false when the text does not follow the grammar or names an impossible date
     * @return microseconds since the epoch, 0 on failure
     */
    static int64_t ParseLocalTime(const std::string& text, bool* success);
};
}

#endif // _TimeUtils_
