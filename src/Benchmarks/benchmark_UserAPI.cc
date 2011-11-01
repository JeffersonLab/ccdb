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
#ifdef WIN32
#include "winpthreads.h"
#else //posix
#include <pthread.h>
#endif

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

    BENCHMARK_START("20000 plain read of /test/test_vars/test_table");
    for (int i=0; i<20000; i++)
    {
        calib->GetCalib(tabledValues, "/test/test_vars/test_table");
    }
    BENCHMARK_FINISH("20000 plain reads in ");

    return true;
}

typedef struct 
{
    int id;
} parm;

void *hello(void *arg)
{
    parm *p=(parm *)arg;
    BENCHMARK_INIT();

    vector<vector<string> > tabledValues;
    MySQLCalibration *calib = new MySQLCalibration(100);
    if(!calib->Connect(TESTS_CONENCTION_STRING)) return NULL;

    BENCHMARK_START("1200 plain read of /test/test_vars/test_table");
    for (int i=0; i<1200; i++)
    {
        calib->GetCalib(tabledValues, "/test/test_vars/test_table");
    }
    BENCHMARK_FINISH("1200 plain reads in ");
    return (NULL);
}


bool banchmark_UserAPIMultithread()
{
    bool result;
    pthread_t *threads;
    pthread_attr_t pthread_custom_attr;
    parm *p;

    int n = 8;
    int i =0; 
    BENCHMARK_INIT();
    BENCHMARK_START("Total is 10000 plain read of /test/test_vars/test_table");
    threads = (pthread_t *) malloc (n*sizeof(*threads));
    pthread_attr_init(&pthread_custom_attr);

    p=(parm *)malloc(sizeof(parm)*n);
    /* Start up thread */

    for (i=0; i<n; i++)
    {
        p[i].id=i;
        pthread_create(&threads[i], &pthread_custom_attr, hello, (void *)(p+i));
    }

    /* Synchronize the completion of each thread. */

    for (i=0; i<n; i++)
    {
        pthread_join(threads[i],NULL);
    }
    free(p);
    BENCHMARK_FINISH("Total. 10000 plain reads in ");
    return true;
}

bool benchmark_AllHallDConstants()
{
    bool result;

    BENCHMARK_INIT();

  
    MySQLCalibration *calib = new MySQLCalibration(100);
    if(!calib->Connect(TESTS_CONENCTION_STRING)) return false;
    vector<string> namepathes;
    calib->GetListOfNamepaths(namepathes);

    vector<vector<string> > tabledValues;
    long valuesCount = 0;
    BENCHMARK_START("20000 plain read of /test/test_vars/test_table");
    for (int i=0; i<namepathes.size(); i++)
    {
        calib->GetCalib(tabledValues, namepathes[i]);
        if(tabledValues.size()>0)
        {
            valuesCount+=tabledValues.size() * tabledValues[0].size();
        }
    }
    cout<<"totas constants  "<<valuesCount<<endl;
    BENCHMARK_FINISH("20000 plain reads in ");

    return true;
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