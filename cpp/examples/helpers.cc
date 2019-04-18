/**
 * Example shows how to manipulate with Assignment object to get 
 * extended information about data fields.
 */

#include <CCDB/Calibration.h>
#include <CCDB/CalibrationGenerator.h>
#include <CCDB/SQLiteCalibration.h>
#include <CCDB/Model/Assignment.h>
#include <CCDB/Model/ConstantsTypeColumn.h>
#include <CCDB/Helpers/PathUtils.h>

#include <stdio.h>
#include <string>
#include <vector>
#include <memory>
#include <stdlib.h>     

using namespace std;
using namespace ccdb;

string create_connection_string()
{
	/** creates example connection string to ccdb demo sqlite database*/
	string ccdb_home(getenv("CCDB_HOME"));
	return string("sqlite://" + ccdb_home + "/sql/ccdb.sqlite");
}


int main()
{
	
	// PathUtils::ParseTime
    // parses time as any part of
    // YYYY:MM:DD-hh:mm:ss
    // 
    // 1) in place of ':' and '-' might be any ONE non digit character
    // 
    // 2) One could place only part of the string,
    //    the latest date for this part will be returned.
    //    I.e. if timeString is "2011" - (it means the year 2011 and nothing more),
    //    this function returns result as if it were 2011:12:31-23:59:59
    //    thus using such timestamp would get the latest constants for year 2011
    // 
    // @parameter [in] const string & timeString string to parse
    // @parameter [out] succsess true if success
    // @return   time_t
    // 
    bool success; 
    time_t parsedTime= PathUtils::ParseTime("2020/11/29 14:00", &success);
    cout << "'2020/11/29 14:00' parsed. Succes="<<success<<"  time_t="<<parsedTime<<endl;
    
    
    // PathUtils::ParseContext
    // Parses context string and returns ContextParseResult structure
    // 
    // CONTEXT is a string that may contain default values for CCDB
    // example of context string:
    // 'variation=default calibtime=2012'
    // parameters and values are separated by '=' (!) WITH NO SPACES
    // 
    ContextParseResult result = PathUtils::ParseContext("variation=mc calibtime=2012");
    cout<<"Context parse result:"<<endl;
    cout<<"  VariationIsParsed    : "<<result.VariationIsParsed     <<endl;         // true if variation was not empty
    cout<<"  Variation            : "<<result.Variation             <<endl<<endl;	 // Variation name
    cout<<"  ConstantsTimeIsParsed: "<<result.ConstantsTimeIsParsed <<endl;         //
    cout<<"  ConstantsTime        : "<<result.ConstantsTime         <<endl;
	
	 
}
