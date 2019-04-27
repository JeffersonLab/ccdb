#include <cstdlib>

#include "CCDB/Helpers/StringUtils.h"

using namespace std;
using namespace ccdb;

struct DHTMLReplace {
    string match;
    string replace;
} gHTMLReplaceCodes[] = {
    {"&", "&amp;"},
    {"<", "&lt;"}, 
    {">", "&gt;"},
    {"\"","&quot;"}
};

std::string ccdb::StringUtils::Decode(const string& source )
{
    string rs = source;

    // Replace each matching token in turn
    for ( size_t i = 0; i < array_length( gHTMLReplaceCodes ); i++ ) {
        // Find the first match
        const string& match = gHTMLReplaceCodes[i].replace;
        const string& repl = gHTMLReplaceCodes[i].match;
        string::size_type start = rs.find_first_of( match );

        // Replace all matches
        while ( start != string::npos ) {
            rs.replace( start, match.size(), repl );
            // Be sure to jump forward by the replacement length
            start = rs.find_first_of( match, start + repl.size() );
        }
    }

    return rs;
}

std::string ccdb::StringUtils::Encode( const string& source )
{
    string rs = source;

    // Replace each matching token in turn
    for ( size_t i = 0; i < array_length( gHTMLReplaceCodes ); i++ ) {
        // Find the first match
        const string& match = gHTMLReplaceCodes[i].match;
        const string& repl = gHTMLReplaceCodes[i].replace;
        string::size_type start = rs.find_first_of( match );

        // Replace all matches
        while ( start != string::npos ) {
            rs.replace( start, match.size(), repl );
            // Be sure to jump forward by the replacement length
            start = rs.find_first_of( match, start + repl.size() );
        }
    }

    return rs;
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
    char *cp, *mp;
    while ((*source) && (*pattern != '*')) 
    {
        if ((*pattern != *source) && (*pattern != '?')) 
        {
                return 0;
        }

        pattern++;
        source++;
    }

    while (*source) 
    {
        if (*pattern == '*') 
        {
            if (!*++pattern) 
            {
                    return 1;
            }

            mp = const_cast<char *>(pattern);
            cp = const_cast<char *>(source+1);
        } 
        else if ((*pattern == *source) || (*pattern == '?')) 
        {
            pattern++;
            source++;
        } 
        else 
        {
            pattern = mp;
            source = cp++;
        }
    }

    while (*pattern == '*') 
    {
        pattern++;
    }

    return !*pattern;
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
int ccdb::StringUtils::ParseInt( const string& source, bool *result/*=NULL*/  )
{
    return atoi(source.c_str()); //ugly isn't it?
}


//______________________________________________________________________________
unsigned int ccdb::StringUtils::ParseUInt( const string& source, bool *result/*=NULL*/  )
{
    return static_cast<unsigned int>(atoi(source.c_str())); //ugly isn't it?
}


//______________________________________________________________________________
long ccdb::StringUtils::ParseLong( const string& source, bool *result/*=NULL*/  )
{
    return atol(source.c_str()); //ugly isn't it?
}


//______________________________________________________________________________
unsigned long ccdb::StringUtils::ParseULong( const string& source, bool *result/*=NULL*/  )
{
    return static_cast<unsigned long>(atol(source.c_str())); //ugly isn't it?
}


//______________________________________________________________________________
bool ccdb::StringUtils::ParseBool( const string& source, bool *result/*=NULL*/  )
{
    if(source=="true") return true;
    if(source=="false") return false;

    return static_cast<bool>(atoi(source.c_str())!=0); //ugly isn't it?
}

//___________________________________________________________________________________
double ccdb::StringUtils::ParseDouble( const string& source, bool *result/*=NULL*/  )
{
    return atof(source.c_str()); //ugly isn't it?
}

//_______________________________________________________________________________________
std::string ccdb::StringUtils::ParseString( const string& source, bool *result/*=NULL*/  )
{
    return string(source);
}


//_______________________________________________________________________________________
time_t ccdb::StringUtils::ParseUnixTime( const std::string& source, bool *result/*=NULL*/  )
{   
    return static_cast<time_t>(ParseULong(source, result));
}



//____________________________________________________________________________________________
void ccdb::StringUtils::LexicalSplit( std::vector<std::string>& tokens, const std::string& source )
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

