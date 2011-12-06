//Disable posix warning on getch()
#pragma warning(disable : 4996)

#include <iostream>

#ifdef WIN32
#include <conio.h>
#include <windows.h>
#endif

#ifdef WIN32
#include <winsock.h>
#endif


using namespace std;

//#include "tests.h"
#include "Web/HttpContext.h"
using namespace ccdb;

bool benchmark_Providers();
void PrintHelp();

std::string gConnectionString;

int main (int argc,char *argv[])
{
	//cout<<"Web is web, pa pa, parara"<<endl;
	HttpContext * context = HttpContext::Instance();
	context->ProcessRequest();
}