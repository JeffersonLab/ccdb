#pragma warning(disable:4800)
#ifdef CCDB_MYSQL
#include "Tests/catch.hpp"
#include "Tests/tests.h"

#include "CCDB/Providers/MySQLDataProvider.h"
#include "CCDB/Model/Directory.h"
#include "CCDB/Log.h"

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
	if(!prov->Connect(TESTS_CONENCTION_STRING)) return;
	
	//get directory by path
	Directory *dir=prov->GetDirectory("/test/subtest");
	REQUIRE(dir!=NULL);
	

	//Search directories by pattern	
	vector<Directory *> dirs = prov->SearchDirectories(static_cast<string>("t??t_va*"), "/test");
	REQUIRE(dirs.size()>0);

	dirs = prov->SearchDirectories("t??t_va*");
	REQUIRE(dirs.size()>0);
		
	//Search directories by pattern
	dirs = prov->SearchDirectories(static_cast<string>("*"), "/");
	REQUIRE(dirs.size()>0);
}
#endif //ifdef CCDB_MYSQL
