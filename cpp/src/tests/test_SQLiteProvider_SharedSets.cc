#pragma warning(disable:4800)
#include "tests/tests.h"
#include "tests/catch.hpp"

#include <stdlib.h>

#include "CCDB/Calibration.h"
#include "CCDB/CalibrationGenerator.h"
#include "CCDB/Providers/SQLiteDataProvider.h"
#include "CCDB/Model/Assignment.h"
#include "CCDB/Model/Variation.h"

using namespace std;
using namespace ccdb;


/** *********************************************************************
 * @brief Schema 6 cases of the web GUI fixture read through the API that 2.4 users call
 *
 * Schema 6 lets several assignments share one constant set: assignments.constantSetId of two rows may point
 * to the same constantSets row. The C++ library has no schema version check and joins assignments to their
 * set by id, so it must read such a database exactly as before. This test proves it on the GUI fixture that
 * scripts/webgui/make_fixture.py builds (function add_schema6_cases). The assignment ids, rows and texts of
 * /schema6/shared and /schema6/numeric are the literals listed in that function's docstring, which the Python
 * fixture test asserts too, so both languages are checked against one source. The column names and the
 * deprecated table and variation checks read values from the code of the same function.
 *
 * The fixture is a built SQLite file, not part of the repository: the test reads it through
 * CCDB_TEST_FIXTURE_CONNECTION (sqlite:///path/to/ccdb_fixture.sqlite). Without the variable the test warns
 * and passes, so a developer can run the suite without the fixture; under CI (variable CI set) it fails,
 * so a CI job that forgot to build the fixture cannot pass unnoticed.
 */
