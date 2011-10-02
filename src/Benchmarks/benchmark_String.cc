#pragma warning(disable:4800)
#include "Benchmarks/benchmarks.h"

#include "CCDB/Console.h"
#include "CCDB/Helpers/StringUtils.h"
#include "CCDB/Helpers/StopWatch.h"
#include <sstream>

using namespace std;
using namespace ccdb;

/** 
 * @brief This benchmark should test, what is slowing down strings
 */
bool benchmark_String()
{
	bool result;
	
    BENCHMARK_INIT();
    
  
    
    //Using StringUtils
    BENCHMARK_START("100000 Call of StringUtils::Format");
    for (int i=0; i<100000; i++)
    {
        string query=
            "SELECT `assignments`.`id` AS `asId`, "
            "`constantSets`.`vault` AS `blob` "
            "FROM  `assignments` "
            "USE INDEX (id_UNIQUE) "
            "INNER JOIN `runRanges` ON `assignments`.`runRangeId`= `runRanges`.`id` "
            "INNER JOIN `constantSets` ON `assignments`.`constantSetId` = `constantSets`.`id` "
            "WHERE  `runRanges`.`runMin` <= '%i' "
            "AND `runRanges`.`runMax` >= '%i' "
            "AND `assignments`.`variationId`= '%i' "
            "AND `constantSets`.`constantTypeId` ='%i' "
            "ORDER BY `assignments`.`id` DESC "
            "LIMIT 1 ";

        query=StringUtils::Format(query.c_str(), 1, 1, 1, 1);
    }
    BENCHMARK_FINISH("100000 Call of StringUtils::Format do in ");

    //Using string stream
    BENCHMARK_START("100000 of stringstream formatting");
    for (int i=0; i<100000; i++)
    {
          stringstream ss;
            ss<<"SELECT `assignments`.`id` AS `asId`, "
            "`constantSets`.`vault` AS `blob` "
            "FROM  `assignments` "
            "USE INDEX (id_UNIQUE) "
            "INNER JOIN `runRanges` ON `assignments`.`runRangeId`= `runRanges`.`id` "
            "INNER JOIN `constantSets` ON `assignments`.`constantSetId` = `constantSets`.`id` "
            "WHERE  `runRanges`.`runMin` <= '"<<1<<"' "
            "AND `runRanges`.`runMax` >= '"<<1<<"' "
            "AND `assignments`.`variationId`= '"<<1<<"' "
            "AND `constantSets`.`constantTypeId` ='"<<1<<"' "
            "ORDER BY `assignments`.`id` DESC "
            "LIMIT 1 ";
          string query = ss.str();
    }
    BENCHMARK_FINISH("100000 of stringstream formatting do in ");
    return true;
}
