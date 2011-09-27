#include "Tests/catch.h"
#include <iostream>
#include "CCDB/Console.h"
#include "CCDB/Helpers/StringUtils.h"
using namespace std;
using namespace ccdb;

TEST_CASE( "CCDB/Console", "Console testing" )
{
    Console console;
    console.SetUseColors(true);
    //
    //Wite line test
    console.WriteLine("test console.WriteLine %i \n",6);

    //write test
    console.Write("test %i |",6);
    console.Write(" Write |");
    console.WriteLine(" and WriteLine |");

    REQUIRE( 1==1 );
    REQUIRE( 2==2 );
    REQUIRE( 3==3 );
    REQUIRE( 4==4 );
    REQUIRE( 3 );
}