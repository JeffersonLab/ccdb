#pragma warning(disable:4800)
#include "Tests/tests_macros.h"
#include "DConsole.h"
#include "DStringUtils.h"
#include "Providers/DMySQLDataProvider.h"
#include "Model/DDirectory.h"
#include "DWorkUtils.h"
#include "DStopWatch.h"
#include "Model/DVariation.h"
#include "UserAPI/DMySQLCallibration.h"

using namespace std;
using namespace ccdb;

//Next functions is for data printing
void test_UserAPI_PrintData(const vector<vector<string> > & data);
void test_UserAPI_PrintData(const vector<vector<double> > & data);
void test_UserAPI_PrintData(const vector<map<string,double> > & data);
void test_UserAPI_PrintData(const vector<int> & data);
void test_UserAPI_PrintData(const map<string,int> & data);

/** ********************************************************************* 
 * @brief Test of CCDB USER API work
 *
 * @return true if test passed
 */
bool test_UserAPI()
{
	bool result;
	TESTS_INIT(" - - -   U S E R   A P I   - - - ")
	DDataProvider *prov = new DMySQLDataProvider();
	if(!prov->Connect(gConnectionString)) return false;

	//U S I N G   U S E R   A P I   D I R E C T L Y
	//----------------------------------------------------
	gConsole.WriteLine(DConsole::cBrightWhite, "\n[ Creating DMySQLCalibration directly ]");

    DMySQLCalibration *calib = new DMySQLCalibration(100);
    result = false;
    try
    {
        result = calib->Connect(gConnectionString);
    }
    catch (std::exception &e)
    {
    	gConsole.WriteLine("Exception was caught %s", e.what());
    }
    TITLE("DMySQLCalibration connected");  TEST(result);

    //get data as table of strings
    //----------------------------------------------------
    vector<vector<string> > tabledValues;
    try
    {
        result = calib->GetCalib(tabledValues, "/test/test_vars/test_table");
    }
    catch (exception &e)
    {
    	gConsole.WriteLine("Exception was caught %s", e.what());
    }
    
    TITLE("Data read");          TEST(tabledValues.size()>0);
    TITLE("Test rows exists");   TEST(tabledValues.size()==2);	
    TITLE("Test cells exists");  TEST(tabledValues[0].size()==3);

    int rowsNum = tabledValues.size();
    int columnsNum = tabledValues[0].size(); //rawTableValues[0] - size was checked in GetCalib
       
    //print values
    for (int rowIter = 0; rowIter < rowsNum; rowIter++)
    {   
        for (int columnsIter = 0; columnsIter < columnsNum; columnsIter++)
        {
            gConsole.Write("| %-8s ", tabledValues[rowIter][columnsIter].c_str());
        }
        gConsole.WriteLine("|");
    }



    /*

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
	TITLE("Create assignment from previus one"); TEST(result);	

	//test what we will get
	result = prov->GetAssignments(assignments, "/test/test_vars/test_table", 100);
	TITLE("Assignments were selected ");       TEST(result);	
	TITLE("Number of assignments increased");  TEST(assignments.size()==(selectedAssignments+1));
	TITLE("New Id is set");                    TEST(lastId!= assignment->GetId());
	TITLE("New data vault Id is set");         TEST(lastDataVaultId!= assignment->GetDataVaultId());
	TITLE("Directory test");                   TEST(assignment->GetTypeTable()->GetColumns().size());
	
	//Lets print table
	vector<vector<string> > tabeled_values = assignment->GetData();
	TITLE("Test rows exists");       TEST(tabeled_values.size()>0);	
	TITLE("Test cells exists");       TEST(tabeled_values[0].size()>0);	
	TITLE("Decode blob");       TEST(DAssignment::DecodeBlobSeparator("30e-2") == "30e-2");	
	
	return true;*/
}

//______________________________________________________________________________
void test_UserAPI_PrintData(const vector<vector<string> > & data)
{
    int rowsNum = data.size();
    int columnsNum = data[0].size(); //rawTableValues[0] - size was checked in GetCalib

    //print values
    for (int rowIter = 0; rowIter < rowsNum; rowIter++)
    {   
        for (int columnsIter = 0; columnsIter < columnsNum; columnsIter++)
        {
            gConsole.Write("|  %-9s ", data[rowIter][columnsIter].c_str());
        }
        gConsole.WriteLine("|");
    }
}

//______________________________________________________________________________
void test_UserAPI_PrintData(const vector<vector<double> > & data)
{
    int rowsNum = data.size();
    int columnsNum = data[0].size(); //rawTableValues[0] - size was checked in GetCalib

    //print values
    for (int rowIter = 0; rowIter < rowsNum; rowIter++)
    {   
        for (int columnsIter = 0; columnsIter < columnsNum; columnsIter++)
        {
            gConsole.Write("| %-9s ", DStringUtils::Format("%.6d", data[rowIter][columnsIter]).c_str());
        }
        gConsole.WriteLine("|");
    }
}

//______________________________________________________________________________
void test_UserAPI_PrintData(const vector<map<string,double> > & data)
{
    int rowsNum = data.size();
    int columnsNum = data[0].size(); //rawTableValues[0] - size was checked in GetCalib

    //print values
    for (int rowIter = 0; rowIter < rowsNum; rowIter++)
    {   
        map<string,double>::const_iterator cell;
        const map<string,double> &row = data[rowIter];

        for (cell = row.begin(); cell!= row.end(); cell++)
        {
            gConsole.Write("| %-20s ", DStringUtils::Format("%s : %.6d", cell->first.c_str(), cell->second).c_str());
        }
        gConsole.WriteLine("|");
    }
}

//______________________________________________________________________________
void test_UserAPI_PrintData(const vector<int> & data)
{
    //print values
    for (int columnsIter = 0; columnsIter < data.size(); columnsIter++)
    {
        gConsole.Write("| %-9s ", DStringUtils::Format("%i", data[columnsIter]).c_str());
    }
    gConsole.WriteLine("|");
}

//______________________________________________________________________________
void test_UserAPI_PrintData(const map<string,int> & data)
{
    map<string,int>::const_iterator cell;
    const map<string,int> &row = data;

    for (cell = row.begin(); cell!= row.end(); cell++)
    {
        gConsole.Write("| %-20s ", DStringUtils::Format("%s : %i", cell->first.c_str(), cell->second).c_str());
    }
    gConsole.WriteLine("|");
}
