#pragma warning(disable:4800)
#include "Tests/tests_macros.h"
#include "CCDB/Console.h"
#include "CCDB/Helpers/StringUtils.h"
#include "CCDB/Providers/MySQLDataProvider.h"
#include "CCDB/Model/Directory.h"
#include "CCDB/Helpers/WorkUtils.h"
#include "CCDB/Helpers/StopWatch.h"


using namespace std;
using namespace ccdb;

/********************************************************************* ** 
 * @brief Test of directories work
 *
 * @return true if test passed
 */
bool test_DMySQLDataProviderDirectories()
{
	TESTS_INIT("")
	
	DMySQLDataProvider *prov = new DMySQLDataProvider();
	if(!prov->Connect(gConnectionString)) return false;

	//Directories
	gConsole.WriteLine(Console::cBrightWhite, "\n[ Directories testing ]");

	//List of directories
	gConsole.Write(Console::cBrightCyan, "\nCheck list of directories");
	PrintDirectoryTree(prov->GetRootDirectory(), false);
	gConsole.WriteLine();
	
	//get directory by path
	TITLE("Get Directory by path");
	DDirectory *dir=prov->GetDirectory("/test/subtest");
	TEST(dir!=NULL);
	

	//Search directories by pattern	
	vector<DDirectory *> dirs = prov->SearchDirectories(static_cast<string>("t??t_va*"), "/test");
	TITLE("Search directory by parent in parent"); TEST_STEP(dirs.size()>0);

	dirs = prov->SearchDirectories("t??t_va*");
	TITLE("Search directory *"); TEST_STEP(dirs.size()>0);
		
	//Search directories by pattern
	TITLE("Search by * in /   ");
	 dirs = prov->SearchDirectories(static_cast<string>("*"), "/");
	TEST_STEP(dirs.size()>0);
	
	//Ok, lets check if directory for the next text exists...
	if(dir=prov->GetDirectory("/test/testdir"))
	{
		delete dir; 
		//ok we havent test it, but have to use it... 
		prov->DeleteDirectory("/test/testdir");
	}

	//Create test directory structure
	TITLE("MakeDirectory");
	TEST(prov->MakeDirectory("testdir", "/test"));

	//create subdirectory
	TITLE("Create SubDirectory 1");
	TEST(prov->MakeDirectory("constants","/test/testdir","My constants"));

	//refuse to create existing directory
	TITLE("Refuse to create existing directory");
	TEST(!prov->MakeDirectory("constants","/test/testdir","My constants"));

	//create subdirectory
	TITLE("Create second subdirectory");
	TEST(prov->MakeDirectory("variables","/test/testdir",""));
	
	//create third subdirectory
	TITLE("Create third subdirectory");
	TEST(prov->MakeDirectory("my_vars","/test/testdir",""));

	//list what we have
	gConsole.Write(Console::cBrightCyan,"\nCheck list of directories");
	PrintDirectoryTree(prov->GetRootDirectory(), false);
	gConsole.WriteLine();

	TITLE("Delete subdirectory");
	TEST(prov->DeleteDirectory("/test/testdir/constants"));

	TITLE("Delete non emty directory prohibit");
	TEST(!prov->DeleteDirectory("/test/testdir"));
	
	TITLE("Delete subdirectory 2"); TEST(prov->DeleteDirectory("/test/testdir/my_vars"));
	TITLE("Delete subdirectory 3");	TEST(prov->DeleteDirectory("/test/testdir/variables"));
	TITLE("Delete subdirectory 4");	TEST(prov->DeleteDirectory("/test/testdir"));

	gConsole.Write(Console::cBrightCyan,"\nCheck list of directories");
	PrintDirectoryTree(prov->GetRootDirectory(), false);
	gConsole.WriteLine();
	return true;
}