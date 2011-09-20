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
#include "Model/DDirectory.h"
#include "Providers/DMySQLDataProvider.h"
#include "DConsole.h"
#include "DWorkUtils.h"
#include "DStopWatch.h"
#include "DLog.h"
#include "Web/DHttpContext.h"
using namespace ccdb;

bool benchmark_Providers();
void PrintHelp();

DConsole gConsole;
std::string gConnectionString;

int main (int argc,char *argv[])
{
	cout<<"Web is web, pa pa, parara"<<endl;
	DHttpContext * context = DHttpContext::Instance();
	context->ProcessRequest();
}