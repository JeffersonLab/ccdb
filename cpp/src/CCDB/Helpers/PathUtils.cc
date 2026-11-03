#include <cstdlib>

#include <stdexcept>
#include "CCDB/Helpers/PathUtils.h"
#include "CCDB/Helpers/TimeUtils.h"

using namespace std;
using namespace ccdb;

//______________________________________________________________________________
string ccdb::PathUtils::ExtractDirectory( const string& path )
{
	return path.substr( 0, path.find_last_of( '/' )  ); //will get directory without final /
}


//______________________________________________________________________________
string ccdb::PathUtils::ExtractObjectname( const string& path )
{
	return path.substr( path.find_last_of( '/' ) +1 );
}


//______________________________________________________________________________
string ccdb::PathUtils::CombinePath( const string& left, const string& right )
{
	if(right.length()==0) return left;
	if(left.length()==0)  return right;
	char separator = '/';
	string result = left;
	bool needAddSeparator = false;
	char leftLast = left[left.length()-1];
	char rightFirst = right[0];

	if((leftLast == separator) && (rightFirst == separator))
	{
		//it is a situation we have both "left/ + /right" 
		//so erase one of them
		result.erase(result.length());

		//needAddSeparator should be false by default so we dont touch it
	}
	else if((leftLast != separator) && (rightFirst != separator))
	{
		//it is a situation we have "left + right"
		//needs separator
		needAddSeparator = true;
	}

	//The last case (leftLast != separator) || (rightFirst != separator)
	//gives us needAddSeparator = false, but it is false by default


	if(needAddSeparator) result += separator; 
	return result+right;
}


//______________________________________________________________________________
bool ccdb::PathUtils::WildCardCheck( const char* pattern, const char* source )
{	
	char *cp, *mp;
	while ((*source) && (*pattern != '*')) 	{
		if ((*pattern != *source) && (*pattern != '?')) {
				return 0;
		}

		pattern++;
		source++;
	}

	while (*source) {
		if (*pattern == '*') {
			if (!*++pattern) {
					return 1;
			}

			mp = const_cast<char *>(pattern);
			cp = const_cast<char *>(source+1);
		} 
		else if ((*pattern == *source) || (*pattern == '?')) {
			pattern++;
			source++;
		} 
		else {
			pattern = mp;
			source = cp++;
		}
	}

	while (*pattern == '*') {
		pattern++;
	}

	return !*pattern;
}


//______________________________________________________________________________
time_t ccdb::PathUtils::ParseTime( const string &timeStr, bool * succsess )
{
    // The whole second of the instant TimeUtils::ParseLocalTime reads (docs/concepts/time.md)
    bool parsed = false;
    int64_t micro = TimeUtils::ParseLocalTime(timeStr, &parsed);
    if(succsess!=NULL) *succsess = parsed;
    return parsed ? TimeUtils::ToSeconds(micro) : 0;
}


//______________________________________________________________________________
ccdb::RequestParseResult ccdb::PathUtils::ParseRequest( const string& requestStr )
{
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

    //Set default parameters
    RequestParseResult result;
    result.RunNumber=0;	              // Run number
    result.WasParsedRunNumber=false;  // true if Run number was non empty
    result.IsInvalidRunNumber=false;  // true if was an error parsing runnumber
    result.Path = "";                 // Object path
    result.WasParsedPath=false;       // true if Path was nonempty
    result.Variation="";              // Variation name
    result.WasParsedVariation=false;  // true if variation was not empty
    result.Time=0;                    // Time stamp
    result.TimeMicro=0;               // Time stamp in microseconds
    result.WasParsedTime=false;       // true if time stamp was not empty
    result.TimeString="";             // Original string with time
    result.Tag="";                    // Tag name
    result.WasParsedTag=false;        // true if the request names a tag

    // A tag is the part after '@': /path/to/data@tag or /path/to/data:run@tag
    // Neither paths, nor runs, nor variations, nor times contain '@', so the first one starts the tag
    string request = requestStr;
    size_t tagPos = requestStr.find('@');
    if(tagPos != string::npos)
    {
        result.Tag = requestStr.substr(tagPos + 1);
        result.WasParsedTag = true;
        request = requestStr.substr(0, tagPos);

        if(!IsValidTagName(result.Tag))
        {
            throw std::invalid_argument("Request '" + requestStr + "': tag name '" + result.Tag +
                                        "' is invalid. It should consist of A-Z, a-z, 0-9, _");
        }
    }

    int colonCount=0;
    string runStr ="";
    for (size_t i=0; i<request.size(); i++)
    {
        char symbol = request[i];
        if(symbol!=':')
        {
            //it is not a colon so we add this symbol somewhere
            switch(colonCount)
            {
            case 0:  //it is a path
                result.Path.push_back(symbol);
                result.WasParsedPath=true;
                break;
            case 1:  //it is a run range
                runStr.push_back(symbol);
                result.WasParsedRunNumber = true;
                break;
            case 2:  //it is variation
                result.Variation.push_back(symbol);     // Variation name
                result.WasParsedVariation=true;         // true since we've got a variation
                break;
            default:  //it should be a time than
                result.WasParsedTime=true;              // true if time stampt was not empty
                result.TimeString.push_back(symbol);    // Original string with time
                break;
            }
        }
        else //the symbol is colon (symbol==':')
        {
            colonCount++;

			//This addition is for situation when ':' is found in time string 
			if (colonCount > 3) result.TimeString.push_back(':');
        }
    }

    // at this point we parsed all symbols and it is time for final parsing

    //parse run number
    if(result.WasParsedRunNumber)
    {
        bool success = true;
        result.RunNumber = StringUtils::ParseInt(runStr, &success);

        result.IsInvalidRunNumber = !success || result.RunNumber<0;
    }

    // A tag replaces variation and time. Empty parts (/path:run:@tag) are fine, as in Python
    if(result.WasParsedTag && (result.WasParsedVariation || result.WasParsedTime))
    {
        throw std::invalid_argument("Request '" + requestStr + "': a tag (@NAME) may not be combined with a variation or a time");
    }

    //parse time: an invalid time is an error, as in Python, not "the newest constants"
    if(result.WasParsedTime)
    {
        bool success=false;
        result.TimeMicro = TimeUtils::ParseLocalTime(result.TimeString, &success);
        if(!success)
        {
            throw std::invalid_argument("Request '" + requestStr + "': can't read the time '" + result.TimeString +
                                        "' (YYYY-MM-DD hh:mm:ss.ffffff or a leading part of it)");
        }
        result.Time = TimeUtils::ToSeconds(result.TimeMicro);
    }

    return result;
}


