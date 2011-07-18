
#pragma warning(disable:4800)
#include "Tests/tests_macros.h"
#include "DConsole.h"
#include "DStringUtils.h"
#include "Providers/DMySQLDataProvider.h"
#include "Model/DDirectory.h"
#include "DWorkUtils.h"
#include "DStopWatch.h"

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
