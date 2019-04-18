#pragma warning(disable:4800)
#ifdef CCDB_MYSQL
#include "Tests/catch.hpp"
#include "Tests/tests.h"

#include "CCDB/Console.h"
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
	REQUIRE(prov->Connect(TESTS_CONENCTION_STRING));
	REQUIRE(prov->IsConnected());
    REQUIRE(prov->GetConnectionString() == TESTS_CONENCTION_STRING);

    //disconnect
	prov->Disconnect();
	REQUIRE_FALSE(prov->IsConnected());

	//reconnect
	REQUIRE(prov->Connect(TESTS_CONENCTION_STRING));

	//cleanup
	prov->Disconnect();
	delete prov;
}
#endif //ifdef CCDB_MYSQL
