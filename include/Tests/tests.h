// This is not a formal unit tests, but a very close thing
// One can create tests for each module (class) as:
// test_<module name>.cpp
// and create a function in it:
// bool test_<module name>() // that tests this module and returns bool if module is OK
// Place the function prototype here and test it in RunTests() function


#ifndef tests_h__
#define tests_h__

//function pointer typedef:
typedef bool (*test_function)();


class UnitTests
{
public:
    UnitTests()
    {
        mCurrentIndex = 0;
    }

    void AddTest(test_function func)
    {
        mTests[mCurrentIndex] = func;
        mCurrentIndex++;
    }

private:
    int mCurrentIndex;
    test_function mTests[1000];
};
/*****************************************************
*                   T E S T S                        *
*****************************************************/

bool test_Console();                //A Test of Console class
bool test_ModelObjects();            //A test of model creation
bool test_DMySQLDataProvider();      //A test of MySQL Provider
bool test_DMySQLDataProvider_TypeTables();      //tables work
bool test_DMySQLDataProvider_RunRanges();       //tun ranges
bool test_DMySQLDataProvider_Variations();      //variations work
bool test_DMySQLDataProvider_Assignments();     //assignments tests
bool test_StringUtils();                       //string utils
bool test_PathUtils();                         //test or parsing requests
bool test_UserAPI();                            //test of user api functions and objects
/**
 * Run unit tests
 */
bool RunTests()
{
    bool result = true;
    result = result && test_Console();             //disabled, too many text
    result = result && test_StringUtils();
    result = result && test_PathUtils();
    result = result && test_ModelObjects();         //A test of model creation
    result = result && test_DMySQLDataProvider(); 
    result = result && test_DMySQLDataProvider_TypeTables();
    result = result && test_DMySQLDataProvider_RunRanges();
    result = result && test_DMySQLDataProvider_Variations();
    result = result && test_DMySQLDataProvider_Assignments();
    result = result && test_UserAPI();
    return result;
}

/*****************************************************
*                B E N C H M A R K S                 *
*****************************************************/

bool benchmark_Providers();             //providers benchmark
bool benchmark_PreparedStatements();    //prepared statements benchmark

/**
 * Run various benchmarks
 */
bool RunBenchmarks()
{
    bool result = true;
    result = result && benchmark_Providers();       //providers benchmark
    result = result && benchmark_PreparedStatements();

    return result;
}

#endif // tests_h__