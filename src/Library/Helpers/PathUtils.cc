#include <cstdlib>

#include "CCDB/Helpers/PathUtils.h"

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
    
    
    //default result
    tm time;
    time.tm_hour = 23;
    time.tm_mday = 31;
    time.tm_min = 59;
    time.tm_mon = 11;
    time.tm_sec = 59;
    time.tm_isdst=-1;   //auto determine. It is not always work automatically. 
                        //See http://stackoverflow.com/questions/8558919/mktime-and-tm-isdst
    
    if(succsess!=NULL) *succsess = true;

    //some tmp values
    string tmpStr =""; //tmp string to buffer chars
    int delimCount=0;  //number of delimeters we've met

    string workStr(timeStr); //we appended a work string for one more non digit symbol
    workStr.push_back(' ');  //so the logic behind would work in any case

    bool lastIsDigit;   //last symbol was digit

    //scan all symbols
    for (size_t i=0; i<workStr.size(); i++)
    {
        char symbol = workStr[i];

        if(symbol>='0'&&symbol<='9') //Check if it is number
        {
            tmpStr.push_back(symbol);
            lastIsDigit = true;
        }
        else if(lastIsDigit) //it is a delimeter after the value;
        {
            delimCount++;
            if(delimCount ==1) //it was a year
            {
                if(tmpStr.length()!=4) //it is an error with lengtn of year
                {
                    if(succsess!=NULL) *succsess = false;
                    return 0;
                }
                time.tm_year = StringUtils::ParseInt(tmpStr) - 1900;  //since in tm the year is from 1900
            }
            
            if(delimCount ==2) //it was a month
            {
                if(tmpStr.length()!=2) //it is an error with lengtn of year
                {
                    if(succsess!=NULL) *succsess = false;
                    return 0;
                }

                time.tm_mon = StringUtils::ParseInt(tmpStr) - 1;  // -1 becaouse months since January [0-11]

                //#check for 30 day month
                if((time.tm_mon == 9)||(time.tm_mon == 10)||(time.tm_mon == 4)||(time.tm_mon == 6))
                {
                     time.tm_mday = 30;
                }

                //February...
                if(time.tm_mon == 2)
                {
                    if( (time.tm_year % 4 == 0 &&  time.tm_year % 100 != 0) || time.tm_year % 400 == 0)
                    {
                        time.tm_mday = 29;
                    }
                    else
                    {
                        time.tm_mday = 28;
                    }
                }
            }

            if(delimCount ==3) //it was a day
            {
                if(tmpStr.length()!=2) //it is an error with lengtn of day
                {
                    if(succsess!=NULL) *succsess = false;
                    return 0;
                }
                time.tm_mday = StringUtils::ParseInt(tmpStr);  //since in tm the year is from 1900
            }

            if(delimCount ==4) //it was a hour
            {
                if(tmpStr.length()!=2) //it is an error with lengtn
                {
                    if(succsess!=NULL) *succsess = false;
                    return 0;
                }
                time.tm_hour = StringUtils::ParseInt(tmpStr);  //since in tm the year is from 1900
            }
            
            if(delimCount ==5) //it was a min
            {
                if(tmpStr.length()!=2) //it is an error with lengtn of min
                {
                    if(succsess!=NULL) *succsess = false;
                    return 0;
                }
                time.tm_min = StringUtils::ParseInt(tmpStr);  //since in tm the year is from 1900
            }
            
            if(delimCount ==6) //it was a sec
            {
                if(tmpStr.length()!=2) //it is an error with lengtn of sec
                {
                    if(succsess!=NULL) *succsess = false;
                    return 0;
                }
                time.tm_sec = StringUtils::ParseInt(tmpStr);  //since in tm the year is from 1900
            }

			
            //clear temp string for the next digit seria
            tmpStr.clear();
        }
        else
        {
            tmpStr.clear(); //in this case we clear temp string too
        }
    }
    time_t result = mktime(&time);
	if( result == -1 && succsess!=NULL) *succsess = false;
    return result;
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
    result.WasParsedTime=false;       // true if time stamp was not empty
    result.TimeString="";             // Original string with time

    int colonCount=0;
    string runStr ="";
    for (size_t i=0; i<requestStr.size(); i++)
    {
        char symbol = requestStr[i];
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

    //parse time
    if(result.WasParsedTime)
    {
        bool success=true;
        result.Time = ParseTime(result.TimeString, &success);
    }
    return result;
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
			continue;
		}

		//calibtime is found?
		if(token.find("calibtime=")==0)
		{
			result.ConstantsTimeIsParsed = true;
			bool parseResult = false;
			result.ConstantsTime = PathUtils::ParseTime(StringUtils::Replace("calibtime=","",token), &parseResult);
			if(!parseResult) result.ConstantsTime = 0;
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







