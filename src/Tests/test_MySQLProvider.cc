
#pragma warning(disable:4800)
#ifdef CCDB_MYSQL

#include "Tests/catch.hpp"

#include "CCDB/Providers/MySQLDataProvider.h"
#include "CCDB/Model/Directory.h"
#include "CCDB/Helpers/StringUtils.h"

using namespace std;
using namespace ccdb;

TEST_CASE("CCDB/MySQLDataProvider","MySQLDataProvider base tests")
{
    MySQLDataProvider * prov = NULL;
    prov = new MySQLDataProvider();
    REQUIRE(prov!=NULL);
    //REQUIRED_CATEGORY("CCDB/MySQLDataProvider/Connection");
}
#endif //ifdef CCDB_MYSQL
