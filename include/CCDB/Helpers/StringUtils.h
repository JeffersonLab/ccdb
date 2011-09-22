#ifndef _StringUtils_
#define _StringUtils_

#ifdef WIN32
#define _CRT_SECURE_NO_WARNINGS
#include <Windows.h>
#endif

//#include <stdargs.h>
//#include <varargs.h>
#include <stdio.h>

#include <stdarg.h>
#include <string>
#include <string.h>
#include <sstream>
#include <vector>
#include <exception>

#include <iosfwd>
#include <iostream>
#include <ostream>
#include <time.h>


#include <CCDB/Helpers/Varargs.h>

#define CCDB_BLANK_CHARACTERS " \n\t\v\r\f"
//checks if character is blank.
//returns true if char is one of CCDB_BLANK_CHARACTERS
#define CCDB_CHECK_CHAR_IS_BLANK(character) ((character)==' ' || (character)=='\n' || (character)=='\t' || (character)=='\v' || (character)=='\r' || (character)=='\f')
using namespace std;



namespace ccdb
{

#define array_length(array) (sizeof (array) / sizeof (array)[0])


struct DAssignmentRequest
{
	std::string Path;
	        int RunNumber;
	std::string Variation;
	     time_t Time;
};


class StringUtils
{
public:

    /**
	 * @brief printf like string formatter
	 * 
	 * printf like string formatter, based on @see vsprintf
	 * The reason to implement this function is that 
	 * except of sprintf and snprintf the string length 
	 * is determined automathically
	 * @param fmt
	 * @return 
	 */
    static std::string Format(const char *va_(fmt), ...);
	
	
	//static string	Format(const char *fmt, ...);			
	
	/**
	 * @brief vprintf like string formatter
	 * 
	 * vprintf like string formatter, based on @see vsprintf
	 * The reason to implement this function is that 
	 * except of sprintf and snprintf the string length 
	 * is determined automathically
	 * @param fmt
	 * @param ap
	 * @return 
	 */
	static string	vFormat(const char *fmt, va_list ap);	

	/** @brief Encodes string to add to DB
	 * Encode
	 *
	 * @param     const string & source
	 * @return   std::string
	 */
	static string	Encode(const string& source);

	/** @brief Decode string from encoded string
	 *
	 * @param     const string & source
	 * @return   std::string
	 */
	static string	Decode(const string& source);
	
	/** @brief string Replace
	 *
	 * @param     const string & pattern
	 * @param     const string & replace
	 * @param     const string & source
	 * @param     string & out
	 * @return   int
	 */
	static int		Replace(const string& pattern, const string& replace, const string& source, string &out);

	/** @brief String Replace
	 *
	 * @param     const string & pattern
	 * @param     const string & replace
	 * @param     const string & source
	 * @return   std::string
	 */
	static string	Replace(const string& pattern, const string& replace, const string& source);

	/** @brief Extracts Directory from object path
	 *
	 *	in /dir/subdir/object will return /dir/subdir
	 *
	 * @param     const string & path
	 * @return   std::string
	 */
	static string	ExtractDirectory( const string& path );

	/** @brief Extract Objectname from object path
	 *
	 * @param     const string & path
	 * @return   std::string
	 */
	static string	ExtractObjectname( const string& path );

	/** @brief Combines two parts of path
	 *
	 * will hande /path/sub/ + /path/right etc.
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
	 * @return   bool Returns:true on match, false on no match.
	 */
	static bool WildCardCheck(const char* pattern, const char* source);

	
	/** @brief
	 * Split
	 *
	 * @param     const string & str
	 * @param     vector<string> & tokens
	 * @param     const string & delimiters
	 * @return   std::vector<std::string> &
	 */
	static vector<string> &Split(const string& str, vector<string>& tokens, const string& delimiters = " ");


	/** @brief
	 * Split
	 *
	 * @param     const std::string & s
	 * @param     char delim
	 * @return   std::vector<std::string>
	 */
	static std::vector<std::string> Split(const std::string &s, const string& delimiters = " ");

    
	
