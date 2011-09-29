///
/// This is the simplest unit tests. 
/// Also the definition CATCH_CONFIG_MAIN means that Catch Unit Test framework will generate 'main' function. 
/// This define should be placed only once among all files wich contain tests
/// See more on the catch test framework here. 
/// https://github.com/philsquared/Catch
///
///==========================================================================================================

#define CATCH_CONFIG_MAIN  // This tell CATCH to provide a main() - only do this in one cpp file

#include "Tests/catch.h"

using namespace std;

///This defines test method. CCDB/CatchUnitTests has a nested structure of categories
TEST_CASE( "CCDB/CatchUnitTests", "Unit tests test" )
{
    //REQUIRE is an assertion that the 
    REQUIRE( 1==1 );
}