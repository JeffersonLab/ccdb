#include "Tests/catch.h"

#include "CCDB/Helpers/TimeProvider.h"
#include <vector>
#include <string>


using namespace std;
using namespace ccdb;

TEST_CASE("CCDB/TimeProvider", "System get time tests")
{
	// global setup...
    time_t x = 0; 
	REQUIRE_NOTHROW(x = TimeProvider::GetUnixTimeStamp(ClockSources::Monotonic));

}

TEST_CASE("CCDB/TimeProvider", "Test feature")
{
    // global setup...
    time_t x = 0; 
    TimeProvider::SetTimeUnitTest(true);
    REQUIRE(TimeProvider::GetTimeUnitTest());

    TimeProvider::SetUnitTestTime(100);
    REQUIRE(TimeProvider::GetUnixTimeStamp(ClockSources::Monotonic)==100);
    TimeProvider::SetTimeUnitTest(false);

}
