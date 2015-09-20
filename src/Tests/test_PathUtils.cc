#ifndef test_StringUtils_h
#define test_StringUtils_h


#include "Tests/catch.hpp"

#include "CCDB/Helpers/PathUtils.h"

#include <vector>
#include <string>
#include <time.h>

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
}


TEST_CASE("CCDB/PathUtils/Time", "Time parse")
{
	//new year eve of 2011
	tm time;
	time.tm_year = 111; //+1900 = 2011
	time.tm_mon = 11;
	time.tm_mday = 31;
	time.tm_hour = 23;
	time.tm_min = 59;	
	time.tm_sec = 59;	
	time.tm_isdst = -1;

	bool success; 
	time_t tester = mktime(&time);
	time_t result = PathUtils::ParseTime("2011", &success);
	REQUIRE(tester == result);

	time.tm_year = 111; //+1900 = 2011
	time.tm_mon = 7; //since month [0-11]
	time.tm_mday = 31;
	time.tm_hour = 23;
	time.tm_min = 59;	
	time.tm_sec = 59;	
	time.tm_isdst = -1;
	tester = mktime(&time);
	result = PathUtils::ParseTime("2011-08", &success);
	REQUIRE(tester == result);
	REQUIRE(success);

	time.tm_year = 111; //+1900 = 2011
	time.tm_mon = 7; //since month [0-11]
	time.tm_mday = 17;
	time.tm_hour = 23;
	time.tm_min = 59;	
	time.tm_sec = 59;	
	time.tm_isdst = -1;
	tester = mktime(&time);
	result = PathUtils::ParseTime("2011-08-17", &success);
	REQUIRE(tester == result);
	REQUIRE(success);

	time.tm_year = 111; //+1900 = 2011
	time.tm_mon = 7; //since month [0-11]
	time.tm_mday = 17;
	time.tm_hour = 14;
	time.tm_min = 30;	
	time.tm_sec = 59;	
	time.tm_isdst = -1;
	tester = mktime(&time);
	result = PathUtils::ParseTime("2011-08-17 14:30", &success);
	REQUIRE(tester == result);
	REQUIRE(success);

	time.tm_year = 111; //+1900 = 2011
	time.tm_mon = 7; //since month [0-11]
	time.tm_mday = 17;
	time.tm_hour = 14;
	time.tm_min = 30;	
	time.tm_sec = 20;	
	time.tm_isdst = -1;
	tester = mktime(&time);
	result = PathUtils::ParseTime("2011-08-17 14:30:20", &success);
	REQUIRE(tester == result);
	REQUIRE(success);

	time.tm_year = 112; //+1900 = 2011
	time.tm_mon = 6;
	time.tm_mday = 12;
	time.tm_hour = 06;
	time.tm_min = 30;	
	time.tm_sec = 15;	
	time.tm_isdst=-1;
	tester = mktime(&time);
	result = PathUtils::ParseTime("2012 07 12 06:30:15", &success);
	REQUIRE(tester == result);
	REQUIRE(success);

	//! success
	result = PathUtils::ParseTime("2011-08-17 14:30:", &success);
	REQUIRE_FALSE(success);
}


TEST_CASE("CCDB/PathUtils/Context", "Context parse")
{
	//empty string
	ContextParseResult result = PathUtils::ParseContext("");
	REQUIRE(result.ConstantsTimeIsParsed == false);
	REQUIRE(result.VariationIsParsed == false);
	REQUIRE(result.RunNumberIsParsed == false);

	//empty string 2
	result = PathUtils::ParseContext(" ");
	REQUIRE(result.ConstantsTimeIsParsed == false);
	REQUIRE(result.VariationIsParsed == false);
	REQUIRE(result.RunNumberIsParsed == false);

	result = PathUtils::ParseContext("variation=james time=2012 run=123");
	REQUIRE(result.ConstantsTimeIsParsed == false);
	REQUIRE(result.VariationIsParsed == true);
	REQUIRE(result.RunNumberIsParsed == true);
	REQUIRE(result.Variation == "james");
	REQUIRE(result.RunNumber == 123);

	result = PathUtils::ParseContext("run=123 variation=james calibtime=2012 ");
	REQUIRE(result.ConstantsTimeIsParsed == true);
	REQUIRE(result.VariationIsParsed == true);
	REQUIRE(result.RunNumberIsParsed == true);
	REQUIRE(result.Variation == "james");
	REQUIRE(result.RunNumber == 123);
}
#endif //test_StringUtils_h
