#pragma warning(disable:4800)
#ifdef CCDB_MYSQL
#include "Tests/tests.h"
#include "Tests/catch.hpp"

#include "CCDB/Console.h"
#include "CCDB/Helpers/StringUtils.h"
#include "CCDB/Providers/MySQLDataProvider.h"
#include "CCDB/Model/Variation.h"
#include "CCDB/Model/Directory.h"

using namespace std;
using namespace ccdb;

/********************************************************************* ** 
 * @brief Test of directories work
 *
 * @return true if test passed
 */
TEST_CASE("CCDB/MySQLDataProvider/Assignments","Assignments tests")
{
	bool result;
	
	DataProvider *prov = new MySQLDataProvider();
	if(!prov->Connect(TESTS_CONENCTION_STRING)) return;

	//GET ASSIGNMENTS TESTS
	//----------------------------------------------------
	//lets start with simple cases. 
	//Get FULL assignment by table and name
	
	Assignment * assignment = prov->GetAssignmentFull(100,"/test/test_vars/test_table");
	
	REQUIRE(assignment!=NULL);

	//Check that everything is loaded
	REQUIRE(assignment->GetVariation() != NULL);
	REQUIRE(assignment->GetRunRange()  != NULL);
	REQUIRE(assignment->GetTypeTable() != NULL);	
	REQUIRE(assignment->GetTypeTable()->GetColumns().size()>0);
	vector<vector<string> > tabeled_values = assignment->GetData();
	REQUIRE(tabeled_values.size()==2);	
	REQUIRE(tabeled_values[0].size()==3);	
	REQUIRE(tabeled_values[0][0] == "2.2");
	REQUIRE(tabeled_values[0][1] == "2.3");
	REQUIRE(tabeled_values[0][2] == "2.4");
	REQUIRE(tabeled_values[1][0] == "2.5");
	REQUIRE(tabeled_values[1][1] == "2.6");
	REQUIRE(tabeled_values[1][2] == "2.7");
	
	//Ok! Lets get all assigments for current types table
	vector<Assignment *> assignments;
	result = prov->GetAssignments(assignments, "/test/test_vars/test_table", 100);
	
	REQUIRE(result);	
	REQUIRE(assignments.size()>0);
	
	//save number of asignments
	int selectedAssignments = assignments.size();
	dbkey_t lastId = assignment->GetId();
	dbkey_t lastDataVaultId = assignment->GetDataVaultId();

    //Variations work test
    delete assignment;

    //variation hierarchy is
    // default -> test -> subtest
    // There are /test/test_vars/test_table for variation subtest. 
    // But  /test/test_vars/test_table2 has only default variation

    assignment = prov->GetAssignmentShort(100,"/test/test_vars/test_table2", "subtest");



}
#endif //ifdef CCDB_MYSQL
