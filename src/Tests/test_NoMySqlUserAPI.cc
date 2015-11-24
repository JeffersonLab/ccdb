#pragma warning(disable:4800)
#include "Tests/catch.hpp"
#include "Tests/tests.h"

#include "CCDB/Console.h"
#include "CCDB/SQLiteCalibration.h"
#include "CCDB/Providers/SQLiteDataProvider.h"
#include "CCDB/Helpers/PathUtils.h"
#include "CCDB/CalibrationGenerator.h"


using namespace std;
using namespace ccdb;


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
	
	//ask for vector
	vector<vector<int> > tabledDoubleValues;
	REQUIRE_NOTHROW(result = sqliteCalib->GetCalib(tabledDoubleValues, "/test/test_vars/test_table2::test"));
	REQUIRE(result);
	REQUIRE(tabledDoubleValues.size()>0);
	REQUIRE(tabledDoubleValues.size()==1);
	REQUIRE(tabledDoubleValues[0].size()==3);
	REQUIRE(tabledDoubleValues[0][0]==10);
	REQUIRE(tabledDoubleValues[0][1]==20);
	REQUIRE(tabledDoubleValues[0][2]==30);
	
	vector<int> lineOfIntValues;
	REQUIRE_NOTHROW(result = sqliteCalib->GetCalib(lineOfIntValues, "/test/test_vars/test_table2:0:test:2012-09-30 23-48-42"));
	REQUIRE(result);
	REQUIRE(lineOfIntValues.size()==3);
	REQUIRE(lineOfIntValues[0]==10);
	REQUIRE(lineOfIntValues[1]==20);
	REQUIRE(lineOfIntValues[2]==30);

	//Get Type table through the Provider()
	ConstantsTypeTable* table = sqliteCalib->GetProvider()->GetConstantsTypeTable("/test/test_vars/test_table2", true);
	REQUIRE(table->GetColumns()[0]->GetType() == ConstantsTypeColumn::cIntColumn);

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

		//No such calibration exist in mc variation, but constants should fallback to default varitaion
		res = PathUtils::ParseContext("variation=subtest calibtime=2012-11");
		sqliteCalib = gen->MakeCalibration(TESTS_SQLITE_STRING, 100, res.Variation, res.ConstantsTime);
		REQUIRE_NOTHROW(result = sqliteCalib->GetCalib(tabledValues, "/test/test_vars/test_table"));
		REQUIRE(result);
		REQUIRE(tabledValues.size()>0);
		REQUIRE(tabledValues.size()==2);
		REQUIRE(tabledValues[0].size()==3);
		REQUIRE(tabledValues[0][0]=="10");
		
		//No such calibration exist in test variation run 100, but constants should fallback to variation
		res = PathUtils::ParseContext("variation=test");
		sqliteCalib = gen->MakeCalibration(TESTS_SQLITE_STRING, 100, res.Variation);
		REQUIRE_NOTHROW(result = sqliteCalib->GetCalib(tabledValues, "/test/test_vars/test_table"));
		REQUIRE(result);
		REQUIRE(tabledValues.size()>0);
		REQUIRE(tabledValues.size()==2);
		REQUIRE(tabledValues[0].size()==3);
		REQUIRE(tabledValues[0][0]=="2.2");

		//Error regression test for bug with absent column names. Filling map will test the column names are OK
		vector<map<string, string> > tableMapValues;
		REQUIRE_NOTHROW(result = sqliteCalib->GetCalib(tableMapValues, "/test/test_vars/test_table"));
	}

	SECTION("Get Assignment test", "Test all elements of getting data through get assignment")
	{
		Assignment *a;
		REQUIRE_NOTHROW(a = sqliteCalib->GetAssignment("/test/test_vars/test_table2:0:test"));
		REQUIRE(result);
		REQUIRE(a->GetValueType(0) == ConstantsTypeColumn::cIntColumn);
		REQUIRE(a->GetValueType("c3") == ConstantsTypeColumn::cIntColumn);
		REQUIRE(a->GetValue(1) == "20");
		REQUIRE(a->GetValue(0, 1) == "20");
		REQUIRE(a->GetValue("c1") == "10");
		REQUIRE(a->GetValue(0, "c3") == "30");
		REQUIRE(a->GetValueInt(1) == 20);
		REQUIRE(a->GetValueInt(0, 1) == 20);
		REQUIRE(a->GetValueInt("c1") == 10);
		REQUIRE(a->GetValueInt(0, "c3") == 30);
		REQUIRE(a->GetValueDouble(2) > 29);
	}
}
