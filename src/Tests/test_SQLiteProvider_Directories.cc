#pragma warning(disable:4800)
#include "Tests/catch.hpp"
#include "Tests/tests.h"

#include "CCDB/Providers/SQLiteDataProvider.h"
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
TEST_CASE("CCDB/SQLiteDataProvider/Directories","Directories tests")
{	
	SQLiteDataProvider *prov = new SQLiteDataProvider();
	if(!prov->Connect(TESTS_SQLITE_STRING)) return;
	
	//get directory by path
	Directory *dir=prov->GetDirectory("/test/subtest");
	REQUIRE(dir!=NULL);
	

	//Search directories by pattern	
	//vector<Directory *> dirs = prov->SearchDirectories(static_cast<string>("t??t_va*"), "/test");
	//REQUIRE(dirs.size()>0);

	//dirs = prov->SearchDirectories("t??t_va*");
	//REQUIRE(dirs.size()>0);
	//	
	////Search directories by pattern
	//dirs = prov->SearchDirectories(static_cast<string>("*"), "/");
	//REQUIRE(dirs.size()>0);
	//
	//Ok, lets check if directory for the next text exists...
/*	if(dir=prov->GetDirectory("/test/testdir"))
	{
		delete dir; 
		//ok we haven't test it, but have to use it... 
		prov->DeleteDirectory("/test/testdir");
	}

	//Create test directory structure
	REQUIRE(prov->MakeDirectory("testdir", "/test"));

	//create subdirectory
	REQUIRE(prov->MakeDirectory("constants","/test/testdir","My constants"));

	//refuse to create existing directory
    Log::SetErrorLevel(0); //suppress log messages

	REQUIRE_FALSE(prov->MakeDirectory("constants","/test/testdir","My constants"));

	//create subdirectory
	REQUIRE(prov->MakeDirectory("variables","/test/testdir",""));
	
	//create third subdirectory
	REQUIRE(prov->MakeDirectory("my_vars","/test/testdir",""));

	
    //Delete subdirectory
	REQUIRE(prov->DeleteDirectory("/test/testdir/constants"));

	//Delete non empty directory prohibit
	REQUIRE_FALSE(prov->DeleteDirectory("/test/testdir"));
	
 //   //Delete subdirectory with nested directorite
    REQUIRE(prov->DeleteDirectory("/test/testdir/variables"));
    REQUIRE(prov->DeleteDirectory("/test/testdir/my_vars"));
    REQUIRE(prov->DeleteDirectory("/test/testdir"));
    Log::SetErrorLevel(3); //suppress log messages
	*/
}
