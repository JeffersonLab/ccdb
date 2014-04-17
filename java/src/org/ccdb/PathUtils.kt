/**
 * Created by Dmitry on 3/24/2014.
 */

package org.jlab.ccdb.helpers

import java.util.Date
import java.text.SimpleDateFormat
import org.omg.CORBA.Request
import org.jlab.ccdb.RequestParseResult

/** @brief Extracts Directory from object path
 *
 *	in /dir/subdir/object will return /dir/subdir
 *
 * @param    const string & path
 * @return   std::string
 */
fun extractDirectory(path: String): String {
    val index = path.lastIndexOf("/")
    if (index <= 0) return ""
    return path.substring(0, index)
}

/** @brief Extract Objectname from object path
 * @example ExtractObjectname("/dir/subdir/object") will return "object"
 * @param  const string & path
 * @return std::string
 */
fun extractObjectname(path: String): String {
    val index = path.lastIndexOf("/")
    if (index < 0 || index == path.size - 1) return ""
    return path.substring(index + 1)
}


/** @brief Combines two parts of path
 *
 * will hande /path/left/ + /and/right etc.
 *
 * @param     const string & left
 * @param     const string & right
 * @return   std::string
 */
fun combinePath(left: String, right: String): String {
    if (right.length == 0) return left
    if (left.length == 0) return right
    val separator = '/'
    var result = left;
    var needAddSeparator = false;
    var leftLast = left[left.length - 1];
    var rightFirst = right[0];

    if ((leftLast == separator) && (rightFirst == separator)) {
        //it is a situation we have both "left/ + /right"
        //so erase one of them
        result = left.substring(0, left.length)

        //needAddSeparator should be false by default so we dont touch it
    } else if ((leftLast != separator) && (rightFirst != separator)) {
        //it is a situation we have "left + right"
        //needs separator
        needAddSeparator = true;
    }

    //The last case (leftLast != separator) || (rightFirst != separator)
    //gives us needAddSeparator = false, but it is false by default

    if (needAddSeparator) result += separator;
    return result + right;
}


////______________________________________________________________________________
//bool ccdb::PathUtils::WildCardCheck( const char* pattern, const char* source )
//{
//char *cp, *mp;
//while ((*source) && (*pattern != '*')) 	{
//if ((*pattern != *source) && (*pattern != '?')) {
//return 0;
//}
//
//pattern++;
//source++;
//}
//
//while (*source) {
//if (*pattern == '*') {
//if (!*++pattern) {
//return 1;
//}
//
//mp = const_cast<char *>(pattern);
//cp = const_cast<char *>(source+1);
//}
//else if ((*pattern == *source) || (*pattern == '?')) {
//pattern++;
//source++;
//}
//else {
//pattern = mp;
//source = cp++;
//}
//}
//
//while (*pattern == '*') {
//pattern++;
//}
//
//return !*pattern;
//}


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
 * @return   parsed time
 */
fun parseTime(timeStr: String): Date {
    //default result
    var year = 3000
    var mon = 11
    var hour = 23
    var day = 31
    var min = 59
    var sec = 59

    //some tmp values
    var tmpStr = ""              // tmp string to buffer chars
    var delimCount = 0;            // number of delimeters we've met
    var workStr = timeStr + " "  // we appended a work string for one more non digit symbol
    var lastIsDigit = false      // last symbol was digit

    //scan all symbols
    for (i in 0..(workStr.size - 1)) {
        val symbol = workStr[i]


        if (symbol.isDigit()) {
            // Check if it is number
            tmpStr += symbol
            lastIsDigit = true
        } else {
            if (lastIsDigit) {
                // It is a delimiter after the value;
                delimCount++
                if (delimCount == 1) //it was a year
                {
                    if (tmpStr.size != 4) //it is an error with length
                    {
                        throw IllegalArgumentException("Year should be in form YYYY but given is '$tmpStr'. Overall date should be in form 'YYYY/MM/dd hh:mm:ss'")
                    }
                    year = Integer.parseInt(tmpStr)   // since in tm the year is from 1900
                }


                if (delimCount == 2) //it was a month
                {
                    if (tmpStr.size != 2) //it is an error with length
                    {
                        throw IllegalArgumentException("Month should be in form 'MM' but given is '$tmpStr'. Overall date should be in form 'YYYY/MM/dd hh:mm:ss'")
                    }


                    mon = Integer.parseInt(tmpStr) - 1  // -1 because months since January [0-11]

                    //check for 30 day month
                    if ((mon == 9) || (mon == 10) || (mon == 4) || (mon == 6)) {
                        day = 30
                    }

                    //February...
                    if (mon == 2) {
                        if ( (year % 4 == 0 && year % 100 != 0) || year % 400 == 0) {
                            day = 29
                        } else {
                            day = 28
                        }
                    }
                }

                if (delimCount == 3) //it was a day
                {

                    if (tmpStr.size != 2) //it is an error with length
                    {
                        throw IllegalArgumentException("Day should be in form 'dd' but given is '$tmpStr'. Overall date should be in form 'YYYY/MM/dd hh:mm:ss'")
                    }
                    day = Integer.parseInt(tmpStr);  //since in tm the year is from 1900
                }

                if (delimCount == 4) //it was a hour
                {
                    if (tmpStr.size != 2) //it is an error with length
                    {
                        throw IllegalArgumentException("Hour should be in form 'hh' but given is '$tmpStr'." +
                        "Overall date should be in form 'YYYY/MM/dd hh:mm:ss'")
                    }

                    hour = Integer.parseInt(tmpStr)
                }

                if (delimCount == 5) //it is a minutes
                {
                    if (tmpStr.size != 2) //it is an error with length
                    {
                        throw IllegalArgumentException("Minutes should be in form 'mm' but given is '$tmpStr'." +
                        "Overall date should be in form 'YYYY/MM/dd hh:mm:ss'")
                    }

                    min = Integer.parseInt(tmpStr)
                }

                if (delimCount == 6) //it is seconds
                {
                    if (tmpStr.size != 2) //it is an error with length
                    {
                        throw IllegalArgumentException("Seconds should be in form 'ss' but given is '$tmpStr'." +
                        "Overall date should be in form 'YYYY/MM/dd hh:mm:ss'")
                    }

                    sec = Integer.parseInt(tmpStr)
                }
            }
            tmpStr = ""     // Clear the temp string
            lastIsDigit = false
        }
    }

    return Date(year, mon, day, hour, min, sec)
}

