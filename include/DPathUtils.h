#ifndef _DPathUtils_
#define _DPathUtils_

#ifdef WIN32
#define _CRT_SECURE_NO_WARNINGS
#include <Windows.h>
#endif

//#include <stdargs.h>
//#include <varargs.h>
#include <stdio.h>
#include <stdarg.h>
#include <string>
#include <sstream>
#include <vector>
#include <exception>

#include <iosfwd>
#include <iostream>
#include <ostream>
#include <time.h>
#include "DStringUtils.h"

using namespace std;

namespace ccdb
{
    /// @brief DRequestParseResult is structure that represents parse result of
    /// a string request. @see DPathUtils::ParseRequest
struct DParseRequestResult
{
	int    RunNumber;	       /// Run number
	bool   WasParsedRunNumber; /// true if Run number was non empty
	bool   IsInvalidRunNumber; /// true if was an error parsing runnumber
	string Path;               /// Object path
	bool   WasParsedPath;      /// true if Path was nonempty
	string Variation;          /// Variation name
	bool   WasParsedVariation; /// true if variation was not empty
	time_t Time;               /// Time stampt
	bool   WasParsedTime;      /// true if time stampt was not empty
	string TimeString;         /// Original string with time
};


/*@class DPathUtils provides static methods of CCDB objects namepath manipulation
 */
class DPathUtils
{
public:

	/** @brief Extracts Directory from object path
	 *
	 *	in /dir/subdir/object will return /dir/subdir
	 *
	 * @param    const string & path
	 * @return   std::string
	 */
	static string	ExtractDirectory( const string& path );

	/** @brief Extract Objectname from object path
	 * @example ExtractObjectname("/dir/subdir/object") will return "object"
	 * @param  const string & path
	 * @return std::string
	 */
	static string	ExtractObjectname( const string& path );

	/** @brief Combines two parts of path
	 *
	 * will hande /path/left/ + /and/right etc.
	 *
	 * @param     const string & left
	 * @param     const string & right
	 * @return   std::string
	 */
	static string	CombinePath( const string& left, const string& right );

	/** @brief search pattern in source using * and ?
	 *
	 * @param pattern
	 * @param source
	 * @return   bool Returns:true on match, false on no matches.
	 */
	static bool WildCardCheck(const char* pattern, const char* source);

	/** @brief    Parses request string and returns corresponding 
     * @see DParseRequestResult structure. 
     * 
     * This function is used to parse user requests. The user requests 
     * full form of request is 
	 * /path/to/data:run:variation:time
     * but request might be given in any shorter form
     * /path/to/data - just path to date, no run, variation and timestamp specified
     * /path/to/data::mc - no run or date specified.
     * /path/to/data:::2029 - only path and date
     *
	 * @parameter [in] requestStr - user request
	 * @return structure that represent user result
	 */
	static DParseRequestResult ParseRequest(const string& requestStr);

    /** @brief ParseTime
     * parses time as any part of
     * YYYY:MM:DD-hh:mm:ss
     *
     * 1) in place of ':' and '-' might be any ONE non digit character
     *
     * 2) One could place only part of the string,
     *    the latest date for this part will be returned.
     *    I.e. if timeString is "2011" - (it means the year 2011 and nothing more),
     *    this function returns result as if it were 2011:12:31-23:59:59
     *    thus using such timestamp would get the latest constants for year 2011
     *
     * @parameter [in] const string & timeString string to parse
     * @parameter [out] succsess true if success
     * @return   time_t
     */
    static time_t ParseTime(const string &timeStr, bool * succsess);
};
}
#endif // _DPathUtils_