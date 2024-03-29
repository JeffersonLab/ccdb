#pragma warning(disable:4800)
#include "tests/catch.hpp"
#include "tests/tests.h"
#include <memory>

#include "CCDB/MySQLCalibration.h"
#include "CCDB/SQLiteCalibration.h"
#include "CCDB/Providers/MySQLDataProvider.h"
#include "CCDB/Providers/SQLiteDataProvider.h"
#include "CCDB/Model/Directory.h"
#include "CCDB/Model/Variation.h"

#include "CCDB/Helpers/PathUtils.h"
#include "CCDB/CalibrationGenerator.h"
#include "CCDB/Helpers/TimeProvider.h"

using namespace std;
using namespace ccdb;

// Next functions are for data printing
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
    REQUIRE_NOTHROW(prov->Connect(get_test_mysql_connection()));


	//U S I N G   U S E R   A P I   D I R E C T L Y
	//----------------------------------------------------

	auto con_str = get_test_mysql_connection();

    MySQLCalibration *calib = new MySQLCalibration(100);
	REQUIRE_NOTHROW(calib->Connect(con_str));
    REQUIRE(calib->GetConnectionString() == con_str);
    
    //get data as table of strings
    //----------------------------------------------------
    vector<vector<string> > tabledValues;
    REQUIRE_NOTHROW(result = calib->GetCalib(tabledValues, "/test/test_vars/test_table"));
    REQUIRE(tabledValues.size()>0);
    REQUIRE(tabledValues.size()==2);
    REQUIRE(tabledValues[0].size()==3);

    //test of disconnect and reconnect function
    //----------------------------------------------------
    REQUIRE_NOTHROW(calib->Disconnect());
    REQUIRE_NOTHROW(calib->Reconnect());
    
    //test of getting data without / in the beginning
    //----------------------------------------------------
    tabledValues.clear();
    REQUIRE_NOTHROW(result = calib->GetCalib(tabledValues, "test/test_vars/test_table"));
    REQUIRE(result);
    REQUIRE(tabledValues.size()>0);

    //test of getting data as map
    //----------------------------------------------------
    map<string, string> mappedValues;
    REQUIRE_NOTHROW(result = calib->GetCalib(mappedValues, "test/test_vars/test_table2::test"));
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
    
    //Now lets check if user forget to connect...
    Calibration *calib = new MySQLCalibration(100);

    //We are not connected... So lets check it! 
    REQUIRE_FALSE(calib->IsConnected());

    //Ok.. next we will try to get data from not opened calibrations
    // This should result some logic error. 
     vector<vector<string> > tabledValues;
    REQUIRE_THROWS(calib->GetCalib(tabledValues, "test/test_vars/test_table"));

    
    //Now we will connect to improper source...
    REQUIRE_THROWS(calib->Connect("ha ha ha"));
    REQUIRE_THROWS(calib->Connect("mysql://muuuu ha ha ha"));
    
    //Ok, lets connect at last...
    bool result;
    REQUIRE_NOTHROW(result = calib->Connect(get_test_mysql_connection()));
    REQUIRE(result);

    //And then lets connect once more to the same string...
    REQUIRE_NOTHROW(result = calib->Connect(get_test_mysql_connection()));
    REQUIRE(result);

    //And then lets connect once more to another string...
    REQUIRE_THROWS(result = calib->Connect("mysql://muuuu ha ha ha"));
}

