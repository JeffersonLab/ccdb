#include <cerrno>
#include <climits>
#include <cstdlib>
#include <cstring>

#include "CCDB/Helpers/StringUtils.h"

using namespace std;
using namespace ccdb;

namespace
{
    // Encode replaces '&' first and Decode replaces "&amp;" last, so an encoded "&lt;" decodes to "&lt;" again
    const char* const gEntities[][2] = {{"&", "&amp;"}, {"<", "&lt;"}, {">", "&gt;"}, {"\"", "&quot;"}};
    const size_t gEntityCount = sizeof(gEntities) / sizeof(gEntities[0]);

    /// Whether the text, blanks around it aside, ended where the number ended
    bool OnlyBlanksAfter(const char* end)
    {
        while (*end && CCDB_CHECK_CHAR_IS_BLANK(*end)) end++;
        return *end == '\0';
    }

    /// strtol-style parse with the whole-text and range check of the Parse functions
    template<typename Number, typename Parse>
    Number ParseNumber(const string& source, bool* result, Parse parse)
    {
        const char* begin = source.c_str();
        char* end = nullptr;
        errno = 0;
        Number value = parse(begin, &end);
        if (result) *result = end != begin && errno != ERANGE && OnlyBlanksAfter(end);
        return value;
    }
}


std::string ccdb::StringUtils::Encode(const string& source)
{
    string encoded;
    encoded.reserve(source.size());
    for (char symbol: source) {
        size_t i = 0;
        while (i < gEntityCount && symbol != gEntities[i][0][0]) i++;
        if (i < gEntityCount) encoded += gEntities[i][1]; else encoded += symbol;
    }
    return encoded;
}


std::string ccdb::StringUtils::Decode(const string& source)
{
    string decoded;
    decoded.reserve(source.size());
    for (size_t position = 0; position < source.size(); ) {
        size_t i = 0;
        while (i < gEntityCount && source.compare(position, strlen(gEntities[i][1]), gEntities[i][1]) != 0) i++;
        if (i < gEntityCount) {
            decoded += gEntities[i][0];
            position += strlen(gEntities[i][1]);
        }
        else {
            decoded += source[position++];
        }
    }
    return decoded;
}


//_____________________________________________________________________________________________________________
int ccdb::StringUtils::Replace(const string& pattern, const string& replace, const string& source, string &out)
{
    int matches = 0;
    out.assign(source);

    string::size_type start = out.find( pattern );

    // Replace all matches
    while ( start != string::npos ) {
        matches++;
        out.replace( start, pattern.size(), replace );
        // Be sure to jump forward by the replacement length
        start = out.find( pattern, start + replace.size() );
    }
    return matches;
}


//___________________________________________________________________________________________________
string ccdb::StringUtils::Replace(const string& pattern, const string& replace, const string& source)
{
    string out("");
    Replace(pattern, replace, source, out);
    return out;
}

//______________________________________________________________________________
bool ccdb::StringUtils::WildCardCheck( const char* pattern, const char* source )
{
    // Greedy match with one backtrack point: the last '*' and the source position it was tried at
    const char* star = nullptr;
    const char* resume = nullptr;
    while (*source) {
        if (*pattern == '*') {
            star = pattern++;
            resume = source;
        }
        else if (*pattern == '?' || *pattern == *source) {
            pattern++;
            source++;
        }
        else if (star) {
            pattern = star + 1;
            source = ++resume;
        }
        else {
            return false;
        }
    }
    while (*pattern == '*') pattern++;
    return *pattern == '\0';
}


//___________________________________________________________________________________________________________
std::vector<std::string> ccdb::StringUtils::Split( const std::string &s, const string& delimiters /*= " "*/ )
{
    std::vector<std::string> elems;
    return Split(s, elems, delimiters);
}


