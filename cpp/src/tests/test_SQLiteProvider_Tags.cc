#pragma warning(disable:4800)
#include "tests/tests.h"
#include "tests/catch.hpp"

#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "CCDB/Calibration.h"
#include "CCDB/CalibrationGenerator.h"
#include "CCDB/Providers/SQLiteDataProvider.h"
#include "CCDB/Model/Assignment.h"
#include "CCDB/Model/Variation.h"

#if defined(_WIN32) || defined(WIN32)
#define timegm _mkgmtime
#endif

using namespace std;
using namespace ccdb;


/** *********************************************************************
 * @brief Tags of the web GUI fixture resolved by the C++ library (CCDB 2.5)
 *
 * A request /path:run@NAME resolves with the variation and the snapshot time of the tag NAME.
 * scripts/webgui/make_fixture.py (add_schema6_cases) creates two tags on variation 'default':
 *   fixture_newest - snapshotTime 2020-01-06 10:17:00, the creation time of assignment 3618, the newest
 *   fixture_past   - snapshotTime 2020-01-02 12:00:00, inside the fixture's history
 * snapshotTime is UTC, assignments.created is the writing client's local time. The fixture writes both
 * as UTC values, so the test runs with TZ=UTC.
 *
 * /calib/fcal/gains for run 500 (range 0-999) straddles 2020-01-02 12:00: assignment 1380 was created
 * at 2020-01-02 11:29, the next one, 1620, at 15:29, the newest, 3582, at 2020-01-04 00:11.
 *
 * Skip/CI-fail pattern as in test_SQLiteProvider_SharedSets.cc: CCDB_TEST_FIXTURE_CONNECTION
 */
