// MySQL provider behavior that does not need a MySQL server
#ifdef CCDB_MYSQL
#include "tests/catch.hpp"
#include "tests/tests.h"

#include <string>

#include "CCDB/Providers/MySQLDataProvider.h"
#include "CCDB/MySQLCalibration.h"

using namespace std;
using namespace ccdb;

// Nothing listens on port 1 of the local host, so the connection is refused at once
static const char* kRefusedConnection = "mysql://ccdb_user:S3cretPw@127.0.0.1:1/ccdb";

TEST_CASE("CCDB/MySQLDataProvider/NoServer/FailedConnect", "[mysql-noserver]")
{
    MySQLDataProvider prov;

    for (int attempt = 0; attempt < 2; attempt++) {
        string message;
        try { prov.Connect(kRefusedConnection); }
        catch (const std::exception& ex) { message = ex.what(); }

        REQUIRE_FALSE(message.empty());
        REQUIRE(message.find("S3cretPw") == string::npos);
        REQUIRE_FALSE(prov.IsConnected());
    }

    // Disconnect after failed connects releases the client handle and is idempotent
    REQUIRE_NOTHROW(prov.Disconnect());
    REQUIRE_NOTHROW(prov.Disconnect());
    REQUIRE_FALSE(prov.IsConnected());
}


TEST_CASE("CCDB/MySQLDataProvider/NoServer/ParseErrorMasksPassword", "[mysql-noserver]")
{
    MySQLDataProvider prov;
    string message;
    try { prov.Connect("MySQL://ccdb_user:S3cretPw@host/ccdb"); }
    catch (const std::exception& ex) { message = ex.what(); }

    REQUIRE_FALSE(message.empty());
    REQUIRE(message.find("S3cretPw") == string::npos);
    REQUIRE(message.find("ccdb_user:***@host") != string::npos);
}


TEST_CASE("CCDB/MySQLCalibration/NoServer/DisconnectNeverConnected", "[mysql-noserver]")
{
    MySQLCalibration calib(100);
    REQUIRE_FALSE(calib.IsConnected());
    REQUIRE_NOTHROW(calib.Disconnect());

    REQUIRE_THROWS(calib.Connect(kRefusedConnection));
    REQUIRE_FALSE(calib.IsConnected());
    REQUIRE_NOTHROW(calib.Disconnect());
}
#endif //CCDB_MYSQL
