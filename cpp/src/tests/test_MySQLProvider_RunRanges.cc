#pragma warning(disable:4800)
#ifdef CCDB_MYSQL
#include "tests/catch.hpp"
#include "tests/tests.h"

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
	prov->Connect(get_test_mysql_connection());

    // GET RUN-RANGE TEST
    //----------------------------------------------------
    
    //Get run range by name, test "all" run range	
	RunRange *rrange = prov->GetRunRange(CCDB_ALL_RUNRANGE_NAME);
	REQUIRE(rrange!=NULL);
	
	//Get run range by min and max run values
	rrange = prov->GetRunRange(0, 2000);
	REQUIRE(rrange!=NULL);	
}
#endif //ifdef CCDB_MYSQL
