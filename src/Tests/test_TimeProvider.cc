#include "Tests/catch.hpp"

#include "CCDB/Helpers/TimeProvider.h"
#include <vector>
#include <string>


using namespace std;
using namespace ccdb;

TEST_CASE("CCDB/TimeProvider/Success", "System get time tests")
{
	// global setup...
    time_t x = 0; 
	REQUIRE_NOTHROW(x = TimeProvider::GetUnixTimeStamp(ClockSources::Monotonic));

}

TEST_CASE("CCDB/TimeProvider/Failure", "Test feature")
{
    // global setup...
    time_t x = 0; 
    TimeProvider::SetTimeUnitTest(true);
    REQUIRE(TimeProvider::GetTimeUnitTest());

    TimeProvider::SetUnitTestTime(100);
    REQUIRE(TimeProvider::GetUnixTimeStamp(ClockSources::Monotonic)==100);
    
    //disable unit test fixed time
    TimeProvider::SetTimeUnitTest(false);

}