TEST_CASE("CCDB/SQLiteDataProvider/SharedSets", "[fixture] Schema 6 fixture: shared constant sets")
{
	const char* fixtureConnection = getenv("CCDB_TEST_FIXTURE_CONNECTION");
	if(!fixtureConnection) {
		if(getenv("CI")) {
			FAIL("CCDB_TEST_FIXTURE_CONNECTION is not set. Under CI it is required: build the fixture with "
			     "scripts/webgui/make_fixture.py --out <file> and export CCDB_TEST_FIXTURE_CONNECTION=sqlite:///<file>");
		}
		WARN("CCDB_TEST_FIXTURE_CONNECTION is not set: the schema 6 fixture test is skipped");
		SUCCEED();
		return;
	}
	const string connectionString(fixtureConnection);

	// Runs inside the two run ranges of the fixture: 0-999 and 1000-1999
	const int firstRangeRun = 500;
	const int secondRangeRun = 1500;

	CalibrationGenerator* gen = new CalibrationGenerator();
	Calibration* firstCalib = gen->MakeCalibration(connectionString, firstRangeRun, "default");
	Calibration* secondCalib = gen->MakeCalibration(connectionString, secondRangeRun, "default");
	REQUIRE(firstCalib->IsConnected());
	REQUIRE(secondCalib->IsConnected());

	//TWO ASSIGNMENTS, ONE CONSTANT SET
	//----------------------------------------------------
	// Assignments 3614 (runs 0-999) and 3615 (runs 1000-1999) of /schema6/shared both point to constant set 3614
	SECTION("Two assignments of one constant set", "Each run range gives the shared rows and its own assignment")
	{
		const vector<vector<string> > expectedRows = {
			{"0", "1.25", "100.5"},
			{"1", "1.5",  "101.0"},
			{"2", "0.75", "99.5"}
		};

		vector<vector<string> > firstRows;
		vector<vector<string> > secondRows;
		REQUIRE(firstCalib->GetCalib(firstRows, "/schema6/shared"));
		REQUIRE(secondCalib->GetCalib(secondRows, "/schema6/shared"));
		REQUIRE(firstRows == expectedRows);
		REQUIRE(secondRows == expectedRows);

		// The run can also be given in the request itself. Both run ranges carry the same rows, so only the
		// assignment id shows that the run of the request, not the calibration's run 500, was used
		vector<vector<string> > requestedRows;
		REQUIRE(firstCalib->GetCalib(requestedRows, "/schema6/shared:1500"));
		REQUIRE(requestedRows == expectedRows);
		Assignment* requestedAssignment = firstCalib->GetAssignment("/schema6/shared:1500");
		REQUIRE(requestedAssignment != NULL);
		REQUIRE(requestedAssignment->GetId() == 3615);
		if(!firstCalib->IsCacheEnabled()) delete requestedAssignment;    // otherwise owned by the calibration cache

		// Column names come from the columns table, which schema 6 extends with units
		vector<map<string, double> > firstMaps;
		REQUIRE(firstCalib->GetCalib(firstMaps, "/schema6/shared"));
		REQUIRE(firstMaps.size() == 3);
		REQUIRE(firstMaps[1]["channel"] == 1);
		REQUIRE(firstMaps[1]["gain"] == 1.5);
		REQUIRE(firstMaps[1]["pedestal"] == 101.0);

		// Each run range resolves to its own assignment; both carry the same data
		Assignment* firstAssignment = firstCalib->GetAssignment("/schema6/shared");
		Assignment* secondAssignment = secondCalib->GetAssignment("/schema6/shared");
		REQUIRE(firstAssignment != NULL);
		REQUIRE(secondAssignment != NULL);
		REQUIRE(firstAssignment->GetId() == 3614);
		REQUIRE(secondAssignment->GetId() == 3615);
		REQUIRE(firstAssignment->GetRawData() == secondAssignment->GetRawData());
		REQUIRE(firstAssignment->GetData() == expectedRows);
		if(!firstCalib->IsCacheEnabled()) delete firstAssignment;
		if(!secondCalib->IsCacheEnabled()) delete secondAssignment;
	}

	//THE SAME, THROUGH THE DATA PROVIDER
	//----------------------------------------------------
	SECTION("Two assignments of one constant set, data provider", "GetAssignmentShort as the provider tests use it")
	{
		DataProvider *prov = new SQLiteDataProvider();
		prov->Connect(connectionString);

		Assignment* first = prov->GetAssignmentShort(firstRangeRun, "/schema6/shared", 0, "default", false);
		Assignment* second = prov->GetAssignmentShort(secondRangeRun, "/schema6/shared", 0, "default", false);
		REQUIRE(first != NULL);
		REQUIRE(second != NULL);
		REQUIRE(first->GetId() == 3614);
		REQUIRE(second->GetId() == 3615);
		vector<vector<string> > firstRows = first->GetData();
		REQUIRE(firstRows.size() == 3);
		REQUIRE(firstRows[0][0] == "0");
		REQUIRE(firstRows[0][1] == "1.25");
		REQUIRE(firstRows[2][2] == "99.5");
		REQUIRE(second->GetData() == firstRows);

		delete first;
		delete second;
		delete prov;
	}

	//1.0 AND 1.00: EQUAL NUMBERS, TWO CONSTANT SETS
	//----------------------------------------------------
	// Assignment 3616 (runs 0-999) stores the text 1.0, assignment 3617 (runs 1000-1999) stores 1.00
	SECTION("1.0 and 1.00", "The text is kept as written; as numbers both are 1.0")
	{
		string firstText;
		string secondText;
		REQUIRE(firstCalib->GetCalib(firstText, "/schema6/numeric"));
		REQUIRE(secondCalib->GetCalib(secondText, "/schema6/numeric"));
		REQUIRE(firstText == "1.0");
		REQUIRE(secondText == "1.00");

		// The single-number GetCalib fills the value but returns false even on success (a library bug older than
		// schema 6), so only the value it fills is checked here
		double firstNumber = 0;
		double secondNumber = 0;
		REQUIRE_NOTHROW(firstCalib->GetCalib(firstNumber, "/schema6/numeric"));
		REQUIRE_NOTHROW(secondCalib->GetCalib(secondNumber, "/schema6/numeric"));
		REQUIRE(firstNumber == 1.0);
		REQUIRE(secondNumber == 1.0);

		Assignment* firstAssignment = firstCalib->GetAssignment("/schema6/numeric");
		Assignment* secondAssignment = secondCalib->GetAssignment("/schema6/numeric");
		REQUIRE(firstAssignment != NULL);
		REQUIRE(secondAssignment != NULL);
		REQUIRE(firstAssignment->GetId() == 3616);
		REQUIRE(secondAssignment->GetId() == 3617);
		if(!firstCalib->IsCacheEnabled()) delete firstAssignment;
		if(!secondCalib->IsCacheEnabled()) delete secondAssignment;
	}

	//DEPRECATED TABLE AND VARIATION
	//----------------------------------------------------
	// Schema 6 adds deprecation columns; deprecation hides entries from listings only, so requests for
	// deprecated tables and variations read as before
	SECTION("Deprecated table and variation", "Read as before")
	{
		// Assignment 3618 of the deprecated table /schema6/retired_table, runs 0-999
		vector<vector<string> > retiredRows;
		REQUIRE(firstCalib->GetCalib(retiredRows, "/schema6/retired_table"));
		REQUIRE(retiredRows.size() == 1);
		REQUIRE(retiredRows[0].size() == 1);
		REQUIRE(retiredRows[0][0] == "2.5");
		Assignment* retiredAssignment = firstCalib->GetAssignment("/schema6/retired_table");
		REQUIRE(retiredAssignment != NULL);
		REQUIRE(retiredAssignment->GetId() == 3618);
		if(!firstCalib->IsCacheEnabled()) delete retiredAssignment;

		// The deprecated variation 'retired' has no data of its own, so requests fall back to its parent 'default'
		Calibration* retiredCalib = gen->MakeCalibration(connectionString, firstRangeRun, "retired");
		REQUIRE(retiredCalib->IsConnected());
		vector<vector<string> > fallbackRows;
		REQUIRE(retiredCalib->GetCalib(fallbackRows, "/schema6/retired_table"));
		REQUIRE(fallbackRows == retiredRows);

		Assignment* sharedAssignment = retiredCalib->GetAssignment("/schema6/shared");
		REQUIRE(sharedAssignment != NULL);
		REQUIRE(sharedAssignment->GetId() == 3614);
		REQUIRE(sharedAssignment->GetVariation()->GetName() == "default");
		if(!retiredCalib->IsCacheEnabled()) delete sharedAssignment;

		DataProvider *prov = new SQLiteDataProvider();
		prov->Connect(connectionString);
		Variation* retired = prov->GetVariation("retired");
		REQUIRE(retired != NULL);
		REQUIRE(retired->GetParent() != NULL);
		REQUIRE(retired->GetParent()->GetName() == "default");
		delete prov;    // variations are owned by the provider's cache
	}

	gen->DeleteCalibrations();
	delete gen;
}