//________________________________________________________________________________________________________________________
vector<string> & ccdb::StringUtils::Split( const string& str, vector<string>& tokens, const string& delimiters /*= " "*/ )
{
    // Skip delimiters at beginning.
    string::size_type lastPos = str.find_first_not_of(delimiters, 0);

    // Find first "non-delimiter".
    string::size_type pos     = str.find_first_of(delimiters, lastPos);

    while (string::npos != pos || string::npos != lastPos)
    {
        // Found a token, add it to the vector.
        tokens.push_back(str.substr(lastPos, pos - lastPos));
        // Skip delimiters.  Note the "not_of"
        lastPos = str.find_first_not_of(delimiters, pos);
        // Find next "non-delimiter"
        pos = str.find_first_of(delimiters, lastPos);
    }
    return tokens;
}


//______________________________________________________________________________
std::string ccdb::StringUtils::IntToString(int value, int base /*= 10*/)
{
    if (base == 10) return std::to_string(value);
    if (base < 2 || base > 36) return string();

    // the magnitude as unsigned, so the smallest int has one too
    unsigned long long magnitude = value < 0 ? 0ULL - static_cast<unsigned long long>(value) : static_cast<unsigned long long>(value);
    string digits;
    do {
        digits += "0123456789abcdefghijklmnopqrstuvwxyz"[magnitude % base];
        magnitude /= base;
    } while (magnitude);
    if (value < 0) digits += '-';
    return string(digits.rbegin(), digits.rend());
}


//______________________________________________________________________________
int ccdb::StringUtils::ParseInt( const string& source, bool *result/*=NULL*/  )
{
    long value = ParseNumber<long>(source, result, [](const char* text, char** end) { return std::strtol(text, end, 10); });
    if (result && (value < INT_MIN || value > INT_MAX)) *result = false;
    return static_cast<int>(value);
}


//______________________________________________________________________________
unsigned int ccdb::StringUtils::ParseUInt( const string& source, bool *result/*=NULL*/  )
{
    long value = ParseNumber<long>(source, result, [](const char* text, char** end) { return std::strtol(text, end, 10); });
    if (result && (value < 0 || value > static_cast<long>(UINT_MAX))) *result = false;
    return static_cast<unsigned int>(value);
}


//______________________________________________________________________________
long ccdb::StringUtils::ParseLong( const string& source, bool *result/*=NULL*/  )
{
    return ParseNumber<long>(source, result, [](const char* text, char** end) { return std::strtol(text, end, 10); });
}


//______________________________________________________________________________
unsigned long ccdb::StringUtils::ParseULong( const string& source, bool *result/*=NULL*/  )
{
    return ParseNumber<unsigned long>(source, result, [](const char* text, char** end) { return std::strtoul(text, end, 10); });
}


//______________________________________________________________________________
bool ccdb::StringUtils::ParseBool( const string& source, bool *result/*=NULL*/  )
{
    if(source=="true") { if (result) *result = true; return true; }
    if(source=="false") { if (result) *result = true; return false; }
    return ParseInt(source, result) != 0;
}

//___________________________________________________________________________________
double ccdb::StringUtils::ParseDouble( const string& source, bool *result/*=NULL*/  )
{
    return ParseNumber<double>(source, result, [](const char* text, char** end) { return std::strtod(text, end); });
}

//_______________________________________________________________________________________
std::string ccdb::StringUtils::ParseString( const string& source, bool *result/*=NULL*/  )
{
    if (result) *result = true;
    return string(source);
}


//_______________________________________________________________________________________
time_t ccdb::StringUtils::ParseUnixTime( const std::string& source, bool *result/*=NULL*/  )
{   
    return static_cast<time_t>(ParseULong(source, result));
}



//____________________________________________________________________________________________
void ccdb::StringUtils::LexicalSplit(std::vector<std::string>& tokens, const std::string& source)
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


//______________________________________________________________________________
std::string ccdb::StringUtils::MaskPassword(const std::string& connectionString)
{
    size_t schemeEnd = connectionString.find("://");
    size_t userStart = (schemeEnd == std::string::npos) ? 0 : schemeEnd + 3;

    size_t atPos = connectionString.rfind('@');
    if(atPos == std::string::npos || atPos < userStart) return connectionString;

    size_t colonPos = connectionString.find(':', userStart);
    if(colonPos == std::string::npos || colonPos > atPos) return connectionString;   // user name only

    return connectionString.substr(0, colonPos + 1) + "***" + connectionString.substr(atPos);
}
