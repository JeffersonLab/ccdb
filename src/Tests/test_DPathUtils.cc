#ifndef test_DStringUtils_h
#define test_DStringUtils_h

#include "DPathUtils.h"
#include <vector>
#include <string>
#include "Tests/tests_macros.h"

using namespace std;
using namespace ccdb;

bool test_DPathUtils()
{
	TESTS_INIT(" --- D P a t h   U t i l s   t e s t s --- ")


    // * * * try to parse simple path  * * * 
    gConsole.WriteLine(DConsole::cBrightWhite, "[ Parse simple request '/my/value' ]");

    string path("/my/value");
    DParseRequestResult result= DPathUtils::ParseRequest(path);

    TITLE("Path is correct");          TEST(result.Path == path);
    TITLE("Was parsed Path");          TEST(result.WasParsedPath);
    TITLE("Was not parsed RunNumber"); TEST(!result.WasParsedRunNumber);
    TITLE("Was not parsed Variation"); TEST(!result.WasParsedVariation);
    TITLE("Was not parsed Time");      TEST(!result.WasParsedTime);


    // * * * parse full request  * * * 
    gConsole.WriteLine(DConsole::cBrightWhite, "[ Parse '/my/value:100:mc:2029' ]");
    
    path.assign("/my/value:100:mc:2029");
    result= DPathUtils::ParseRequest(path);

    //now tests
    TITLE("Path is correct");          TEST(result.Path == "/my/value");
    TITLE("Was parsed Path");          TEST(result.WasParsedPath);
    TITLE("Run number is correct");    TEST(result.RunNumber == 100);
    TITLE("Is valid run number");      TEST(!result.IsInvalidRunNumber);
    TITLE("Was parsed RunNumber");     TEST(result.WasParsedRunNumber);
    TITLE("Variation is correct");     TEST(result.Variation == "mc");
    TITLE("Was parsed Variation");     TEST(result.WasParsedVariation);
    TITLE("Time is not 0");            TEST(result.Time != 0);
    TITLE("Was parsed Time");          TEST(result.WasParsedTime);
    
    // * * * parse part of request  * * * 
    gConsole.WriteLine(DConsole::cBrightWhite, "[ Parse '/my/value::mc' ]");

    path.assign("/my/value::mc");
    result= DPathUtils::ParseRequest(path);

    TITLE("Path is correct");          TEST(result.Path == "/my/value");
    TITLE("Was parsed Path");          TEST(result.WasParsedPath);
    TITLE("Was not parsed RunNumber"); TEST(!result.WasParsedRunNumber);
    TITLE("Variation is correct");     TEST(result.Variation == "mc");
    TITLE("Was parsed Variation");     TEST(result.WasParsedVariation);
    TITLE("Was not parsed Time");      TEST(!result.WasParsedTime);

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
#endif //test_DStringUtils_h