TEST_CASE("CCDB/SQLiteDataProvider/Tags", "[fixture] Schema 6 fixture: tags")
{
	const char* fixtureConnection = getenv("CCDB_TEST_FIXTURE_CONNECTION");
	if(!fixtureConnection) {
		if(getenv("CI")) {
			FAIL("CCDB_TEST_FIXTURE_CONNECTION is not set. Under CI it is required: build the fixture with "
			     "scripts/webgui/make_fixture.py --out <file> and export CCDB_TEST_FIXTURE_CONNECTION=sqlite:///<file>");
		}
		WARN("CCDB_TEST_FIXTURE_CONNECTION is not set: the schema 6 tags test is skipped");
		SUCCEED();
		return;
	}
	const string connectionString(fixtureConnection);

	// The fixture's times are UTC values; the guard restores the previous TZ, also when a REQUIRE fails
	struct TzGuard {
		bool hadTz;
		string previousTz;
		TzGuard() {
			const char* value = getenv("TZ");
			hadTz = value != nullptr;
			if(hadTz) previousTz = value;
			setenv("TZ", "UTC", 1);
			tzset();
		}
		~TzGuard() {
			if(hadTz) setenv("TZ", previousTz.c_str(), 1); else unsetenv("TZ");
			tzset();
		}
	} tzGuard;

	const int run = 500;

	SECTION("Tag requests through Calibration", "/path@tag and /path:run@tag")
	{
		CalibrationGenerator* gen = new CalibrationGenerator();
		Calibration* calib = gen->MakeCalibration(connectionString, run, "default");
		REQUIRE(calib->IsConnected());

		// The tag at the newest creation time sees everything
		Assignment* shared = calib->GetAssignment("/schema6/shared@fixture_newest");
		REQUIRE(shared != NULL);
		REQUIRE(shared->GetId() == 3614);
		if(!calib->IsCacheEnabled()) delete shared;

		Assignment* sharedOtherRun = calib->GetAssignment("/schema6/shared:1500@fixture_newest");
		REQUIRE(sharedOtherRun != NULL);
		REQUIRE(sharedOtherRun->GetId() == 3615);
		if(!calib->IsCacheEnabled()) delete sharedOtherRun;

		// The tag's time is the creation time of assignment 3618 itself: it is included
		Assignment* retired = calib->GetAssignment("/schema6/retired_table@fixture_newest");
		REQUIRE(retired != NULL);
		REQUIRE(retired->GetId() == 3618);
		if(!calib->IsCacheEnabled()) delete retired;

		Assignment* newest = calib->GetAssignment("/calib/fcal/gains:500@fixture_newest");
		REQUIRE(newest != NULL);
		REQUIRE(newest->GetId() == 3582);
		if(!calib->IsCacheEnabled()) delete newest;

		// The past tag returns the assignment that was the newest at 2020-01-02 12:00
		Assignment* past = calib->GetAssignment("/calib/fcal/gains@fixture_past");
		REQUIRE(past != NULL);
		REQUIRE(past->GetId() == 1380);
		if(!calib->IsCacheEnabled()) delete past;

		Assignment* pastWithRun = calib->GetAssignment("/calib/fcal/gains:500@fixture_past");
		REQUIRE(pastWithRun != NULL);
		REQUIRE(pastWithRun->GetId() == 1380);
		if(!calib->IsCacheEnabled()) delete pastWithRun;

		// Empty variation and time parts are allowed with a tag
		Assignment* pastEmptyVariation = calib->GetAssignment("/calib/fcal/gains:500:@fixture_past");
		REQUIRE(pastEmptyVariation != NULL);
		REQUIRE(pastEmptyVariation->GetId() == 1380);
		if(!calib->IsCacheEnabled()) delete pastEmptyVariation;

		Assignment* pastEmptyRun = calib->GetAssignment("/calib/fcal/gains::@fixture_past");
		REQUIRE(pastEmptyRun != NULL);
		REQUIRE(pastEmptyRun->GetId() == 1380);
		if(!calib->IsCacheEnabled()) delete pastEmptyRun;

		Assignment* pastEmptyTime = calib->GetAssignment("/calib/fcal/gains:500::@fixture_past");
		REQUIRE(pastEmptyTime != NULL);
		REQUIRE(pastEmptyTime->GetId() == 1380);
		if(!calib->IsCacheEnabled()) delete pastEmptyTime;

		// Without a tag the same request gives the newest
		Assignment* untagged = calib->GetAssignment("/calib/fcal/gains:500");
		REQUIRE(untagged != NULL);
		REQUIRE(untagged->GetId() == 3582);
		if(!calib->IsCacheEnabled()) delete untagged;

		vector<vector<string> > rows;
		REQUIRE(calib->GetCalib(rows, "/schema6/shared@fixture_newest"));
		REQUIRE(rows.size() == 3);
		REQUIRE(rows[1][1] == "1.5");

		// A tag with a variation or a time is an error, both ways
		REQUIRE_THROWS(calib->GetAssignment("/schema6/shared:500:default@fixture_newest"));
		REQUIRE_THROWS(calib->GetAssignment("/schema6/shared:500::2020@fixture_newest"));
		REQUIRE_THROWS(calib->GetAssignment("/schema6/shared:500@fixture_newest:default"));
		REQUIRE_THROWS(calib->GetAssignment("/schema6/shared@fixture_newest::2020"));

		// An unknown tag is an error
		REQUIRE_THROWS(calib->GetAssignment("/schema6/shared@no_such_tag"));
	}

	SECTION("The tag replaces the calibration's variation", "Calibration made for variation 'retired'")
	{
		CalibrationGenerator* gen = new CalibrationGenerator();
		Calibration* calib = gen->MakeCalibration(connectionString, run, "retired");
		REQUIRE(calib->IsConnected());
		Assignment* shared = calib->GetAssignment("/schema6/shared@fixture_newest");
		REQUIRE(shared != NULL);
		REQUIRE(shared->GetId() == 3614);
		REQUIRE(shared->GetVariation()->GetName() == "default");
		if(!calib->IsCacheEnabled()) delete shared;
	}

	SECTION("Tag requests through the data provider", "GetAssignmentShortByTag")
	{
		DataProvider *prov = new SQLiteDataProvider();
		prov->Connect(connectionString);

		Assignment* past = prov->GetAssignmentShortByTag(run, "/calib/fcal/gains", "fixture_past", false);
		REQUIRE(past != NULL);
		REQUIRE(past->GetId() == 1380);
		REQUIRE(past->GetVariation()->GetName() == "default");
		delete past;

		Assignment* newest = prov->GetAssignmentShortByTag(run, "/calib/fcal/gains", "fixture_newest", false);
		REQUIRE(newest != NULL);
		REQUIRE(newest->GetId() == 3582);
		delete newest;

		// The same as the explicit variation and time of the tag
		struct tm pastTime;
		memset(&pastTime, 0, sizeof(pastTime));
		pastTime.tm_year = 2020 - 1900; pastTime.tm_mon = 0; pastTime.tm_mday = 2; pastTime.tm_hour = 12;
		Assignment* explicitPast = prov->GetAssignmentShort(run, "/calib/fcal/gains", timegm(&pastTime), "default", false);
		REQUIRE(explicitPast != NULL);
		REQUIRE(explicitPast->GetId() == 1380);
		delete explicitPast;

		// /schema6/shared was created after the past tag
		Assignment* none = prov->GetAssignmentShortByTag(run, "/schema6/shared", "fixture_past", false);
		REQUIRE(none == NULL);

		REQUIRE_THROWS(prov->GetAssignmentShortByTag(run, "/schema6/shared", "no_such_tag", false));
		REQUIRE_THROWS(prov->GetAssignmentShortByTag(run, "/schema6/shared", "", false));
		REQUIRE_THROWS(prov->GetAssignmentShortByTag(run, "/schema6/shared", "bad\"name", false));
		REQUIRE_THROWS(prov->GetAssignmentShortByTag(run, "/schema6/shared", "fixture-past", false));

		// A variation is only a variation: "@NAME" is not read as a tag
		REQUIRE_THROWS(prov->GetAssignmentShort(run, "/calib/fcal/gains", 0, "@fixture_past", false));

		REQUIRE(DataProvider::UtcDateTimeToUnixTime("2020-01-06 10:17:00.000000") == 1578305820);
		REQUIRE(DataProvider::UtcDateTimeToUnixTime("2020-01-02 12:00:00") == 1577966400);
		REQUIRE(DataProvider::UtcDateTimeToUnixTime("garbage") == -1);
		delete prov;
	}

}