TEST_CASE("CCDB/UserAPI/CalibrationGenerator","Use universal generator to get calibrations")
{
	bool result;
	CalibrationGenerator* gen = new CalibrationGenerator();
	Calibration* sqliteCalib = gen->MakeCalibration(get_test_mysql_connection(), 100, "default");
	REQUIRE(static_cast<SQLiteCalibration*>(sqliteCalib) != nullptr);
	REQUIRE(sqliteCalib->IsConnected());
	vector<vector<string> > tabledValues;
	REQUIRE_NOTHROW(result = sqliteCalib->GetCalib(tabledValues, "/test/test_vars/test_table"));
	REQUIRE(result);
	REQUIRE(tabledValues.size()>0);
	REQUIRE(tabledValues.size()==2);
	REQUIRE(tabledValues[0].size()==3);

	Calibration* sqliteCalib2 = gen->MakeCalibration(get_test_mysql_connection(), 100, "default");
	REQUIRE(sqliteCalib == sqliteCalib2);

	Calibration* mysqlCalib  = gen->MakeCalibration(get_test_mysql_connection(), 100, "default");
	REQUIRE(static_cast<MySQLCalibration*>(mysqlCalib)!=NULL);
	REQUIRE(sqliteCalib->IsConnected());
	REQUIRE_NOTHROW(result = sqliteCalib->GetCalib(tabledValues, "/test/test_vars/test_table"));
	REQUIRE(result);
	REQUIRE(tabledValues.size()>0);
	REQUIRE(tabledValues.size()==2);
	REQUIRE(tabledValues[0].size()==3);

	//Check openable tests
	REQUIRE(CalibrationGenerator::CheckOpenable(get_test_mysql_connection()));
	REQUIRE(CalibrationGenerator::CheckOpenable(get_test_sqlite_connection()));
	REQUIRE_FALSE(CalibrationGenerator::CheckOpenable("abra_kadabra://protocol"));

	//=== Default time ===
	SECTION("Default Time SQLite", "Test that test vars are opened with default date")
	{		
		ContextParseResult res = PathUtils::ParseContext("variation=default calibtime=2012-08");
		Calibration* sqliteCalib = gen->MakeCalibration(get_test_sqlite_connection(), 100, res.Variation, res.ConstantsTime);
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
		Calibration* sqliteCalib = gen->MakeCalibration(get_test_mysql_connection(), 100, res.Variation, res.ConstantsTime);
		REQUIRE_NOTHROW(result = sqliteCalib->GetCalib(tabledValues, "/test/test_vars/test_table"));
		REQUIRE(result);
		REQUIRE(tabledValues.size()>0);
		REQUIRE(tabledValues.size()==2);
		REQUIRE(tabledValues[0].size()==3);
		REQUIRE(tabledValues[0][0]=="1.11");
	}
}

TEST_CASE("CCDB/UserAPI/CalibrationGenerator/Timeout","Disconnect database with timeout")
{
    //Set fake time
    TimeProvider::SetTimeUnitTest(true);
    TimeProvider::SetUnitTestTime(100);

    //Get calibration generator
    CalibrationGenerator* gen = new CalibrationGenerator();
    gen->SetMaxInactiveTime(50);  //50 seconds of inactivity

    //Get calibration object
    Calibration* sqliteCalib = gen->MakeCalibration(get_test_mysql_connection(), 100, "default");

    REQUIRE(sqliteCalib->IsConnected());

    //Now update time
    REQUIRE_NOTHROW(gen->UpdateInactivity());
    REQUIRE(sqliteCalib->IsConnected());

    //Update time once more
    TimeProvider::SetUnitTestTime(110);
    REQUIRE_NOTHROW(gen->UpdateInactivity());
    REQUIRE(sqliteCalib->IsConnected());

    //and more... Now the database should be disconnected
    TimeProvider::SetUnitTestTime(251);
    REQUIRE_NOTHROW(gen->UpdateInactivity());
    REQUIRE_FALSE(sqliteCalib->IsConnected());
    
    //Now we download something to check reconnect function
    bool result;
    vector<vector<string> > tabledValues;
    REQUIRE_NOTHROW(result = sqliteCalib->GetCalib(tabledValues, "/test/test_vars/test_table"));
    REQUIRE(result);
    REQUIRE(tabledValues.size()>0);
    REQUIRE(tabledValues.size()==2);
    REQUIRE(tabledValues[0].size()==3);

    //Update time once more. It should be connected 
    TimeProvider::SetUnitTestTime(160);
    REQUIRE_NOTHROW(gen->UpdateInactivity());
    REQUIRE(sqliteCalib->IsConnected());

    //Turn back normal time
    TimeProvider::SetTimeUnitTest(false);
}
