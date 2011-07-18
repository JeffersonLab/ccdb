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

/********************************************************************* ** 
 * @brief Test basic connection
 *
 * @return true if test passed
 */
bool test_DMySQLDataProviderConnection()
{
	TESTS_INIT("")

	DMySQLDataProvider *prov = new DMySQLDataProvider();

	//Connection
	gConsole.WriteLine(DConsole::cBrightWhite, "[ Connect testing ]");

	TITLE("Not connected                          ");
	TEST(!prov->IsConnected());

	TITLE("Connect                                ");
	TEST(prov->Connect(gConnectionString));

	TITLE("Connect status                         ");
	TEST(prov->IsConnected());

	TITLE("Disconnected IsConnected()             ");
	prov->Disconnect();
	TEST(!prov->IsConnected());

	TITLE("Reconnect                              ");
	TEST(prov->Connect(gConnectionString));

	//cleanup
	prov->Disconnect();
	delete prov;
	return true;
}
