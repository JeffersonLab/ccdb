#define CATCH_CONFIG_MAIN  // This tell CATCH to provide a main() - only do this in one cpp file
#include "Tests/catch.h"
#include <iostream>
#include "CCDB/Console.h"
#include "CCDB/Helpers/StringUtils.h"
using namespace std;
using namespace ccdb;

TEST_CASE( "CCDB/StringUtils", "Console testing" )
{
    cout<<StringUtils::Format("test console.Format %i %f", 5, 3.14)<<endl;
    cout<<StringUtils::Format("test long string console.Format aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa %i %f", 5, 3.14)<<endl;

    REQUIRE( 1==1 );
    REQUIRE( 2==2 );
    REQUIRE( 3==3 );
    REQUIRE( 4==4 );
    REQUIRE( 3 );
}