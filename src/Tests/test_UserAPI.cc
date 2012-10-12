#pragma warning(disable:4800)
#include "Tests/catch.h"
#include "Tests/tests.h"

#include "CCDB/Console.h"
#include "CCDB/MySQLCalibration.h"
#include "CCDB/SQLiteCalibration.h"
#include "CCDB/Providers/MySQLDataProvider.h"
#include "CCDB/Providers/SQLiteDataProvider.h"
#include "CCDB/Model/Directory.h"
#include "CCDB/Model/Variation.h"
#include "CCDB/Helpers/StringUtils.h"
#include "CCDB/Helpers/WorkUtils.h"
#include "CCDB/Helpers/Stopwatch.h"
#include "CCDB/Helpers/PathUtils.h"
#include "CCDB/Log.h"
#include "CCDB/CalibrationGenerator.h"

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
TEST_CASE("CCDB/UserAPI/MySQL","tests")
{
	bool result;
	
	DataProvider *prov = new MySQLDataProvider();
	if(!prov->Connect(TESTS_CONENCTION_STRING)) return;

	//U S I N G   U S E R   A P I   D I R E C T L Y
	//----------------------------------------------------

    MySQLCalibration *calib = new MySQLCalibration(100);
    result = false;

    REQUIRE_NOTHROW(result = calib->Connect(TESTS_CONENCTION_STRING));
    REQUIRE(result);
    REQUIRE(calib->GetConnectionString() == TESTS_CONENCTION_STRING);
    
    //get data as table of strings
    //----------------------------------------------------
    vector<vector<string> > tabledValues;
    REQUIRE_NOTHROW(result = calib->GetCalib(tabledValues, "/test/test_vars/test_table"));
    REQUIRE(tabledValues.size()>0);
    REQUIRE(tabledValues.size()==2);
    REQUIRE(tabledValues[0].size()==3);

    
    //test of getting data without / in the beginning
    //----------------------------------------------------
    tabledValues.clear();
    REQUIRE_NOTHROW(result = calib->GetCalib(tabledValues, "test/test_vars/test_table"));
    REQUIRE(result);
    REQUIRE(tabledValues.size()>0);

    //test of getting data as map
    //----------------------------------------------------
    map<string, string> mappedValues;
    REQUIRE_NOTHROW(result = calib->GetCalib(mappedValues, "test/test_vars/test_table"));
    REQUIRE(result);
    REQUIRE(mappedValues.size()>0);

    //test of getting data without / in the beginning
    //----------------------------------------------------
    vector<map<string, string> > vectorOfMapsdValues;
    REQUIRE_NOTHROW(result = calib->GetCalib(vectorOfMapsdValues, "test/test_vars/test_table"));
    REQUIRE(result);
    REQUIRE(vectorOfMapsdValues.size()>0);

    vectorOfMapsdValues.clear();
    REQUIRE_NOTHROW(result = calib->GetCalib(vectorOfMapsdValues, "test/test_vars/test_table"));
    REQUIRE(result);
    REQUIRE(vectorOfMapsdValues.size()>0);

    

    //test of get all namepaths
    //----------------------------------------------------
    vector<string> paths;
    REQUIRE_NOTHROW(calib->GetListOfNamepaths(paths));
    REQUIRE(paths.size()>0);
}

/** ********************************************************************* 
 * @brief Test of CCDB USER API work
 *
 * @return true if test passed
 */
TEST_CASE("CCDB/UserAPI/SQLite","tests")
{
	bool result;
	
	DataProvider *prov = new SQLiteDataProvider();
	if(!prov->Connect(TESTS_SQLITE_STRING)) return;

	//U S I N G   U S E R   A P I   D I R E C T L Y
	//----------------------------------------------------

    SQLiteCalibration *calib = new SQLiteCalibration(100);
    result = false;

    REQUIRE_NOTHROW(result = calib->Connect(TESTS_SQLITE_STRING));
    REQUIRE(result);
    REQUIRE(calib->GetConnectionString() == TESTS_SQLITE_STRING);
    
    //get data as table of strings
    //----------------------------------------------------
    vector<vector<string> > tabledValues;
    REQUIRE_NOTHROW(result = calib->GetCalib(tabledValues, "/test/test_vars/test_table"));
    REQUIRE(tabledValues.size()>0);
    REQUIRE(tabledValues.size()==2);
    REQUIRE(tabledValues[0].size()==3);

    
    //test of getting data without / in the beginning
    //----------------------------------------------------
    tabledValues.clear();
    REQUIRE_NOTHROW(result = calib->GetCalib(tabledValues, "test/test_vars/test_table"));
    REQUIRE(result);
    REQUIRE(tabledValues.size()>0);

    //test of getting data as map
    //----------------------------------------------------
    map<string, string> mappedValues;
    REQUIRE_NOTHROW(result = calib->GetCalib(mappedValues, "test/test_vars/test_table"));
    REQUIRE(result);
    REQUIRE(mappedValues.size()>0);

    //test of getting data without / in the beginning
    //----------------------------------------------------
    vector<map<string, string> > vectorOfMapsdValues;
    REQUIRE_NOTHROW(result = calib->GetCalib(vectorOfMapsdValues, "test/test_vars/test_table"));
    REQUIRE(result);
    REQUIRE(vectorOfMapsdValues.size()>0);

    vectorOfMapsdValues.clear();
    REQUIRE_NOTHROW(result = calib->GetCalib(vectorOfMapsdValues, "test/test_vars/test_table"));
    REQUIRE(result);
    REQUIRE(vectorOfMapsdValues.size()>0);

    //test of get all namepaths
    //----------------------------------------------------
    vector<string> paths;
    REQUIRE_NOTHROW(calib->GetListOfNamepaths(paths));
    REQUIRE(paths.size()>0);
}

