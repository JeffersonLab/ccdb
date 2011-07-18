#ifndef benchmark_Providers_h__
#define benchmark_Providers_h__
#include "DConsole.h"
#include "DStopWatch.h"
#include "Providers/DMySQLDataProvider.h"
#include "Model/DAssignment.h"
#include "Tests/tests_macros.h"
#include "Model/DConstantsTypeTable.h"

bool benchmark_Providers()
{	
	DMySQLDataProvider *prov = new DMySQLDataProvider();
	if(!prov->Connect(gConnectionString)) return false;
	
	BENCHMARK_INIT("P R O V I D E R S   B E N C H M A R K S");
	
	BENCHMARK_START("Get assignment benchmark");
	DStopWatch queryTimer;
	time_t queriesTime=0;
	for(int i=0; i<1000; i++)
	{
		//if(i%100==0) console.WriteLine("%d",i);
		DAssignment * asgn = prov->GetAssignmentShort(100,"/test/test_vars/test_table");
		delete asgn;
	}
	BENCHMARK_FINISH("1000 times GetAssignmentShort");
	/*
	vector<DConstantsTypeTable*> tables;
	BENCHMARK_START("Get tables from directory");
	for(int i=0; i<1000; i++)
	{
		//if(i%100==0) console.WriteLine("%d",i);
		if(!prov->GetConstantsTypeTables(tables, "/test/test_vars", false)) break;
	}
	BENCHMARK_FINISH("1000 times GetConstantsTypeTables");
	*/
	delete prov;

	return true;
}
#endif // benchmark_Providers_h__