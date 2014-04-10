#ifndef test_ModelObjects_h__
#define test_ModelObjects_h__

#include "Tests/catch.hpp"

//Disable posix warning on getch()
#pragma warning(disable : 4800)

#include "CCDB/Console.h"
#include "CCDB/Helpers/StringUtils.h"
#include "CCDB/Helpers/WorkUtils.h"
#include "CCDB/Model/Directory.h"
#include "CCDB/Model/Assignment.h"
#include "CCDB/Model/RunRange.h"
#include "CCDB/Model/Variation.h"
#include "CCDB/Model/ConstantsTypeColumn.h"
#include "CCDB/Model/ConstantsTypeTable.h"

using namespace std;
using namespace ccdb;

TEST_CASE("CCDB/ModelObjects","ModelObjects tests")
{
	//Connection

	StoredObject *ptr;
	
	ptr = new Assignment(NULL, NULL);
	REQUIRE(ptr!=NULL);
		
	ptr =  new RunRange(NULL, NULL);
	REQUIRE(ptr!=NULL);

	
	//	ptr = new DEventRange(NULL, false);
	//REQUIRE(ptr);

	ptr = new Variation(NULL, NULL);
	REQUIRE(ptr);

	ptr = new Directory(NULL, NULL);
	REQUIRE(ptr);

	ptr = new ConstantsTypeTable(NULL, NULL);
	REQUIRE(ptr);
	
    ptr = new ConstantsTypeColumn(NULL, NULL);
	REQUIRE(ptr);

	//TODO more complicated tests with a - benchmark, b - check for memory management
};
#endif
