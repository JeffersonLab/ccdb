
//some set of macros for better testing

#ifndef TESTS_INIT

#include "CCDB/Console.h"
#include "CCDB/Helpers/StopWatch.h"

using namespace std;
using namespace ccdb;

extern Console gConsole;
extern std::string gConnectionString;
//must be called once per function that performs tests
#define TESTS_INIT(title) bool testtmp; bool testSetpsPassed;gConsole.WriteLine(); gConsole.WriteLine(Console::cBrightYellow, (title)); gConsole.WriteLine();

//render test title
#define TITLE(title) gConsole.Write("%-50.50s",(title));

//Do tests and leave function
#define TEST(condition) testSetpsPassed = testtmp = (condition); gConsole.PrintCondition(testtmp); if(!testtmp) return false;

//Do tests and NOT leave function
#define TEST_STEP(condition) testtmp = (condition); testSetpsPassed = testSetpsPassed && testtmp; gConsole.PrintCondition(testtmp);

//"link" to objects that test is passed
#define TEST_PASSED testSetpsPassed

//"link" to objects that last test is passed
#define STEP_PASSED testtmp

//must be called once per function that performs tests
#define BENCHMARK_INIT(title) Console gConsole; StopWatch stopwatch; gConsole.WriteLine(Console::cBrightYellow, (title)); gConsole.WriteLine();

//must be called once per function that performs tests
#define BENCHMARK_START(title) gConsole.WriteLine(Console::cBrightWhite,"\n[ %s ]", (title)); stopwatch.Start();

//must be called once per function that performs tests
#define BENCHMARK_FINISH(title) stopwatch.Stop(); gConsole.WriteLine(Console::cBrightWhite, " %s %f", (title), stopwatch.GetDuration());

//"gets" test gConsole
#define CONSOLE gConsole

#ifndef WIN32
#define TESTS_CONENCTION_STRING "mysql://ccdb_user@127.0.0.1:3306 ccdb"
#else
#define TESTS_CONENCTION_STRING "mysql://ccdb_user@127.0.0.1:3306 ccdb"
#endif

#endif //#ifndef TESTS_INIT