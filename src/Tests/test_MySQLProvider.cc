
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

bool test_DMySQLDataProviderConnection();  //Test basic connection
bool test_DMySQLDataProviderDirectories(); //Test of directories work

bool test_DMySQLDataProvider()
{
	
	TESTS_INIT(" ---  T E S T S    M y S Q L   D a t a   P r o v i d e r --- ");

	if(!test_DMySQLDataProviderConnection()) return false;
	
	//--- regulad tests
	if(!test_DMySQLDataProviderDirectories()) return false;

	//Ok< if connection test is done, we may play here a little

	DMySQLDataProvider *prov = new DMySQLDataProvider();
	if(!prov->Connect(gConnectionString)) return false;
	
	delete prov;
	return true;
}
