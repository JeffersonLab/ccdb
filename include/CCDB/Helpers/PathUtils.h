#ifndef _PathUtils_
#define _PathUtils_

#ifdef WIN32
#define _CRT_SECURE_NO_WARNINGS
#include <Windows.h>
#endif

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

#include "CCDB/Helpers/StringUtils.h"


/** CCDB prior 1.05.00 didnt parse "run=X" in the context string.
 * ContextParseResult didn't have RunNumber... fields.
 * This define introduced to avoid API change error. So one can do:
 * #ifdef CCDB_PARSES_CONTEXT_RUN
 * parseResult.RunIsParsed...
 * #endif
 */
#define CCDB_PARSES_CONTEXT_RUN 1

using namespace std;

namespace ccdb
{
    /// @brief RequestParseResult is structure that represents parse result of
    /// a string request. @see PathUtils::ParseRequest
struct RequestParseResult
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

/** @brief represents parse result of JANA context
 * 
 * context is given like 'variation=default time=2012 run=303'
 */
struct ContextParseResult
{
	std::string Variation;				/// Variation name
	bool		VariationIsParsed;      /// true if variation was not empty
	time_t      ConstantsTime;
	bool        ConstantsTimeIsParsed;

    int         RunNumber;              /// The run number that is HAS to be used for CCDB
    bool        RunNumberIsParsed;      /// The run number is parsed

	/*ContextParseResult()
	{
	VariationIsParsed = false;
	ConstantsTimeIsParsed = false;
	}
	~ContextParseResult();*/
};


/*@class PathUtils provides static methods of CCDB objects namepath manipulation
 */
class PathUtils
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
	static RequestParseResult ParseRequest(const string& requestStr);

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

    /** @brief Adds '/' to the beginning of the path if it is not there
     *
     * If one have 'the/path' this function will change the string as '/the/path'
     * If one gave '/the/path' this function does nothing
     * @parameter [in, out] string & path
     * @return   void
     */
    static string & MakeAbsolute(string &path);

    /** @brief Check if the path is absolute - starts with /
     */
    static bool IsAbsolute(const string &path);

	/** Parses JANA context string and returns ContextParseResult structure
	 * 
	 * JANA_CONTEXT is a string that may contain default values for CCDB. 
	 * example of context string:
	 * 'variation=default calibtime=2012'
	 * parameters and values are separated by '=' (!) WITH NO SPACES
	 */
	static ContextParseResult ParseContext(const string& context);
};
}
#endif // _PathUtils_