	/**
	 * @brief trims string from the both sides
	 * 
	 * @warning the method changes the string
	 * removes blank characters:
	 * " ", "\n", "\t", "\v", "\r", "\f"
	 * from the beginning and the end of the string
	 * 
	 * @param [in,out] s - string that will be trimmed
	 */
	static  void Trim( string& s )
	{	
		// Remove leading and trailing whitespace
		static const char whitespace[] = CCDB_BLANK_CHARACTERS;
		s.erase( 0, s.find_first_not_of(whitespace) );
		s.erase( s.find_last_not_of(whitespace) + 1U );
	}
	
    static std::vector<string> SplitStringToData(const std::string& source)
    {
        std::vector<string> tokens;
        SplitStringToData(tokens, source);
        return tokens;
    }
	
	static void SplitStringToData(std::vector<string>& tokens, const std::string& source)
	{
		//clear output
		tokens.clear();
		bool stringIsStarted = false; //Indicates that we meet '"' and looking for second one
		bool isSlash = false; //indicates if \ sign is happen to shield the quote or anothe slash
		std::string readValue="";
		//iterate through string
		for(size_t i=0; i<source.length(); i++)
		{
			if(CCDB_CHECK_CHAR_IS_BLANK(source[i]) && !stringIsStarted)
			{
				//we have a space! Is it a space that happens after value?
				if(readValue.length()>0)
				{
					tokens.push_back(readValue);
					readValue="";
				}
			}
			else
			{
				//it is not a blank character!
				if(source[i]=='\\' && stringIsStarted && i<(source.length()-1) && source[i+1]=='"')
				{
					//ok! we found a \" inside a string! Not a problem! At all!					
					
					i++; //skip this \ symbol
					readValue+=source[i]; //it is just one more symbol in value
				}
				else if(source[i]=='#' && !stringIsStarted) //lets check if it is a comment symbol that is not incide a string...
				{
					//it is a comment started...
					//lets save what we collected for now if we collected
					if(readValue.length()>0)
					{
						tokens.push_back(readValue);
						readValue="";
					}
					
					//and put there the rest of the lint(all comment) if there is something to put
					if(i<(source.length()-1))
					{
						tokens.push_back(source.substr(i));
						
						//after that gentelment should exit
						return;
					}
				}
				else if(source[i]=='"')
				{
					
					//it is a beginnig or ending  of a string 
					//just set appropriate flag and continue
					stringIsStarted = !stringIsStarted;
				}
				else
				{
					//it is just one more symbol in file
					readValue+=source[i];
				}
			}
			
			//last we have is to check that 
			//it is not the end of the lint			
			if(i==(source.length()-1) && readValue.length()>0)
			{
				tokens.push_back(readValue);
				readValue="";
			}
		}
	}

	/** @brief Prints object to string
	 *
	 * @param     obj Object to be converted to string. Should have << stream 
	 * @return   String with value, if object doesn't have reloaded operator <<, return string::empty()
	 */
	template<class T>
	static std::string ToString(const T& obj)
	{
		std::stringstream sstream (stringstream::out);
		string result(string::empty());

		try
		{
			sstream << obj;
			result = sstream.str();
		}
		catch (std::exception ex) {	/*eat it*/}
		return result;
	}
	
	static int				ParseInt(const string& source, bool *result=NULL );		    ///Reads int	from the last query row
	static unsigned int		ParseUInt(const string& source, bool *result=NULL );        ///Reads unsigned int from the last query row
	static long				ParseLong(const string& source, bool *result=NULL );        ///Reads long from the last query row
	static unsigned long	ParseULong(const string& source, bool *result=NULL );       ///Reads unsigned long from the last query row
	static bool				ParseBool(const string& source, bool *result=NULL );        ///Reads bool from the last query row
	static double			ParseDouble(const string& source, bool *result=NULL );      ///Reads double from the last query row
	static string			ParseString(const string& source, bool *result=NULL );      ///Reads string from the last query row
	static time_t			ParseUnixTime(const string& source, bool *result=NULL );    ///Reads string from the last query row
};


}
#endif // StringUtils_h__

