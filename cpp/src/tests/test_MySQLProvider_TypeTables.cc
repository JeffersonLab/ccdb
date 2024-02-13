#pragma warning(disable:4800)
#ifdef CCDB_MYSQL
#include "tests/catch.hpp"
#include "tests/tests.h"

#include "CCDB/Providers/MySQLDataProvider.h"
#include "CCDB/Model/Directory.h"
#include "CCDB/Model/ConstantsTypeColumn.h"
#include "CCDB/Model/ConstantsTypeTable.h"
#include "CCDB/Providers/DataProvider.h"

using namespace std;
using namespace ccdb;

/********************************************************************* ** 
 * @brief Test of directories work
 *
 * @return true if test passed
 */
TEST_CASE("CCDB/MySQLDataProvider/TypeTables","TypeTables tests")
{
	
	MySQLDataProvider *prov = new MySQLDataProvider();
	prov->Connect(get_test_mysql_connection());

    bool result;
	
    //TYPE TABLE BASICS
    //======================================================
    //basic get type table functional

    //get type table from DB
	ConstantsTypeTable *table = static_cast<ccdb::DataProvider*>(prov)->GetConstantsTypeTable("/test/test_vars/test_table", true);
    REQUIRE(table!=NULL);
	REQUIRE(table->GetColumns().size() == 3);
	REQUIRE(table->GetColumnsCount() == 3);
	REQUIRE(table->GetName() == "test_table");
	REQUIRE(table->GetFullPath() == "/test/test_vars/test_table");
	REQUIRE(table->GetDirectory() != NULL);
	REQUIRE(table->GetDirectory()->GetName() == "test_vars");
	REQUIRE(table->GetColumns()[0]->GetName() == string("x"));

	//print type table
	delete table; //cleanup
	delete prov;//with all objects...
}
#endif //ifdef CCDB_MYSQL
