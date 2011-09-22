//============================================================================
// Name        : workbench.cpp
// Author      : Dmitry A Romanov
//============================================================================

//Disable posix warning on getch()
#pragma warning(disable : 4996)

#include <iostream>

/* vfprintf example */
#include <stdio.h>
#include <stdarg.h>
#ifdef WIN32
#include <conio.h>
#include <windows.h>
#endif

#include <cstdio>
#include <iostream>
#include <mysql.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <map>
#include <algorithm>
#include <iostream>
#include <vector>
#include <string>
#ifdef WIN32
#include <winsock.h>
#endif

#include <mysql.h>
using namespace std;

//#include "tests.h"
#include "CCDB/Model/Directory.h"
#include "CCDB/Providers/MySQLDataProvider.h"
#include "Tests/tests.h"
#include "CCDB/Console.h"
#include "CCDB/Helpers/WorkUtils.h"
#include "CCDB/Helpers/StopWatch.h"
#include "Tests/tests_macros.h"
#include "DLog.h"
#include "Web/DHttpContext.h"
using namespace ccdb;

void PrintHelp();

#include "Tests/tests_macros.h"
#include "Model/DConstantsTypeTable.h"


Console gConsole;
std::string gConnectionString;
int main (int argc,char *argv[])
{

    //some setup
    gConnectionString = TESTS_CONENCTION_STRING;
    gConsole.SetUseColors(true);
    DLog::SetUseColors(true);
    bool runTests = false;
    bool runBenchmarks = false;
    bool runPause = false;
    
    
    // copy program arguments into vector
    vector<string> args;
    for (int i=1;i<argc;i++) args.push_back(argv[i]);
    
    // parse arguments    
    for (int i=0;i<args.size();i++) 
    {
        if(args[i]=="--nocolors"   || args[i]=="-c") { gConsole.SetUseColors(false); DLog::SetUseColors(false);}
        if(args[i]=="--tests"      || args[i]=="-t") runTests = true;
        if(args[i]=="--benchmarks" || args[i]=="-b") runBenchmarks = true;
        if(args[i]=="--pause"      || args[i]=="-p") runPause = true;
        if(args[i]=="--help"       || args[i]=="-h") PrintHelp();
        if(args[i]=="--verbose"    || args[i]=="-v") DLog::SetLevel(4);
        if(args[i]=="--server"     || args[i]=="-s") 
        {
            if(i>= (args.size()-1)) PrintHelp(); //check if we have argument after
            i++;
            gConnectionString = args[i];
        }
    }
    
    //what to do?
    if(args.size()==0) PrintHelp();
    
    //benchmarks?
    if(runBenchmarks)
    {
        RunBenchmarks();
        gConsole.WriteLine(Console::cBrightGreen, "\n>>> Benchmarks done <<<");
    }

    //tests?
    if(runTests)
    {
        RunTests();
        gConsole.WriteLine(Console::cBrightGreen, "\n>>> Tests done <<<");
    }

    //pause?
    if(runPause)
    {
        string x;
        cout<<endl<<"paused"<<endl;
        cin>>x;
    }
    
    return 0;
}

void PrintHelp()
{
    gConsole.WriteLine("Test and benchmarking of CCDB database");
    gConsole.WriteLine("   --nocolors   or -c  disables colors");
    gConsole.WriteLine("   --tests      or -t  run tests");
    gConsole.WriteLine("   --benchmarks or -b  run benchmarks");
    gConsole.WriteLine("   --pause      or -p  pause at the end");
    gConsole.WriteLine("   --help       or -h  shows this help");
    gConsole.WriteLine("   --server     or -s  connection string like mysql://user:pwd@server");
    gConsole.WriteLine("   --verbose    or -v  shows additional (probably debug) information");
}
