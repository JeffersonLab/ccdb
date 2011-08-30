#pragma warning(disable:4800)
#include "Tests/tests_macros.h"
#include "DConsole.h"
#include "DStringUtils.h"
#include "Providers/DMySQLDataProvider.h"
#include "Model/DDirectory.h"
#include "DWorkUtils.h"
#include "DStopWatch.h"
#include "Model/DVariation.h"

using namespace std;
using namespace ccdb;

/********************************************************************* ** 
 * @brief Test of directories work
 *
 * @return true if test passed
 */
bool test_DMySQLDataProvider_RunRanges()
{
	TESTS_INIT(" - - -   DMySQLDataProvider   R U N   R A N G E S   - - - ")
	DMySQLDataProvider *prov = new DMySQLDataProvider();
	if(!prov->Connect(gConnectionString)) return false;
	


    // GET RUN-RANGE TEST
    //----------------------------------------------------
    gConsole.WriteLine(DConsole::cBrightWhite, "\n[ Get run-range testing ]");
  
    //Get run range by name, test "all" run range	
	DRunRange *rrange = prov->GetRunRange(CCDB_ALL_RUNRANGE_NAME);
	TITLE("Get default runrange by name"); TEST(rrange!=NULL);
	
	//Get run range by min and max run values
	rrange = prov->GetRunRange(0, 2000);
	TITLE("Get runrange by range"); TEST(rrange!=NULL);



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

    TITLE("Get not existant runrange by range"); TEST(rrange==NULL);



    // GET OR CREATE RUNRANGE
    //----------------------------------------------------

    //Get or create run-range is the main function to get RunRange without name
    // 0-2001 should be absent or deleted so this function will create run-range
    rrange = prov->GetOrCreateRunRange(0, 2001); 
    TITLE("Get or create run range"); TEST(rrange!=NULL);
    TITLE("Check created run has valid Id"); TEST(rrange->GetId()!=0);

    //this time the run range should be just loaded
    rrange = prov->GetOrCreateRunRange(0, 2001); 
    TITLE("Get or create run range 2"); TEST(rrange!=NULL);



    // DELETE RUN-RANGE TEST
    //----------------------------------------------------
    gConsole.WriteLine(DConsole::cBrightWhite, "\n[ Delete run-range testing ]");

    bool result = prov->DeleteRunRange(rrange);
    TITLE("Delete run range"); TEST(result)
	
	return true;
	
}