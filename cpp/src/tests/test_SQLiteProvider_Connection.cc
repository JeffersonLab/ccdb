#include "tests/catch.hpp"
#include "tests/tests.h"

#include "CCDB/Providers/SQLiteDataProvider.h"

using namespace std;
using namespace ccdb;

/********************************************************************* **
 * @brief Test basic connection
 *
 * @return true if test passed
 */
TEST_CASE("CCDB/SQLiteDataProvider/Connection","Connection tests")
{
	SQLiteDataProvider *prov = new SQLiteDataProvider();

	//Pre Connection
	REQUIRE_FALSE(prov->IsConnected());
    
    //Connection
    REQUIRE_NOTHROW(prov->Connect(TESTS_SQLITE_STRING));
	REQUIRE(prov->IsConnected());
    REQUIRE(string(prov->GetConnectionString()) == string(TESTS_SQLITE_STRING));

    //disconnect
	prov->Disconnect();
	REQUIRE_FALSE(prov->IsConnected());

	//reconnect
    REQUIRE_NOTHROW(prov->Connect(TESTS_SQLITE_STRING));

	//cleanup
	prov->Disconnect();
	delete prov;
}
