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

    /** @brief Encodes string to add to DB
     * Encode
     *
     * @param     const string & source
     * @return   std::string
     */
    static std::string    Encode(const std::string& source);

    /** @brief Decode string from encoded string
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


    /** itoa implementation for string
     *  C++ version 0.4 char* style "itoa": Written by Lukas Chmela
     *  Released under GPLv3.
     * @remark:
     * It is proved by benchmarking that writing int to C buffer and making it a string at the end is the fastest way of getting string from int
     */
    static std::string IntToString(int value, int base = 10)
    {
        /**
         * C++ version 0.4 char* style "itoa":
         * Written by Lukas Chmela
         * Released under GPLv3.
         */

        char result[50];

        // check that the base if valid
        if (base < 2 || base > 36) { *result = '\0'; return result; }

        char* ptr = result, *ptr1 = result, tmp_char;
        int tmp_value;

        do {
            tmp_value = value;
            value /= base;
            *ptr++ = "zyxwvutsrqponmlkjihgfedcba9876543210123456789abcdefghijklmnopqrstuvwxyz" [35 + (tmp_value - value * base)];
        } while ( value );

        // Apply negative sign
        if (tmp_value < 0) *ptr++ = '-';
        *ptr-- = '\0';
        while(ptr1 < ptr) {
            tmp_char = *ptr;
            *ptr--= *ptr1;
            *ptr1++ = tmp_char;
        }
        return std::string(result);

    }

    static int              ParseInt(const std::string& source, bool *result=nullptr );         ///Reads int    from the last query row
    static unsigned int     ParseUInt(const std::string& source, bool *result=nullptr );        ///Reads unsigned int from the last query row
    static long             ParseLong(const std::string& source, bool *result=nullptr );        ///Reads long from the last query row
    static unsigned long    ParseULong(const std::string& source, bool *result=nullptr );       ///Reads unsigned long from the last query row
    static bool             ParseBool(const std::string& source, bool *result=nullptr );        ///Reads bool from the last query row
    static double           ParseDouble(const std::string& source, bool *result=nullptr );      ///Reads double from the last query row
    static std::string      ParseString(const std::string& source, bool *result=nullptr );      ///Reads string from the last query row
    static time_t           ParseUnixTime(const std::string& source, bool *result=nullptr );    ///Reads string from the last query row
};
}
#endif // StringUtils_h__
