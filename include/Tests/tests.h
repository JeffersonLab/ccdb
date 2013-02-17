// This is not a formal unit tests config
#ifndef tests_h__
#define tests_h__

#include <string>



#ifndef WIN32
#define TESTS_CONENCTION_STRING "mysql://ccdb_user@127.0.0.1:3306/ccdb"
#define TESTS_SQLITE_STRING ( "sqlite://" + string(getenv("CCDB_HOME")) + "/sql/ccdb.sqlite").c_str()

#else
#define TESTS_CONENCTION_STRING "mysql://ccdb_user@127.0.0.1:3306/ccdb"
#define TESTS_SQLITE_STRING "sqlite://..\\..\\..\\sql\\ccdb.sqlite"
#endif


#endif // tests_h__
