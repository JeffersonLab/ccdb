#pragma warning(disable:4800)
#ifdef CCDB_MYSQL
#include "Tests/catch.hpp"
#include "Tests/tests.h"

#include "CCDB/Providers/MySQLDataProvider.h"
#include "CCDB/Model/Directory.h"

#include <iostream>

using namespace std;
using namespace ccdb;

/********************************************************************* ** 
 * @brief Test of directories work
 *
 * @return true if test passed
 */
TEST_CASE("CCDB/MySQLDataProvider/Directories","Directories tests")
{	
	MySQLDataProvider *prov = new MySQLDataProvider();
	prov->Connect(get_test_mysql_connection());
	
	//get directory by path
	Directory *dir=prov->GetDirectory("/test/subtest");
	REQUIRE(dir!=NULL);
}
#endif //ifdef CCDB_MYSQL
