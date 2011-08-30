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
bool test_DMySQLDataProvider_Assignments()
{
	bool result;
	TESTS_INIT(" - - -   DMySQLDataProvider   A S S I G N M E N T S   - - - ")
	DDataProvider *prov = new DMySQLDataProvider();
	if(!prov->Connect(gConnectionString)) return false;

	//GET ASSIGNMENTS TESTS
	//----------------------------------------------------
	gConsole.WriteLine(DConsole::cBrightWhite, "\n[ Get Assignment testing ]");

	//lets start with simple cases. 
	//Get FULL assignment by table and name
	
	DAssignment * assignment = prov->GetAssignmentFull(100,"/test/test_vars/test_table");
	
	TITLE("Get Assignment");   TEST(assignment!=NULL);

	//Check that everything is loaded
	TITLE("Have variation");  TEST(assignment->GetVariation() != NULL);
	TITLE("Test Run Range");  TEST(assignment->GetRunRange()  != NULL);
	TITLE("Test type table"); TEST(assignment->GetTypeTable() != NULL);	
	TITLE("Test columns ");   TEST(assignment->GetTypeTable()->GetColumns().size()>0);
	
	//print to gConsole data of the assignment
	PrintAssignmentVertical(gConsole, assignment);
	
	//Ok! Lets get all assigments for current types table
	
	vector<DAssignment *> assignments;
	result = prov->GetAssignments(assignments, "/test/test_vars/test_table", 100);
	
	TITLE("Assignments were selected with no errors"); TEST(result);	
	TITLE("One or more assignments were selected");    TEST(assignments.size()>0);
	
	//save number of asignments
	int selectedAssignments = assignments.size();
	dbkey_t lastId = assignment->GetId();
	dbkey_t lastDataVaultId = assignment->GetDataVaultId();
	gConsole.WriteLine("Selected %i assignments; Last id %i; Last dataVault id %i",selectedAssignments, lastId, lastDataVaultId);
	
	//Lets try create assignments testing from copy assignment
	gConsole.WriteLine(DConsole::cBrightWhite, "\n[ Copy Assignment testing ]");
	
	//simple copy
	result = prov->CreateAssignment(assignment);
	TITLE("Create assignment from previous one"); TEST(result);	

	//test what we will get
	result = prov->GetAssignments(assignments, "/test/test_vars/test_table", 100);
	TITLE("Assignments were selected ");       TEST(result);	
	TITLE("Number of assignments increased");  TEST(assignments.size()==(selectedAssignments+1));
	TITLE("New Id is set");                    TEST(lastId!= assignment->GetId());
	TITLE("New data vault Id is set");         TEST(lastDataVaultId!= assignment->GetDataVaultId());
	TITLE("Directory test");                   TEST(assignment->GetTypeTable()->GetColumns().size());
	
	//Lets print table
	vector<vector<string> > tabeled_values = assignment->GetData();
	TITLE("Test rows exists");   TEST(tabeled_values.size()>0);	
	TITLE("Test cells exists");  TEST(tabeled_values[0].size()>0);	
	TITLE("Decode blob");        TEST(DAssignment::DecodeBlobSeparator("30e-2") == "30e-2");	
	
	return true;
}