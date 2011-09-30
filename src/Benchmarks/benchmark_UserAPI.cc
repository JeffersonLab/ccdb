#pragma warning(disable:4800)
#include "Benchmarks/benchmarks.h"

#include "CCDB/Console.h"
#include "CCDB/MySQLCalibration.h"
#include "CCDB/Providers/MySQLDataProvider.h"
#include "CCDB/Model/Directory.h"
#include "CCDB/Model/Variation.h"
#include "CCDB/Helpers/StringUtils.h"
#include "CCDB/Helpers/WorkUtils.h"
#include "CCDB/Helpers/StopWatch.h"

using namespace std;
using namespace ccdb;

//Next functions is for data printing
void test_UserAPI_PrintData(const vector<vector<string> > & data);
void test_UserAPI_PrintData(const vector<vector<double> > & data);
void test_UserAPI_PrintData(const vector<map<string,double> > & data);
void test_UserAPI_PrintData(const vector<int> & data);
void test_UserAPI_PrintData(const map<string,int> & data);

/** ********************************************************************* 
 * @brief Test of CCDB USER API work
 *
 * @return true if test passed
 */
bool benchmark_UserAPI()
{
	bool result;
	
    BENCHMARK_INIT();

    vector<vector<string> > tabledValues;
    MySQLCalibration *calib = new MySQLCalibration(100);
    if(!calib->Connect(TESTS_CONENCTION_STRING)) return false;

    BENCHMARK_START("10000 plain read of /test/test_vars/test_table");
    for (int i=0; i<10000; i++)
    {
        calib->GetCalib(tabledValues, "/test/test_vars/test_table");
    }
    BENCHMARK_FINISH("10000 plain reads in ");

    return true;
	////U S I N G   U S E R   A P I   D I R E C T L Y
	////----------------------------------------------------

 //   MySQLCalibration *calib = new MySQLCalibration(100);
 //   result = false;

 //   REQUIRE_NOTHROW(result = calib->Connect(TESTS_CONENCTION_STRING));
 //   REQUIRE(result);
 //   
 //   //get data as table of strings
 //   //----------------------------------------------------
 //   
 //   REQUIRE_NOTHROW(result = );
 //   REQUIRE(tabledValues.size()>0);
 //   REQUIRE(tabledValues.size()==2);
 //   REQUIRE(tabledValues[0].size()==3);

 //   
 //   //test of getting data without / in the beginning
 //   //----------------------------------------------------
 //   tabledValues.clear();
 //   REQUIRE_NOTHROW(result = calib->GetCalib(tabledValues, "test/test_vars/test_table"));
 //   REQUIRE(tabledValues.size()>0);
}

/*
//______________________________________________________________________________
void test_UserAPI_PrintData(const vector<vector<string> > & data)
{
    int rowsNum = data.size();
    int columnsNum = data[0].size(); //rawTableValues[0] - size was checked in GetCalib

    //print values
    for (int rowIter = 0; rowIter < rowsNum; rowIter++)
    {   
        for (int columnsIter = 0; columnsIter < columnsNum; columnsIter++)
        {
            gConsole.Write("|  %-9s ", data[rowIter][columnsIter].c_str());
        }
        gConsole.WriteLine("|");
    }
}

//______________________________________________________________________________
void test_UserAPI_PrintData(const vector<vector<double> > & data)
{
    int rowsNum = data.size();
    int columnsNum = data[0].size(); //rawTableValues[0] - size was checked in GetCalib

    //print values
    for (int rowIter = 0; rowIter < rowsNum; rowIter++)
    {   
        for (int columnsIter = 0; columnsIter < columnsNum; columnsIter++)
        {
            gConsole.Write("| %-9s ", StringUtils::Format("%.6d", data[rowIter][columnsIter]).c_str());
        }
        gConsole.WriteLine("|");
    }
}

//______________________________________________________________________________
void test_UserAPI_PrintData(const vector<map<string,double> > & data)
{
    int rowsNum = data.size();
    int columnsNum = data[0].size(); //rawTableValues[0] - size was checked in GetCalib

    //print values
    for (int rowIter = 0; rowIter < rowsNum; rowIter++)
    {   
        map<string,double>::const_iterator cell;
        const map<string,double> &row = data[rowIter];

        for (cell = row.begin(); cell!= row.end(); cell++)
        {
            gConsole.Write("| %-20s ", StringUtils::Format("%s : %.6d", cell->first.c_str(), cell->second).c_str());
        }
        gConsole.WriteLine("|");
    }
}

//______________________________________________________________________________
void test_UserAPI_PrintData(const vector<int> & data)
{
    //print values
    for (int columnsIter = 0; columnsIter < data.size(); columnsIter++)
    {
        gConsole.Write("| %-9s ", StringUtils::Format("%i", data[columnsIter]).c_str());
    }
    gConsole.WriteLine("|");
}

//______________________________________________________________________________
void test_UserAPI_PrintData(const map<string,int> & data)
{
    map<string,int>::const_iterator cell;
    const map<string,int> &row = data;

    for (cell = row.begin(); cell!= row.end(); cell++)
    {
        gConsole.Write("| %-20s ", StringUtils::Format("%s : %i", cell->first.c_str(), cell->second).c_str());
    }
    gConsole.WriteLine("|");
}
*/