fun parseRequest( requestStr:String ): RequestParseResult{
///** @brief    Parses request string and returns corresponding
// * @see DParseRequestResult structure.
// *
// * This function is used to parse user requests. The user requests
// * full form of request is
// * /path/to/data:run:variation:time
// * but request might be given in any shorter form
// * /path/to/data - just path to date, no run, variation and timestamp specified
// * /path/to/data::mc - no run or date specified.
// * /path/to/data:::2029 - only path and date
// *
// * @parameter [in] requestStr - user request
// * @return structure that represent user result
// */
//
    val result = RequestParseResult(requestStr)
    var colonCount = 0
    var runStr = ""
    for (i in 0..(requestStr.size-1)) {
        val symbol = requestStr[i]
        if (symbol != ':') {
            //it is not a colon so we add this symbol somewhere
            when(colonCount) {
                0 -> {
                    //it is a path
                    result.path += symbol
                    result.wasParsedPath = true;
                }
                1 -> {
                    //it is a run range
                    runStr += symbol
                    result.wasParsedRunNumber = true;
                }
                2 -> {
                    //it is variation
                    result.variation += symbol          // Variation name
                    result.wasParsedVariation = true;   // true since we've got a variation
                }
                else -> {
                    //it should be a time than
                    result.timeString += symbol    // Original string with time
                    result.wasParsedTime = true;   // true if time stamp was not empty
                }
            }
        } else{
            //the symbol is colon (symbol==':')
            colonCount++;

            //This is patch for situation when time string has ':' inside
            if(colonCount>3) result.timeString += ':'
        }
    }

    //at this point we parsed all symbols and it is time for final parsing
    //parse run number
    if(result.wasParsedRunNumber){
        result.runNumber = Integer.parseInt(runStr)
    }

    //parse time
    if(result.wasParsedTime){
        result.time = parseTime(result.timeString)
    }

    return result
}

/** @brief Adds '/' to the beginning of the path if it is not there
 *
 * If one have 'the/path' this function will change the string as '/the/path'
 * If one gave '/the/path' this function does nothing
 * @parameter [in] string & path
 * @return   void
 */
fun makeAbsolute(path: String): String {
    if ( !isAbsolute(path) ) return '/' + path;
    return path;
}

/** @brief Check if the path is absolute - starts with /
 */
fun isAbsolute(path: String): Boolean {
    return (path.length > 0) && (path[0] == '/')
}

//
////______________________________________________________________________________
//ccdb::ContextParseResult ccdb::PathUtils::ParseContext( const string& context )
//{
///** Parses JANA context string and returns ContextParseResult structure
// *
// * JANA_CONTEXT is a string that may contain default values for CCDB.
// * example of context string:
// * 'variation=default calibtime=2012'
// * parameters and values are separated by '=' (!) WITH NO SPACES
// */
//
//ContextParseResult result;
//result.ConstantsTimeIsParsed = false;
//result.VariationIsParsed = false;
//
////check empty string
//if(context.size()<=0) return result;
//
////split context to name=value pairs
//vector<string> tokens = StringUtils::LexicalSplit(context);
//
////iterate through pairs
//for(int i=0; i<tokens.size(); i++)
//{
//string token = tokens[i];
//
////variation is found?
//if(token.find("variation=")==0)  //TODO move "variation=" to some define?
//{
//result.VariationIsParsed = true;
//result.Variation = StringUtils::Replace("variation=","",token);
//continue;
//}
//
////calibtime is found?
//if(token.find("calibtime=")==0)
//{
//result.ConstantsTimeIsParsed = true;
//bool parseResult = false;
//result.ConstantsTime = PathUtils::ParseTime(StringUtils::Replace("calibtime=","",token), &parseResult);
//if(!parseResult) result.ConstantsTime = 0;
//}
//}
//
//return result;
//}
//







