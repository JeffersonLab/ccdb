// This is not a formal unit tests config
#ifndef tests_h__
#define tests_h__

#include <string>
#include <stdexcept>

#ifndef WIN32
    #define TESTS_CONENCTION_STRING
    #define TESTS_SQLITE_STRING ( "sqlite:///" + string() + "/sql/ccdb.sqlite")
#else
    #define TESTS_CONENCTION_STRING "mysql://ccdb_user@127.0.0.1:3306/ccdb_test"
    #define TESTS_SQLITE_STRING "sqlite://..\\..\\..\\sql\\ccdb.sqlite"
#endif

inline std::string get_test_mysql_connection() {
    auto conStr = getenv("CCDB_TEST_MYSQL_CONNECTION");
    if(!conStr) {
        throw std::runtime_error("Environment variable CCDB_TEST_MYSQL_CONNECTION is not set. It is required for MySQL tests");
    }

    return conStr;
}

inline std::string get_test_sqlite_connection() {
    auto conStr = getenv("CCDB_TEST_SQLITE_CONNECTION");
    if(!conStr) {
        throw std::runtime_error("Environment variable CCDB_TEST_SQLITE_CONNECTION is not set. It is required for MySQL tests");
    }
}

#endif // tests_h__
