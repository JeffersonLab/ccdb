// This is not a formal unit tests config


#ifndef bencjmarks_h__
#define bencjmarks_h__

#ifndef WIN32
#define TESTS_CONENCTION_STRING "mysql://ccdb_user@127.0.0.1:3306 ccdb"
#else
#define TESTS_CONENCTION_STRING "mysql://ccdb_user@127.0.0.1:3306 ccdb"
#endif

#include "CCDB/Console.h"
#include "CCDB/Helpers/StopWatch.h"

using namespace std;
using namespace ccdb;

extern Console gConsole;
extern std::string gConnectionString;


//must be called once per function that performs tests
#define BENCHMARK_INIT() StopWatch stopwatch; 

//must be called once per function that performs tests
#define BENCHMARK_START(title) gConsole.WriteLine(Console::cBrightBlue,"\n[ %s ]", (title)); stopwatch.Start();

//must be called once per function that performs tests
#define BENCHMARK_FINISH(title) stopwatch.Stop(); gConsole.WriteLine(Console::cGreen, " %s %f", (title), stopwatch.GetDuration());

#endif // bencjmarks_h__