//______________________________________________________________________________
bool ccdb::PathUtils::IsValidTagName( const string& name )
{
    if(name.empty()) return false;
    for(char letter: name)
    {
        bool isValid = (letter >= 'a' && letter <= 'z') ||
                       (letter >= 'A' && letter <= 'Z') ||
                       (letter >= '0' && letter <= '9') ||
                       letter == '_';
        if(!isValid) return false;
    }
    return true;
}


//______________________________________________________________________________
string & ccdb::PathUtils::MakeAbsolute( string &path )
{
     /** @brief Adds '/' to the beginning of the path if it is not there
     *
     * If one have 'the/path' this function will change the string as '/the/path'
     * If one gave '/the/path' this function does nothing
     * @parameter [in] string & path
     * @return   void
     */

    if(!IsAbsolute(path)) path.insert(0,1,'/');
    return path;
}
//______________________________________________________________________________
bool ccdb::PathUtils::IsAbsolute( const string &path )
{
    /** @brief Check if the path is absolute - starts with /
     */
    return (path.length()>0 && path[0]=='/');
}

//______________________________________________________________________________
ccdb::ContextParseResult ccdb::PathUtils::ParseContext( const string& context )
{
	/** Parses JANA context string and returns ContextParseResult structure
	 * 
	 * JANA_CONTEXT is a string that may contain default values for CCDB. 
	 * example of context string:
	 * 'variation=default calibtime=2012'
	 * parameters and values are separated by '=' (!) WITH NO SPACES
	 */

	ContextParseResult result;	
	result.ConstantsTimeIsParsed = false;
	result.ConstantsTime = 0;
	result.ConstantsTimeMicro = 0;
	result.VariationIsParsed = false;
    result.RunNumberIsParsed = false;
	
	//check empty string
	if(context.size()<=0) return result;

	//split context to name=value pairs
	vector<string> tokens = StringUtils::LexicalSplit(context);

	//iterate through pairs
	for(int i=0; i<tokens.size(); i++)
	{
		string token = tokens[i];

		//variation is found?
		if(token.find("variation=")==0)  //TODO move "variation=" to some define?
		{
			result.VariationIsParsed = true;
			result.Variation = StringUtils::Replace("variation=","",token);

			// A tag is named only in a request (/path@NAME). Variation names have no '@', so a context
			// with one is someone trying to set a default tag: say so now, not as an unknown variation later
			if(result.Variation.find('@') != string::npos)
			{
				throw std::invalid_argument("Context '" + context + "': variation '" + result.Variation +
				                            "' is invalid. A tag (@NAME) can't be a default variation, put it in the request: /path/to/data@NAME");
			}
			continue;
		}

		//calibtime is found?
		if(token.find("calibtime=")==0)
		{
			result.ConstantsTimeIsParsed = true;
			bool parseResult = false;
			string timeText = StringUtils::Replace("calibtime=","",token);
			result.ConstantsTimeMicro = TimeUtils::ParseLocalTime(timeText, &parseResult);
			if(!parseResult)
			{
				throw std::invalid_argument("Context '" + context + "': can't read calibtime '" + timeText +
				                            "' (YYYY-MM-DD-hh-mm-ss.ffffff or a leading part of it)");
			}
			result.ConstantsTime = TimeUtils::ToSeconds(result.ConstantsTimeMicro);
		}

        //calibtime is found?
        if(token.find("run=")==0)
        {
            result.RunNumberIsParsed = true;
            result.RunNumber = StringUtils::ParseInt(StringUtils::Replace("run=","",token));
        }
	}

	return result;
}







