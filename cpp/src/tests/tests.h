// This is not a formal unit tests config
#ifndef tests_h__
#define tests_h__

#include <string>
#include <stdexcept>

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
    return conStr;
}

#endif // tests_h__
