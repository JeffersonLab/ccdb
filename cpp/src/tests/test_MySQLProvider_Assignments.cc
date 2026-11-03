#pragma warning(disable:4800)
#ifdef CCDB_MYSQL
#include "tests/tests.h"
#include "tests/catch.hpp"

#include "CCDB/Helpers/StringUtils.h"
#include "CCDB/Providers/MySQLDataProvider.h"
#include "CCDB/Model/Variation.h"
#include "CCDB/Model/Directory.h"
#include "CCDB/Model/RunRange.h"
#include "CCDB/Model/ConstantsTypeTable.h"

using namespace std;
using namespace ccdb;

/********************************************************************* ** 
 * @brief Test of directories work
 *
 * @return true if test passed
 */
TEST_CASE("CCDB/MySQLDataProvider/Assignments", "[mysql] Assignments tests")
{
    DataProvider *prov = new MySQLDataProvider();
    prov->Connect(get_test_mysql_connection());

    // GetAssignmentFull (issue #94): the data, and the run range, variation, comment and times with it
    Assignment* assignment = prov->GetAssignmentFull(100, "/test/test_vars/test_table");
    REQUIRE(assignment != nullptr);
    REQUIRE(assignment->GetId() == 4);
    REQUIRE(assignment->GetVariation() != nullptr);
    REQUIRE(assignment->GetVariation()->GetName() == "default");
    REQUIRE(assignment->GetRunRange() != nullptr);
    REQUIRE(assignment->GetRunRange()->GetMin() == 0);
    REQUIRE(assignment->GetRunRange()->GetMax() == INFINITE_RUN);
    REQUIRE(assignment->GetComment() == "Test assignment for software tests 4");
    REQUIRE(assignment->GetCreatedTime() > 1340000000);    // created in 2012
    REQUIRE(assignment->GetTypeTable() != nullptr);
    REQUIRE(assignment->GetTypeTable()->GetColumns().size() == 3);
    vector<vector<string> > values = assignment->GetData();
    REQUIRE(values.size() == 2);
    REQUIRE(values[0][0] == "2.2");
    REQUIRE(values[1][2] == "2.7");
    delete assignment;

    // A variation with no data of its own: the data and the variation reported are the parent's
    assignment = prov->GetAssignmentFull(100, "/test/test_vars/test_table", "test");
    REQUIRE(assignment != nullptr);
    REQUIRE(assignment->GetId() == 4);
    REQUIRE(assignment->GetVariation()->GetName() == "default");
    delete assignment;

    // The variation's own data
    assignment = prov->GetAssignmentFull(100, "/test/test_vars/test_table", "subtest");
    REQUIRE(assignment != nullptr);
    REQUIRE(assignment->GetVariation()->GetName() == "subtest");
    REQUIRE(assignment->GetComment() == "Test assignment for software tests 5");
    delete assignment;

    delete prov;
}
#endif //ifdef CCDB_MYSQL
