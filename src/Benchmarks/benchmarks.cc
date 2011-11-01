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


using namespace std;

//#include "tests.h"
#include "CCDB/Console.h"
#include "CCDB/Log.h"
#include "Benchmarks/benchmarks.h"

using namespace ccdb;

void PrintHelp();

Console gConsole;
std::string gConnectionString;

bool benchmark_UserAPI();
//bool benchmark_Providers();             //providers benchmark
bool benchmark_PreparedStatements();    //prepared statements benchmark
bool banchmark_UserAPIMultithread();
bool benchmark_String();
bool benchmark_AllHallDConstants();
/**
 * Run various benchmarks
 */
bool RunBenchmarks()
{
    bool result = true;
    //result = result && benchmark_UserAPI();       //providers benchmark
    banchmark_UserAPIMultithread();
    //benchmark_AllHallDConstants();
    //benchmark_String();
  //  result = result && benchmark_Providers();       //providers benchmark
    //result = result && benchmark_PreparedStatements();

    return result;
}

int main (int argc,char *argv[])
{

    //some setup
    gConnectionString = TESTS_CONENCTION_STRING;
    gConsole.SetUseColors(true);
    Log::SetUseColors(true);
    bool runTests = false;
    bool runBenchmarks = false;
    bool runPause = false;
    
    
    // copy program arguments into vector
    vector<string> args;
    for (int i=1;i<argc;i++) args.push_back(argv[i]);
    
    // parse arguments    
    for (int i=0;i<args.size();i++) 
    {
        if(args[i]=="--nocolors"   || args[i]=="-c") { gConsole.SetUseColors(false); Log::SetUseColors(false);}
        if(args[i]=="--pause"      || args[i]=="-p") runPause = true;
        if(args[i]=="--help"       || args[i]=="-h") PrintHelp();
        if(args[i]=="--verbose"    || args[i]=="-v") Log::SetErrorLevel(4);
        if(args[i]=="--server"     || args[i]=="-s") 
        {
            if(i>= (args.size()-1)) PrintHelp(); //check if we have argument after
            i++;
            gConnectionString = args[i];
        }
    }
    
    //what to do?
    if(args.size()==0) PrintHelp();
  
    RunBenchmarks();
    
    return 0;
}

void PrintHelp()
{
    gConsole.WriteLine("Benchmarking for CCDB C++ API");
    gConsole.WriteLine("   --nocolors   or -c  disables colors");
    gConsole.WriteLine("   --pause      or -p  pause at the end");
    gConsole.WriteLine("   --help       or -h  shows this help");
    gConsole.WriteLine("   --server     or -s  connection string like mysql://user:pwd@server");
    gConsole.WriteLine("   --verbose    or -v  shows additional (probably debug) information");
}
