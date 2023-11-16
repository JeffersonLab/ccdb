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
    REQUIRE_NOTHROW(prov->Connect(get_test_sqlite_connection()));
	REQUIRE(prov->IsConnected());
    REQUIRE(string(prov->GetConnectionString()) == string(get_test_sqlite_connection()));

    //disconnect
	prov->Disconnect();
	REQUIRE_FALSE(prov->IsConnected());

	//reconnect
    REQUIRE_NOTHROW(prov->Connect(get_test_sqlite_connection()));

	//cleanup
	prov->Disconnect();
	delete prov;
}
