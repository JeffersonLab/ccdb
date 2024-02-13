#pragma warning(disable:4800)
#ifdef CCDB_MYSQL
#include "tests/catch.hpp"
#include "tests/tests.h"

#include "CCDB/Providers/MySQLDataProvider.h"
#include "CCDB/Model/Directory.h"

using namespace std;
using namespace ccdb;

bool test_DMySQLDataProviderConnection();  //Test basic connection

/********************************************************************* ** 
 * @brief Test basic connection
 *
 * @return true if test passed
 */
TEST_CASE("CCDB/MySQLDataProvider/Connection","Connection tests")
{
	MySQLDataProvider *prov = new MySQLDataProvider();

	//Pre Connection
	REQUIRE_FALSE(prov->IsConnected());
    
    //Connection
	REQUIRE_NOTHROW(prov->Connect(get_test_mysql_connection()));
	REQUIRE(prov->IsConnected());
    REQUIRE(prov->GetConnectionString() == get_test_mysql_connection());

    //disconnect
	prov->Disconnect();
	REQUIRE_FALSE(prov->IsConnected());

	//reconnect
	REQUIRE_NOTHROW(prov->Connect(get_test_mysql_connection()));

	//cleanup
	prov->Disconnect();
	delete prov;
}
#endif //ifdef CCDB_MYSQL
