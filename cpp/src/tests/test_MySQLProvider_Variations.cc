#pragma warning(disable:4800)
#ifdef CCDB_MYSQL
#include "tests/catch.hpp"
#include "tests/tests.h"

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
	prov->Connect(get_test_mysql_connection());

	//lets try to get default variation
	Variation *variation = prov->GetVariation("subtest");
	REQUIRE(variation!=NULL);
    REQUIRE(variation->GetName()=="subtest");
    REQUIRE(variation->GetComment().length()>0);
    REQUIRE(variation->GetParentDbId()==3);
    REQUIRE(variation->GetParent()!=NULL);
    
    //switch to parent
    variation = variation->GetParent();
    REQUIRE(variation->GetName()=="test");
    REQUIRE(variation->GetParentDbId()==1);
    REQUIRE(variation->GetParent()!=NULL);

    //switch to parent
    variation = variation->GetParent();
    REQUIRE(variation->GetName()=="default");
    REQUIRE(variation->GetParentDbId()==0);
    REQUIRE(variation->GetParent()==NULL);

    //lets try to get default variation
    variation = prov->GetVariation("default");
    REQUIRE(variation!=NULL);
}
#endif //ifdef CCDB_MYSQL