TEST_CASE("CCDB/UserAPI/StressTests","Try faulty operations tests")
{
    //The next tests will give some errors
    //So lets suppress error logging to stdout

    Log::SetErrorLevel(0); //suppress errors printing
    
    //Now lets check if user forget to connect...
    Calibration *calib = new MySQLCalibration(100);

    //We are not connected... So lets check it! 
    REQUIRE_FALSE(calib->IsConnected());

    //Ok.. next we will try to get data from not opened calibrations
    // This should result some logic error. 
     vector<vector<string> > tabledValues;
    REQUIRE_THROWS(calib->GetCalib(tabledValues, "test/test_vars/test_table"));

    
    //Now we will connect to improper source...
    REQUIRE_FALSE(calib->Connect("ha ha ha"));
    REQUIRE_FALSE(calib->Connect("mysql://muuuu ha ha ha"));
    
    //Ok, lets connect at last...
    bool result;
    REQUIRE_NOTHROW(result = calib->Connect(TESTS_CONENCTION_STRING));
    REQUIRE(result);

    //And then lets connect once more to the same string...
    REQUIRE_NOTHROW(result = calib->Connect(TESTS_CONENCTION_STRING));
    REQUIRE(result);

    //And then lets connect once more to another string...
    REQUIRE_THROWS(result = calib->Connect("mysql://muuuu ha ha ha"));

    //Reenable logging
    Log::SetErrorLevel(3); //restore logging
}

TEST_CASE("CCDB/UserAPI/CalibrationGenerator","Use universal generator to get calibrations")
{
	bool result;
	CalibrationGenerator* gen = new CalibrationGenerator();
	Calibration* sqliteCalib = gen->MakeCalibration(TESTS_SQLITE_STRING, 100, "default");
	REQUIRE(static_cast<SQLiteCalibration*>(sqliteCalib)!=NULL);
	REQUIRE(sqliteCalib->IsConnected());
	vector<vector<string> > tabledValues;
	REQUIRE_NOTHROW(result = sqliteCalib->GetCalib(tabledValues, "/test/test_vars/test_table"));
	REQUIRE(result);
	REQUIRE(tabledValues.size()>0);
	REQUIRE(tabledValues.size()==2);
	REQUIRE(tabledValues[0].size()==3);

	Calibration* sqliteCalib2 = gen->MakeCalibration(TESTS_SQLITE_STRING, 100, "default");
	REQUIRE(sqliteCalib == sqliteCalib2);

	Calibration* mysqlCalib  = gen->MakeCalibration(TESTS_CONENCTION_STRING, 100, "default");
	REQUIRE(static_cast<MySQLCalibration*>(mysqlCalib)!=NULL);
	REQUIRE(sqliteCalib->IsConnected());
	REQUIRE_NOTHROW(result = sqliteCalib->GetCalib(tabledValues, "/test/test_vars/test_table"));
	REQUIRE(result);
	REQUIRE(tabledValues.size()>0);
	REQUIRE(tabledValues.size()==2);
	REQUIRE(tabledValues[0].size()==3);

	//Check openable tests
	REQUIRE(CalibrationGenerator::CheckOpenable(TESTS_CONENCTION_STRING));
	REQUIRE(CalibrationGenerator::CheckOpenable(TESTS_SQLITE_STRING));
	REQUIRE_FALSE(CalibrationGenerator::CheckOpenable("abra_kadabra://protocol"));

	//=== Default time ===
	SECTION("Default Time SQLite", "Test that test vars are opened with default date")
	{		
		ContextParseResult res = PathUtils::ParseContext("variation=default calibtime=2012-08");
		Calibration* sqliteCalib = gen->MakeCalibration(TESTS_SQLITE_STRING, 100, res.Variation, res.ConstantsTime);
		REQUIRE_NOTHROW(result = sqliteCalib->GetCalib(tabledValues, "/test/test_vars/test_table"));
		REQUIRE(result);
		REQUIRE(tabledValues.size()>0);
		REQUIRE(tabledValues.size()==2);
		REQUIRE(tabledValues[0].size()==3);
		REQUIRE(tabledValues[0][0]=="1.11");
	}

	SECTION("Default Time MySQL", "Test that test vars are opened with default date")
	{		
		ContextParseResult res = PathUtils::ParseContext("variation=default calibtime=2012-08");
		Calibration* sqliteCalib = gen->MakeCalibration(TESTS_CONENCTION_STRING, 100, res.Variation, res.ConstantsTime);
		REQUIRE_NOTHROW(result = sqliteCalib->GetCalib(tabledValues, "/test/test_vars/test_table"));
		REQUIRE(result);
		REQUIRE(tabledValues.size()>0);
		REQUIRE(tabledValues.size()==2);
		REQUIRE(tabledValues[0].size()==3);
		REQUIRE(tabledValues[0][0]=="1.11");
	}
}

/*
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
            gConsole.Write("| %-9s ", StringUtils::Format("%.6d", data[rowIter][columnsIter]).c_str());
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
            gConsole.Write("| %-20s ", StringUtils::Format("%s : %.6d", cell->first.c_str(), cell->second).c_str());
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
        gConsole.Write("| %-9s ", StringUtils::Format("%i", data[columnsIter]).c_str());
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
        gConsole.Write("| %-20s ", StringUtils::Format("%s : %i", cell->first.c_str(), cell->second).c_str());
    }
    gConsole.WriteLine("|");
}
*/