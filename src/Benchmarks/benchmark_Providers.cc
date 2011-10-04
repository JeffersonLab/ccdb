#ifndef benchmark_Providers_h__
#define benchmark_Providers_h__

#include "CCDB/Console.h"
#include "CCDB/Helpers/StopWatch.h"
#include "CCDB/Providers/MySQLDataProvider.h"
#include "CCDB/Model/Assignment.h"
#include "CCDB/Model/ConstantsTypeTable.h"

#include "Tests/tests_macros.h"


bool benchmark_Providers()
{	
	MySQLDataProvider *prov = new MySQLDataProvider();
	if(!prov->Connect(gConnectionString)) return false;
	
	BENCHMARK_INIT("P R O V I D E R S   B E N C H M A R K S");
	
	BENCHMARK_START("Get assignment benchmark");
	StopWatch queryTimer;
	time_t queriesTime=0;
	for(int i=0; i<1000; i++)
	{
		//if(i%100==0) console.WriteLine("%d",i);
		Assignment * asgn = prov->GetAssignmentShort(100,"/test/test_vars/test_table");
		delete asgn;
	}
	BENCHMARK_FINISH("1000 times GetAssignmentShort");
	/*
	vector<ConstantsTypeTable*> tables;
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