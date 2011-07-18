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
	
	//Get run range by name, test "all" run range	
	DRunRange *rrange = prov->GetRunRange(CCDB_ALL_RUNRANGE_NAME);
	TITLE("Get default runrange by name"); TEST(rrange!=NULL);
	
	//Get run range by range
	rrange = prov->GetRunRange(0, 2000);
	TITLE("Get runrange by range");        TEST(rrange!=NULL);
	delete prov;
	
	return true;
	
}