#pragma warning(disable:4800)
#ifdef CCDB_MYSQL
#include "Tests/catch.hpp"
#include "Tests/tests.h"

#include "CCDB/Providers/MySQLDataProvider.h"
#include "CCDB/Model/Directory.h"
#include "CCDB/Model/ConstantsTypeColumn.h"
#include "CCDB/Model/ConstantsTypeTable.h"

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
	if(!prov->Connect(TESTS_CONENCTION_STRING)) return;

    bool result;
	
    //TYPE TABLE BASICS
    //======================================================
    //basic get type table functional

    //get type table from DB
	ConstantsTypeTable *table = prov->GetConstantsTypeTable("/test/test_vars/test_table", true);
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
	
	//get all tables from the directory.
    vector<ConstantsTypeTable *> tables;
    result = prov->GetConstantsTypeTables(tables, "/test/test_vars", false); //we dont need to load colums for each table, so we place last argument "false"
	
    //test we've got
	REQUIRE(result);
	REQUIRE(tables.size()>0);

	//second implementation of getting type tables from the directory	
	tables = prov->GetConstantsTypeTables("/test/test_vars", false);

	REQUIRE(tables.size());


    //SEARCH TYPE TABLES
    //======================================================
    //basic get type table functional

	
    //search tables are good too
    //now lets get all tables from the directory.
	result = prov->SearchConstantsTypeTables(tables, "t??t_tab*");

	REQUIRE(result);
	REQUIRE(tables.size()>0);

    //Search table in the specified path
    tables = prov->SearchConstantsTypeTables("*", "/test/test_vars",true);
    REQUIRE(tables.size()>0);

	delete prov;//with all objects...
}
#endif //ifdef CCDB_MYSQL
