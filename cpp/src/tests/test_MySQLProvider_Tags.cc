#pragma warning(disable:4800)
#include "tests/catch.hpp"
#include "tests/tests.h"

#ifdef CCDB_MYSQL

#include <mysql.h>
#include <string>

#include "CCDB/Providers/MySQLDataProvider.h"
#include "CCDB/Model/Assignment.h"
#include "CCDB/Model/Variation.h"
#include "CCDB/Calibration.h"
#include "CCDB/CalibrationGenerator.h"

using namespace std;
using namespace ccdb;


/** Runs SQL on the test database with the MySQL C API: the C++ library has no API that writes tags */
static void ExecuteTestSql(const string& connectionString, const vector<string>& statements)
{
    MySQLConnectionInfo info = MySQLDataProvider::ParseConnectionString(connectionString);
    MYSQL* handle = mysql_init(nullptr);
    REQUIRE(handle != nullptr);
    MYSQL* connected = mysql_real_connect(handle, info.HostName.c_str(), info.UserName.c_str(), info.Password.c_str(),
                                          info.Database.c_str(), info.Port, nullptr, 0);
    if(!connected) {
        string error = mysql_error(handle);
        mysql_close(handle);
        FAIL("Can't connect to the test database: " + error);
    }
    for(const auto& statement: statements) {
        if(mysql_query(handle, statement.c_str()) != 0) {
            string error = mysql_error(handle);
            mysql_close(handle);
            FAIL("Error executing '" + statement + "': " + error);
        }
    }
    mysql_close(handle);
}


/** *********************************************************************
 * @brief Tags on MySQL (CCDB 2.5)
 *
 * The test data of db init: /test/test_vars/test_table has assignments 1 (default, created 2012-07-30 23:48:42),
 * 4 (default, 2012-10-30 23:48:42) and 5 (subtest, 2012-10-30 23:48:43). The tags inserted here lie a day or more
 * away from those times, so the server's time zone does not change the expected assignments.
 * snapshotTime is UTC; the provider compares UNIX_TIMESTAMP(assignments.created) with its unix time (timegm).
 */
TEST_CASE("CCDB/MySQLDataProvider/Tags", "[mysql] tags")
{
    string connectionString = get_test_mysql_connection();
    ExecuteTestSql(connectionString, {
        "DELETE FROM `tags` WHERE `name` LIKE 'cpp_tag_%'",
        "INSERT INTO `tags` (`name`, `variationId`, `snapshotTime`, `comment`) VALUES "
        "('cpp_tag_between', 1, '2012-08-30 00:00:00', 'C++ test: between assignments 1 and 4'), "
        "('cpp_tag_after', 1, '2012-11-01 00:00:00', 'C++ test: after assignment 4'), "
        "('cpp_tag_subtest', 4, '2012-11-01 00:00:00', 'C++ test: variation subtest after assignment 5'), "
        "('cpp_tag_subtest_old', 4, '2012-08-01 00:00:00', 'C++ test: variation subtest before its assignments')"
    });

    DataProvider *prov = new MySQLDataProvider();
    prov->Connect(connectionString);
    REQUIRE(prov->IsConnected());

    SECTION("Data provider", "GetAssignmentShortByTag")
    {
        Assignment* between = prov->GetAssignmentShortByTag(100, "/test/test_vars/test_table", "cpp_tag_between", false);
        REQUIRE(between != NULL);
        REQUIRE(between->GetId() == 1);
        delete between;

        Assignment* after = prov->GetAssignmentShortByTag(100, "/test/test_vars/test_table", "cpp_tag_after", false);
        REQUIRE(after != NULL);
        REQUIRE(after->GetId() == 4);
        delete after;

        Assignment* subtest = prov->GetAssignmentShortByTag(100, "/test/test_vars/test_table", "cpp_tag_subtest", false);
        REQUIRE(subtest != NULL);
        REQUIRE(subtest->GetId() == 5);
        delete subtest;

        // subtest -> test -> default: only assignment 1 of default existed then
        Assignment* subtestOld = prov->GetAssignmentShortByTag(1000, "/test/test_vars/test_table", "cpp_tag_subtest_old", false);
        REQUIRE(subtestOld != NULL);
        REQUIRE(subtestOld->GetId() == 1);
        delete subtestOld;

        REQUIRE_THROWS(prov->GetAssignmentShortByTag(100, "/test/test_vars/test_table", "cpp_tag_none", false));
        REQUIRE_THROWS(prov->GetAssignmentShortByTag(100, "/test/test_vars/test_table", "", false));
        REQUIRE_THROWS(prov->GetAssignmentShortByTag(100, "/test/test_vars/test_table", "bad\"name", false));
        REQUIRE_THROWS(prov->GetAssignmentShortByTag(100, "/test/test_vars/test_table", "bad' OR '1'='1", false));
        REQUIRE_THROWS(prov->GetAssignmentShortByTag(100, "/test/test_vars/test_table", "cpp-tag-after", false));

        // A variation is only a variation: "@NAME" is not read as a tag
        REQUIRE_THROWS(prov->GetAssignmentShort(100, "/test/test_vars/test_table", 0, "@cpp_tag_between", false));

        // No assignment and no parent variation: still an error (the type table is freed before it)
        REQUIRE_THROWS(prov->GetAssignmentShort(100, "/test/test_vars/test_table", 1, "default", false));
    }

    SECTION("Calibration", "Request strings with a tag")
    {
        CalibrationGenerator gen;
        Calibration* calib = gen.MakeCalibration(connectionString, 100, "default");
        REQUIRE(calib->IsConnected());

        Assignment* between = calib->GetAssignment("/test/test_vars/test_table@cpp_tag_between");
        REQUIRE(between != NULL);
        REQUIRE(between->GetId() == 1);
        if(!calib->IsCacheEnabled()) delete between;

        Assignment* subtest = calib->GetAssignment("/test/test_vars/test_table:100@cpp_tag_subtest");
        REQUIRE(subtest != NULL);
        REQUIRE(subtest->GetId() == 5);
        if(!calib->IsCacheEnabled()) delete subtest;

        // Empty variation and time parts are allowed with a tag
        Assignment* emptyParts = calib->GetAssignment("/test/test_vars/test_table:100::@cpp_tag_between");
        REQUIRE(emptyParts != NULL);
        REQUIRE(emptyParts->GetId() == 1);
        if(!calib->IsCacheEnabled()) delete emptyParts;

        // Untagged, the same request gives the newest of default
        Assignment* untagged = calib->GetAssignment("/test/test_vars/test_table:100");
        REQUIRE(untagged != NULL);
        REQUIRE(untagged->GetId() == 4);
        if(!calib->IsCacheEnabled()) delete untagged;

        REQUIRE_THROWS(calib->GetAssignment("/test/test_vars/test_table:100:default@cpp_tag_after"));
        REQUIRE_THROWS(calib->GetAssignment("/test/test_vars/test_table@cpp_tag_after::2013"));
    }

    delete prov;
    ExecuteTestSql(connectionString, {"DELETE FROM `tags` WHERE `name` LIKE 'cpp_tag_%'"});
}

#endif //CCDB_MYSQL
