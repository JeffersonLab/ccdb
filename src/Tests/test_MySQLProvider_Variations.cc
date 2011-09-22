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
bool test_DMySQLDataProvider_Variations()
{
	TESTS_INIT(" - - -   DMySQLDataProvider   V A R I A T I O N S   - - - ")
	DDataProvider *prov = new DMySQLDataProvider();
	if(!prov->Connect(gConnectionString)) return false;
	
	//lets try to get default variation
	DVariation *variation = prov->GetVariation("default");
	TITLE("Get default variation"); TEST(variation!=NULL);
	
	//lets get all variations for table 
	vector<DVariation *> variations;
	bool result = prov->GetVariations(variations, "/test/test_vars/test_table");
	
	TITLE("Get all variations for table");	TEST(result);
	TITLE("Test variations selected");      TEST(variations.size()>0);
	
	return true;
}

