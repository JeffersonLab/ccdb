#pragma warning(disable:4800)
#ifdef CCDB_MYSQL
#include "Tests/catch.h"
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

    if(rrange)  //oh... It shouldn't be... Maybe it is left because of the last tests... 
    {  
        cout<<"WARNING prov->GetRunRange(0, 2001) found run range (should not be there)"<<endl<<
              "trying to delete rrange and do the test one more time... "<<endl;
        prov->DeleteRunRange(rrange);           //(!) <-- test of this function is further
        rrange = prov->GetRunRange(0, 2001);
    }

    REQUIRE(rrange==NULL);

    // GET OR CREATE RUNRANGE
    //----------------------------------------------------

    //Get or create run-range is the main function to get RunRange without name
    // 0-2001 should be absent or deleted so this function will create run-range
    rrange = prov->GetOrCreateRunRange(0, 2001); 
    REQUIRE(rrange!=NULL);
    REQUIRE(rrange->GetId()!=0);

    //this time the run range should be just loaded
    rrange = prov->GetOrCreateRunRange(0, 2001); 
    REQUIRE(rrange!=NULL);


    // DELETE RUN-RANGE TEST
    //----------------------------------------------------
    bool result = prov->DeleteRunRange(rrange);
    REQUIRE(result)
	
}
#endif //ifdef CCDB_MYSQL