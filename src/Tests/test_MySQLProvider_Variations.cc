#pragma warning(disable:4800)
#include "Tests/catch.h"
#include "Tests/tests.h"

#include "CCDB/Providers/MySQLDataProvider.h"
#include "CCDB/Model/Variation.h"

using namespace std;
using namespace ccdb;

/********************************************************************* ** 
 * @brief Test of directories work
 *
 * @return true if test passed
 */
TEST_CASE("CCDB/MySQLDataProvider/Variations","Variations/tests")
{	
	DataProvider *prov = new MySQLDataProvider();
	if(!prov->Connect(TESTS_CONENCTION_STRING)) return;

	//lets try to get default variation
	Variation *variation = prov->GetVariation("default");
	REQUIRE(variation!=NULL);
	
	//lets get all variations for table 
	vector<Variation *> variations;
	bool result = prov->GetVariations(variations, "/test/test_vars/test_table");
	
	REQUIRE(result);
	REQUIRE(variations.size()>0);
}

