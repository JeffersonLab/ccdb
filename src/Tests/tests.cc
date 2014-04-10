///
/// This is the simplest unit tests. 
/// Also the definition CATCH_CONFIG_MAIN means that Catch Unit Test framework will generate 'main' function. 
/// This define should be placed only once among all files wich contain tests
/// See more on the catch test framework here. 
/// https://github.com/philsquared/Catch
///
///==========================================================================================================

#define CATCH_CONFIG_MAIN  // This tell CATCH to provide a main() - only do this in one cpp file
//#define CATCH_CONFIG_RUNNER

#include "Tests/catch.hpp"
#include <stdlib.h>
#include <string>

//using namespace std;
//string gSQLiteConnectionString;
/*
int main (int argc, char* const argv[])
{
	// global setup...
	string ccdb_home(getenv("CCDB_HOME"));
	gSQLiteConnectionString = "sqlite://" + ccdb_home + "/mysql/ccdb.sqlite";
	cout<<"SQLite connection string: "<<gSQLiteConnectionString<<endl;

	int result = Catch::Main( argc, argv );

	// global clean-up...

	return result;
}*/
