#pragma warning(disable:4800)
#include "Tests/catch.hpp"
#include "Tests/tests.h"

#include "CCDB/Providers/MySQLDataProvider.h"
#include "CCDB/Model/Directory.h"
#include "CCDB/Model/Variation.h"

using namespace std;
using namespace ccdb;

/********************************************************************* ** 
 * @brief Test of directories work
 *
 * @return true if test passed
 */
TEST_CASE("CCDB/MySQLDataProvider/RunRanges","RunRanges tests")
{
	
	MySQLDataProvider *prov = new MySQLDataProvider();
	if(!prov->Connect(TESTS_CONENCTION_STRING)) return;

    // GET RUN-RANGE TEST
    //----------------------------------------------------
    
    //Get run range by name, test "all" run range	
	RunRange *rrange = prov->GetRunRange(CCDB_ALL_RUNRANGE_NAME);
	REQUIRE(rrange!=NULL);
	
	//Get run range by min and max run values
	rrange = prov->GetRunRange(0, 2000);
	REQUIRE(rrange!=NULL);


    // NON EXISTENT RUN RANGE
    //----------------------------------------------------
    //Get run range that is not defined
    rrange = prov->GetRunRange(0, 2001);

    
	
}