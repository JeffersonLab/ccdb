#ifndef test_ModelObjects_h__
#define test_ModelObjects_h__
//Disable posix warning on getch()
#pragma warning(disable : 4800)
#include "Tests/tests_macros.h"
#include "CCDB/Console.h"
#include "CCDB/Helpers/StringUtils.h"
#include "CCDB/Providers/MySQLDataProvider.h"
#include "CCDB/Model/Directory.h"
#include "CCDB/Helpers/WorkUtils.h"
#include "Model/DAssignment.h"
#include "Model/DRunRange.h"
#include "Model/Variation.h"
#include "Model/DConstantsTypeColumn.h"
#include "Model/DConstantsTypeTable.h"

using namespace std;
using namespace ccdb;

bool test_ModelObjects()
{
	TESTS_INIT(" ---  T E S T S    M o d e l   O b j e c t s --- ")

	//Connection
	gConsole.WriteLine(Console::cBrightWhite, "[ Creation ]");
	gConsole.WriteLine("Look for crashes");
	StoredObject *ptr;
	
	ptr = new Assignment(NULL, NULL);
	TITLE("DAssignment")  TEST(ptr!=NULL);
		
	ptr =  new RunRange(NULL, NULL);
	TITLE("DRunRange")  TEST(ptr!=NULL);

	
	//	ptr = new DEventRange(NULL, false);
	//TITLE("DEventRange") TEST(ptr);

	ptr = new Variation(NULL, NULL);
	TITLE("DVariation") TEST(ptr);

	ptr = new Directory(NULL, NULL);
	TITLE("DDirectory") TEST(ptr);

	ptr = new ConstantsTypeTable(NULL, NULL);
	TITLE("DConstantsTypeTable") TEST(ptr);
	
    ptr = new ConstantsTypeColumn(NULL, NULL);
	TITLE("DConstantsTypeColumn")	TEST(ptr);

	//TODO more complicated tests with a - benchmark, b - check for memory management

	return true;
};
#endif