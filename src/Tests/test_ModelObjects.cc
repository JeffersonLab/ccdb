#ifndef test_ModelObjects_h__
#define test_ModelObjects_h__
//Disable posix warning on getch()
#pragma warning(disable : 4800)
#include "Tests/tests_macros.h"
#include "DConsole.h"
#include "DStringUtils.h"
#include "Providers/DMySQLDataProvider.h"
#include "Model/DDirectory.h"
#include "DWorkUtils.h"
#include "Model/DAssignment.h"
#include "Model/DRunRange.h"
#include "Model/DVariation.h"
#include "Model/DConstantsTypeColumn.h"
#include "Model/DConstantsTypeTable.h"

using namespace std;
using namespace ccdb;

bool test_ModelObjects()
{
	TESTS_INIT(" ---  T E S T S    M o d e l   O b j e c t s --- ")

	//Connection
	gConsole.WriteLine(DConsole::cBrightWhite, "[ Creation ]");
	gConsole.WriteLine("Look for crashes");
	DStoredObject *ptr;
	
	ptr = new DAssignment(NULL, NULL);
	TITLE("DAssignment")  TEST(ptr!=NULL);
		
	ptr =  new DRunRange(NULL, NULL);
	TITLE("DRunRange")  TEST(ptr!=NULL);

	
	//	ptr = new DEventRange(NULL, false);
	//TITLE("DEventRange") TEST(ptr);

	ptr = new DVariation(NULL, NULL);
	TITLE("DVariation") TEST(ptr);

	ptr = new DDirectory(NULL, NULL);
	TITLE("DDirectory") TEST(ptr);

	ptr = new DConstantsTypeTable(NULL, NULL);
	TITLE("DConstantsTypeTable") TEST(ptr);
	
    ptr = new DConstantsTypeColumn(NULL, NULL);
	TITLE("DConstantsTypeColumn")	TEST(ptr);

	//TODO more complicated tests with a - benchmark, b - check for memory management

	return true;
};
#endif