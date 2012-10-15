#pragma warning(disable:4800)
#include "Tests/catch.h"
#include "Tests/tests.h"

#include "CCDB/Console.h"
#include "CCDB/SQLiteCalibration.h"
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


TEST_CASE("CCDB/UserAPI/SQLite_CalibrationGenerator","Use universal generator to get calibrations")
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
}
