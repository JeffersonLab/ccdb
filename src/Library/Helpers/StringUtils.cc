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
std::string ccdb::StringUtils::vFormat( const char *fmt, va_list ap)
{
    // Formats a string using a printf style format descriptor.
    // Existing string contents will be overwritten.

    size_t buflen = 20 + 20 * strlen(fmt);    // pick a number, any strictly positive number
    char *buffer = (char*)malloc(buflen);
    if (buffer == NULL)
    {
        //Aha! It is an error!
        fprintf(stderr, "Error allocating memory in ccdb::Console::vFormat( const char *fmt, va_list ap) ");
        return string();
    }

    va_list sap;
    D__VA_COPY(sap, ap);

   int n, vc = 0;
again:
   n = vsnprintf(buffer, buflen, fmt, ap);
   // old vsnprintf's return -1 if string is truncated new ones return
   // total number of characters that would have been written
   if (n == -1 || n >= buflen) {
      if (n == -1)
         buflen *= 2;
      else
         buflen = n+1;
      buffer = (char*)realloc(buffer, buflen);
      va_end(ap);
      D__VA_COPY(ap, sap);
      vc = 1;
      goto again;
   }
   va_end(sap);
   if (vc)
      va_end(ap);
   return string(buffer);
}

std::string ccdb::StringUtils::Format(const char *va_(fmt), ...)
{
   // Static method which formats a string using a printf style format
   // descriptor and return a TString. Same as TString::Form() but it is
   // not needed to first create a TString.

   va_list ap;
   va_start(ap, va_(fmt));
   string str(vFormat(va_(fmt), ap));
   va_end(ap);
   return str;
}   

//std::string ccdb::StringUtils::vFormat( const char *fmt, va_list ap)
//{
//  // The function is quite similar to asprintf
//  // but it uses its implementation that assumes, that the message is short
//  // since it is our case...
//
//  //lets assume we have less than 150 chars buffer
//  int size = 150;
//  int nchars;
//  va_list ap2;
//
//  char *buffer = (char*)malloc(size);
//  if (buffer == NULL)
//  {
//      //Aha! It is an error!
//      fprintf(stderr, "Error allocating memory in ccdb::Console::vFormat( const char *fmt, va_list ap) ");
//      return string();
//  }
//
//  //Try to print in the allocated space.
//  //va_start(ap, fmt);
//  va_copy(ap2, ap);
//  //nchars = vsnprintf(buffer, size, fmt, ap2);
//  nchars = vsnprintf(buffer, size, fmt, ap2);
//  //va_end(ap);
//
//  //Ok! It is some more C++ crap
//  // in linux vsnprintf will return actual number of characters if size of buffer is smaller than needed,
//  // moreover, the buffer could be NULL, and than the actual number of characters will be returned
//  // in windows it return -1, so if it is -1 we have to use one more function to obtain needed chars num
//  if(nchars<0)
//  {
//#ifdef WIN32
//      va_end(ap2);
//      va_copy(ap2, ap);
//      nchars = _vscprintf(fmt, ap2);
//#endif
//  }
//
//  if (nchars >= size)
//  {
//      char *tmpbuff;
//
//      // Reallocate buffer now that we know how much space is needed.
//      size = nchars+1;
//      tmpbuff = (char*)realloc(buffer, size);
//
//      if (tmpbuff == NULL)
//      {
//          // we need to free it
//          free(buffer);
//          fprintf(stderr, "Error allocating memory ccdb::Console::vFormat( const char *fmt, va_list ap)");
//          return string();
//      }
//
//      //ok! lets try again.
//      va_end(ap2);
//      //va_end(ap);
//
//      va_copy(ap2, ap);
//      buffer=tmpbuff;
//      nchars = vsnprintf(buffer, size, fmt, ap2);
//      //nchars = vsnprintf(buffer, size, fmt, ap);
//      va_end(ap);
//  }
//
//  va_end(ap2);
//  if (nchars < 0) return string();
//
//  //looks like alll is okk
//  return string(buffer);
//}

//std::string ccdb::StringUtils::Format( const char *fmt, ... )
//{
//  //format
//  va_list ap;
//  va_start(ap, fmt);
//  string str = vFormat(fmt, ap);
//  va_end(ap);
//  return str;
//}

#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>


//______________________________________________________________________________
char * make_message(const char *fmt, ...) 
{
        /* Guess we need no more than 100 bytes. */
        int n, size = 100;
        char *p, *np;
        va_list ap;

        if ((p = (char *) malloc (size)) == NULL)
            return NULL;

        while (1) {
            /* Try to print in the allocated space. */
            va_start(ap, fmt);
            n = vsnprintf (p, size, fmt, ap);
            va_end(ap);
            /* If that worked, return the string. */
            if (n > -1 && n < size)
                return p;
            /* Else try again with more space. */
            if (n > -1)    /* glibc 2.1 */
                size = n+1; /* precisely what is needed */
            else           /* glibc 2.0 */
                size *= 2;  /* twice the old size */
            if ((np = (char *)realloc (p, size)) == NULL) {
                free(p);
                return NULL;
            } else {
                p = np;
            }
        }
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
time_t ccdb::StringUtils::ParseUnixTime( const string& source, bool *result/*=NULL*/  )
{   
    return static_cast<time_t>(ParseULong(source, result));
}


//______________________________________________________________________________
std::vector<string> ccdb::StringUtils::LexicalSplit( const std::string& source )
{
    //

    /** Splits string to lexical values.
    *
    * LexicalSplit treats:
    * 1) "quoted values" as one value,
    * 2) '#' not in the beginning of the file are treated as comments to the end of the line
    * 3) skips all white space characters. All specification is in doc/ccdb_file_format.pdf
    */
    std::vector<string> tokens;
    LexicalSplit(tokens, source);
    return tokens;
}
//____________________________________________________________________________________________
void ccdb::StringUtils::LexicalSplit( std::vector<string>& tokens, const std::string& source )
{
    //

    /** Splits string to lexical values.
    *
    * LexicalSplit treats:
    * 1) "quoted values" as one value,
    * 2) '#' not in the beginning of the file are treated as comments to the end of the line
    * 3) skips all white space characters. All specification is in doc/ccdb_file_format.pdf
    * 
    * @remark
    * Handling inconsistencies and errors while readout parse time:
    *  ?  No ending quote . If no ending “ is found, string value will be taken
    *     until the end of line.
    *  ?  Comment inside a string. Comment symbol inside the line is ignored. 
    *     So if you have a record in the file “info #4” it will be read just
    *     as “info #4” string
    *  ?  Sticked string. In case of there is no spaces between symbols and
    *     an quotes, all will be merged as one string. I.e.:
    *     John" Smith" will be parsed as one value: "John Smith"
    *     John" "Smith will be parsed as one value: "John Smith"
    *     but be careful(!) not to forget to do a spaces between columns
    *     5.14”Smith” will be parsed as one value “5.14Smith” that probably would
    *     lead to errors if these were two different columns
    *  ?  If data contains string fields they are taken into “...” characters. All “
    *     inside string should be saved by \” symbol. All words and symbols
    *     inside “...” will be interpreted as string entity.
    *
    */
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

