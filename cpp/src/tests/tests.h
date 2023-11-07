// This is not a formal unit tests config
#ifndef tests_h__
#define tests_h__

#include <string>

#ifndef WIN32
    #define TESTS_CONENCTION_STRING
    #define TESTS_SQLITE_STRING ( "sqlite:///" + string() + "/sql/ccdb.sqlite")
#else
    #define TESTS_CONENCTION_STRING "mysql://ccdb_user@127.0.0.1:3306/ccdb_test"
    #define TESTS_SQLITE_STRING "sqlite://..\\..\\..\\sql\\ccdb.sqlite"
#endif

inline std::string get_default_test_mysql_connection() {
    return "mysql://ccdb_user@127.0.0.1:3306/ccdb_test";
}

inline std::string get_default_test_sqlite_connection() {
    auto ccdb_home = getenv("CCDB_HOME");
    return "mysql://ccdb_user@127.0.0.1:3306/ccdb_test";
}

#endif // tests_h__
