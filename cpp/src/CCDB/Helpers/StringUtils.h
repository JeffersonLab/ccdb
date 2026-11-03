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


#define CCDB_BLANK_CHARACTERS " \n\t\v\r\f"
//checks if character is blank.
//returns true if char is one of CCDB_BLANK_CHARACTERS
#define CCDB_CHECK_CHAR_IS_BLANK(character) ((character)==' ' || (character)=='\n' || (character)=='\t' || (character)=='\v' || (character)=='\r' || (character)=='\f')


namespace ccdb
{

#define array_length(array) (sizeof (array) / sizeof (array)[0])


struct AssignmentRequest
{
    std::string Path;
    int         RunNumber;
    std::string Variation;
    time_t      Time;
};

class StringUtils
{
public:

    /** @brief HTML-escapes &, <, > and " (as &amp; &lt; &gt; &quot;)
     *
     * @param     const string & source
     * @return   std::string
     */
    static std::string    Encode(const std::string& source);

    /** @brief Reverses Encode: &amp; &lt; &gt; &quot; back to & < > "; other text is unchanged
     *
     * @param     const string & source
     * @return   std::string
     */
    static std::string    Decode(const std::string& source);

    /** @brief string Replace
     *
     * @param     const string & pattern
     * @param     const string & replace
     * @param     const string & source
     * @param     string & out
     * @return   int
     */
    static int        Replace(const std::string& pattern, const std::string& replace, const std::string& source, std::string &out);

    /** @brief String Replace
     *
     * @param     const string & pattern
     * @param     const string & replace
     * @param     const string & source
     * @return   std::string
     */
    static std::string    Replace(const std::string& pattern, const std::string& replace, const std::string& source);

    /** @brief Whether source matches pattern as a whole, '*' standing for any text and '?' for one character
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
    static std::vector<std::string> &Split(const std::string& str, std::vector<std::string>& tokens, const std::string& delimiters = " ");


    /** @brief
     * Split
     *
     * @param     const std::string & s
     * @param     char delimiters
     * @return   std::vector<std::string>
     */
    static std::vector<std::string> Split(const std::string &s, const std::string& delimiters = " ");


    /**
     * @brief Hides the password of a connection string for use in messages and logs
     *
     * "mysql://user:secret@host/db" => "mysql://user:***@host/db"
     * Everything between the first ':' after "://" and the last '@' is masked,
     * so a password that itself contains '@' is hidden completely.
     * Strings without a password are returned unchanged.
     */
    static std::string MaskPassword(const std::string& connectionString);



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
    static  void Trim( std::string& s )
    {
        // Remove leading and trailing whitespace
        static const char whitespace[] = CCDB_BLANK_CHARACTERS;
        s.erase( 0, s.find_first_not_of(whitespace) );
        s.erase( s.find_last_not_of(whitespace) + 1U );
    }

    /** Splits string to lexical values.
     *
     * LexicalSplit treats:
     * 1) "quoted values" as one value,
     * 2) '#' not in the beginning of the file are treated as comments to the end of the line
     * 3) skips all white space characters. All specification is in doc/ccdb_file_format.pdf
     *
     * @remark
     * Handling inconsistencies and errors while readout parse time:
     *  -  No ending quote . If no ending " is found, string value will be taken
     *     until the end of line.
     *  -  Comment inside a string. Comment symbol inside the line is ignored.
     *     So if you have a record in the file "info #4" it will be read just
     *     as "info #4" string
     *  -  Sticked string. In case of there is no spaces between symbols and
     *     an quotes, all will be merged as one string. I.e.:
     *     John" Smith" will be parsed as one value: "John Smith"
     *     John" "Smith will be parsed as one value: "John Smith"
     *     but be careful(!) not to forget to do a spaces between columns
     *     5.14"Smith" will be parsed as one value "5.14Smith" that probably would
     *     lead to errors if these were two different columns
     *  -  If data contains string fields they are taken into "..." characters. All "
     *     inside string should be saved by \" symbol. All words and symbols
     *     inside "..." will be interpreted as string entity.
     *
     */
    static std::vector<std::string> LexicalSplit(const std::string& source) {
        std::vector<std::string> tokens;
        LexicalSplit(tokens, source);
        return tokens;
    }

      /** Splits string to lexical values.
     *
     * LexicalSplit treats:
     * 1) "quoted values" as one value,
     * 2) '#' not in the beginning of the file are treated as comments to the end of the line
     * 3) skips all white space characters. All specification is in doc/ccdb_file_format.pdf
     *
     * @remark
     * Handling inconsistencies and errors while readout parse time:
     *  -  No ending quote . If no ending " is found, string value will be taken
     *     until the end of line.
     *  -  Comment inside a string. Comment symbol inside the line is ignored.
     *     So if you have a record in the file "info #4" it will be read just
     *     as "info #4" string
     *  -  Sticked string. In case of there is no spaces between symbols and
     *     an quotes, all will be merged as one string. I.e.:
     *     John" Smith" will be parsed as one value: "John Smith"
     *     John" "Smith will be parsed as one value: "John Smith"
     *     but be careful(!) not to forget to do a spaces between columns
     *     5.14"Smith" will be parsed as one value "5.14Smith" that probably would
     *     lead to errors if these were two different columns
     *  -  If data contains string fields they are taken into "..." characters. All "
     *     inside string should be saved by \" symbol. All words and symbols
     *     inside "..." will be interpreted as string entity.
     *
     */
    static void LexicalSplit(std::vector<std::string>& tokens, const std::string& source);


    /** @brief The text of an integer in a base from 2 to 36, lower-case digits, '-' before a negative value
     *
     * Base 10 is std::to_string. An invalid base gives an empty string.
     */
    static std::string IntToString(int value, int base = 10);

    /* The Parse functions read text as the C library does (std::strtol, std::strtoul, std::strtod): leading blanks and
     * a sign are allowed, the number is the longest valid prefix, text without one gives 0. When `result` is given it
     * is set to true only if the whole text, blanks around it aside, was a number in range. ParseBool takes "true",
     * "false" or an integer (not 0 is true). */
    static int              ParseInt(const std::string& source, bool *result=nullptr );         ///Reads an int
    static unsigned int     ParseUInt(const std::string& source, bool *result=nullptr );        ///Reads an unsigned int
    static long             ParseLong(const std::string& source, bool *result=nullptr );        ///Reads a long
    static unsigned long    ParseULong(const std::string& source, bool *result=nullptr );       ///Reads an unsigned long
    static bool             ParseBool(const std::string& source, bool *result=nullptr );        ///Reads a bool
    static double           ParseDouble(const std::string& source, bool *result=nullptr );      ///Reads a double
    static std::string      ParseString(const std::string& source, bool *result=nullptr );      ///The text itself
    static time_t           ParseUnixTime(const std::string& source, bool *result=nullptr );    ///Reads seconds since the epoch
};
}
#endif // StringUtils_h__
