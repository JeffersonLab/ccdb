#pragma warning(disable:4800)
#include "Tests/tests_macros.h"
#include "CCDB/Console.h"
#include "CCDB/Helpers/StringUtils.h"
#include "CCDB/Providers/MySQLDataProvider.h"
#include "CCDB/Model/Directory.h"
#include "CCDB/Helpers/WorkUtils.h"
#include "CCDB/Helpers/StopWatch.h"
#include "CCDB/Model/Variation.h"

using namespace std;
using namespace ccdb;

/********************************************************************* ** 
 * @brief Test of directories work
 *
 * @return true if test passed
 */
bool test_DMySQLDataProvider_RunRangesVariations()
{
	TESTS_INIT(" - - -   DMySQLDataProvider   T Y P E   T A B L E S   - - - ")
	DMySQLDataProvider *prov = new DMySQLDataProvider();
	if(!prov->Connect(TESTS_CONENCTION_STRING)) return false;
	
	TITLE("Get default variation");
	DVariation *variation = prov->GetVariation("default");
	TEST(variation!=NULL);
}