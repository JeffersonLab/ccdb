#ifndef test_StringUtils_h
#define test_StringUtils_h


#include "Tests/catch.h"

#include "CCDB/Helpers/PathUtils.h"

#include <vector>
#include <string>


using namespace std;
using namespace ccdb;

TEST_CASE("CCDB/PathUtils", "Request parse")
{

    string path("/my/value");
    RequestParseResult result= PathUtils::ParseRequest(path);

    REQUIRE(result.Path == path);
    REQUIRE(result.WasParsedPath);
    REQUIRE(!result.WasParsedRunNumber);
    REQUIRE(!result.WasParsedVariation);
    REQUIRE(!result.WasParsedTime);


    // * * * parse full request  * * * 

    path.assign("/my/value:100:mc:2029");
    result= PathUtils::ParseRequest(path);

    //now tests
    REQUIRE(result.Path == "/my/value");
    REQUIRE(result.WasParsedPath);
    REQUIRE(result.RunNumber == 100);
    REQUIRE(!result.IsInvalidRunNumber);
    REQUIRE(result.WasParsedRunNumber);
    REQUIRE(result.Variation == "mc");
    REQUIRE(result.WasParsedVariation);
    REQUIRE(result.Time != 0);
    REQUIRE(result.WasParsedTime);
    
    // * * * parse part of request  * * * 
    path.assign("/my/value::mc");
    result= PathUtils::ParseRequest(path);

    REQUIRE(result.Path == "/my/value");
    REQUIRE(result.WasParsedPath);
    REQUIRE(!result.WasParsedRunNumber);
    REQUIRE(result.Variation == "mc");
    REQUIRE(result.WasParsedVariation);
    REQUIRE(!result.WasParsedTime);

    //now tests
    //result.RunNumber=0;	              // Run number
    //result.WasParsedRunNumber=false;  // true if Run number was non empty
    //result.IsInvalidRunNumber=false;  // true if was an error parsing runnumber
    //result.Path = "";                 // Object path
    //result.WasParsedPath=false;       // true if Path was nonempty
    //result.Variation="";              // Variation name
    //result.WasParsedVariation=false;  // true if variation was not empty
    //result.Time=0;                    // Time stamp
    //result.WasParsedTime=false;       // true if time stamp was not empty
    //result.TimeString="";             // Original string with time
}


TEST_CASE("CCDB/PathUtils", "Context parse")
{
	//empty string
	ContextParseResult result = PathUtils::ParseContext("");
	REQUIRE(result.ConstantsTimeIsParsed == false)
	REQUIRE(result.VariationIsParsed == false)

	//empty string 2
	result = PathUtils::ParseContext(" ");
	REQUIRE(result.ConstantsTimeIsParsed == false)
	REQUIRE(result.VariationIsParsed == false)

	result = PathUtils::ParseContext("variation=james time=2012");
	REQUIRE(result.ConstantsTimeIsParsed == false)
	REQUIRE(result.VariationIsParsed == true)
	REQUIRE(result.Variation == "james")

}
#endif //test_StringUtils_h