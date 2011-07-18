#include "UserAPI/DCalibration.h"
#include "UserAPI/DCCDBGlobalMutex.h"
#include "Providers/DMySQLDataProvider.h"
#include "DPathUtils.h"


#include <stdexcept>
#include <assert.h>


namespace ccdb
{

//______________________________________________________________________________
DCalibration::DCalibration()
{
    //Constructor 

    mProvider = NULL;
    mProviderIsLocked = false; //by default we assume that we own the provider
    mDefaultRun = 0;
    mDefaultVariation = "default";
}


//______________________________________________________________________________
DCalibration::DCalibration(int defaultRun, string defaultVariation/*="default"*/ )
{	
    //Constructor 

	mDefaultRun = defaultRun;
	mDefaultVariation = defaultVariation;
    mProvider = NULL;
    mProviderIsLocked = false; //by default we assume that we own the provider
}


//______________________________________________________________________________
DCalibration::~DCalibration()
{
    //Destructor

    if(!mProviderIsLocked && mProvider!=NULL) delete mProvider;
}


//______________________________________________________________________________
void DCalibration::UseProvider( DDataProvider * provider, bool lockProvider/*=true*/ )
{
    // set provider to use. 
    //if lockProvider==true, than @see Connect, @see Disconnect and @see SetConnectionString 
    //will not affect connection of provider. The provider will not be deleted in destruction. 
    Lock();
	mProvider = provider;
	mProviderIsLocked = lockProvider;
    Unlock();
}


//______________________________________________________________________________
bool DCalibration::GetCalib( vector< map<string, string> > &values, const string & namepath )
{
     /** @brief Get constants by namepath
     * 
     * This version of function fills values as a Table, 
     * vector<map<string, string>> - is vector of rows, each row is a map<header_name, string_cell_value>
     *
     * Namepath is usually is just the data path, like 
     * /path/to/data
     * but the full form of request is 
     * /path/to/data:run:variation:time
     * request might be shortened. One may skip 
     * /path/to/data - just path to date, no run, variation and timestamp specified
     * /path/to/data::mc - no run or date specified.
     * /path/to/data:::2029 - only path and date
     * 
     * 
	 * @parameter [out] values - vector of rows, each row is a map<header_name, string_cell_value>
	 * @parameter [in]  namepath - data path
	 * @return true if constants were found and filled. false if namepath was not found. raises std::logic_error if any other error acured.
	 */
    
    DAssignment* assignment = GetAssignment(namepath);
    if(assignment == NULL) return false; //TODO possibly exception throwing?

    //Get data
    assert(values.empty());
    assignment->GetMappedData(values);

    //check data, get columns 
    if(values.size() == 0){
        throw std::logic_error("DMySQLCalibration::GetCalib( vector< map<string, string> >&, const string&). Data has no rows. Zero rows are not supposed to be.");
    }
}


//______________________________________________________________________________
bool DCalibration::GetCalib( vector< map<string, double> > &values, const string & namepath )
{
    //read values

    //TODO right now the function works through copy. 
    //one needs to find out, maybe it needs to be reimplemented
    
    vector<map<string, string> > rawValues;
    try
    {
        if(!GetCalib(rawValues, namepath)) return false;
    }
    catch (std::exception &)
    {
    	throw;
    }

    assert(values.empty());
    
    int rowsNum = rawValues.size();
    int columnsNum = rawValues[0].size(); //rawTableValues[0] - size was checked in GetCalib

    values.resize(rawValues.size());

    //compose values
    for (int rowIter = 0; rowIter < rowsNum; rowIter++)
    {
        map<string, string>::iterator iter;
        for ( iter=rawValues[rowIter].begin() ; iter != rawValues[rowIter].end(); iter++ )
        {
            bool parseResult;
            double tmpVal = DStringUtils::ParseDouble(iter->second, &parseResult);
            if(!parseResult) throw logic_error("Error parsing double in DCalibration::GetCalib( vector< map<string, double> > &, const string &)");
            values[rowIter][iter->first] = tmpVal;
        }
    }

    return true;
}


//______________________________________________________________________________
bool DCalibration::GetCalib( vector< map<string, int> > &values, const string & namepath )
{
    //TODO right now the function works through copy. 
    //one needs to find out, maybe it needs to be reimplemented

    vector<map<string, string> > rawValues;
    try
    {
        if(!GetCalib(rawValues, namepath)) return false;
    }
    catch (std::exception &)
    {
        throw;
    }

    assert(values.empty());

    int rowsNum = rawValues.size();
    int columnsNum = rawValues[0].size(); //rawTableValues[0] - size was checked in GetCalib

    values.resize(rawValues.size());

    //compose values
    for (int rowIter = 0; rowIter < rowsNum; rowIter++)
    {
        map<string, string>::iterator iter;
        for ( iter=rawValues[rowIter].begin() ; iter != rawValues[rowIter].end(); iter++ )
        {
            bool parseResult;
            int intlVal = DStringUtils::ParseInt(iter->second, &parseResult);
            if(!parseResult) throw logic_error("Error parsing double in DCalibration::GetCalib( vector< map<string, int> > &, const string &)");
            values[rowIter][iter->first] = intlVal;
        }
    }

    return true;
}


//______________________________________________________________________________
bool DCalibration::GetCalib( vector< vector<string> > &values, const string & namepath )
{
    /** @brief Get constants by namepath
     * 
     * this version of function fills values as a table represented as
     * vector< vector<string> > = vector of rows where each row is a vector of cells
     *
     * @parameter [out] values - vector of rows, each row is a map<header_name, string_cell_value>
     * @parameter [in]  namepath - data path
     * @return true if constants were found and filled. false if namepath was not found. raises std::logic_error if any other error acured.
     */
    
    DAssignment* assigment = GetAssignment(namepath);
    
    if(assigment == NULL) 
    {
        //TODO possibly exception throwing?
        return false;
    }
        
    assigment->GetData(values);
    
    delete assigment;

    return true;
}


//______________________________________________________________________________
bool DCalibration::GetCalib( vector< vector<double> > &values, const string & namepath )
{
    //TODO right now the function works through copy. 
    //one needs to find out, maybe it needs to be reimplemented

    vector< vector<string> > rawValues;
    try
    {
        if(!GetCalib(rawValues, namepath)) return false;
    }
    catch (std::exception &)
    {
        throw;
    }

    assert(values.empty());

    int rowsNum = rawValues.size();
    int columnsNum = rawValues[0].size(); //rawTableValues[0] - size was checked in GetCalib

    values.resize(rawValues.size());

    //compose values
    for (int rowIter = 0; rowIter < rowsNum; rowIter++)
    {   
        for (int columnsIter = 0; columnsIter < columnsNum; columnsIter++)
        {
            bool parseResult;
            double tmpVal = DStringUtils::ParseDouble(rawValues[rowIter][columnsIter], &parseResult);
            if(!parseResult) throw logic_error("Error parsing double in DCalibration::GetCalib( vector< vector<double> > &, const string &)");
            values[rowIter].push_back(tmpVal);
        }
    }

    return true;
}


//______________________________________________________________________________
bool DCalibration::GetCalib( vector< vector<int> > &values, const string & namepath )
{
    vector< vector<string> > rawValues;
    try
    {
        if(!GetCalib(rawValues, namepath)) return false;
    }
    catch (std::exception &)
    {
        throw;
    }

    assert(values.empty());

    int rowsNum = rawValues.size();
    int columnsNum = rawValues[0].size(); //rawTableValues[0] - size was checked in GetCalib

    values.resize(rawValues.size());

    //compose values
    for (int rowIter = 0; rowIter < rowsNum; rowIter++)
    {   
        for (int columnsIter = 0; columnsIter < columnsNum; columnsIter++)
        {
            bool parseResult;
            int tmpVal = DStringUtils::ParseInt(rawValues[rowIter][columnsIter], &parseResult);
            if(!parseResult) throw logic_error("Error parsing double in DCalibration::GetCalib( vector< vector<int> > &, const string &)");
            values[rowIter].push_back(tmpVal);
        }
    }

    return true;
}


//______________________________________________________________________________
bool DCalibration::GetCalib( map<string, string> &values, const string & namepath )
{
     /** @brief Get constants by namepath
     * 
     * this version of function fills values as one row
     * where map<header_name, string_cell_value>
     *
     * @parameter [out] values - as  map<header_name, string_cell_value>
     * @parameter [in]  namepath - data path
     * @return true if constants were found and filled. false if namepath was not found. raises std::logic_error if any other error acured.
     */
    
    DAssignment* assignment = GetAssignment(namepath);
    

    if(assignment == NULL) 
    {
        //TODO possibly exception throwing?
        return false;
    }

    //Get data
    vector< vector<string> > rawTableValues;
    assignment->GetData(rawTableValues);

    //check data a little...
    if(rawTableValues.size() == 0)
    {
        throw std::logic_error("DMySQLCalibration::GetCalib( map<string, string>&, const string&). Data has no rows. Zero rows are not supposed to be.");
    }

    //TODO should we check that rawTableValues have only one row?
    //now we take only first row of table
    vector<string> rawValues = rawTableValues[0];

    //get table
    DConstantsTypeTable *table = assignment->GetTypeTable(); 
    assert(table != NULL); //It is DataProvider logic, that assignments have some table information

    //get columns names
    vector<string> columnNames = table->GetColumnNames();
    int columnsNum = columnNames.size();
    assert(columnsNum == rawValues.size());

    //VALUES VALIDATION
    assert(values.empty());
    
    //compose values
    for (int i=0; i<columnsNum; i++)
    {
        values[columnNames[i]] = rawValues[i];
    }
    
    //finishing
    delete assignment;
    return true;
}


//______________________________________________________________________________
bool DCalibration::GetCalib( map<string, double> &values, const string & namepath )
{
    map<string, string> rawValues;
    try
    {
        if(!GetCalib(rawValues, namepath)) return false;
    }
    catch (std::exception &)
    {
        throw;
    }

    assert(values.empty());
    
    //compose values
    map<string, string>::iterator iter;
    for ( iter=rawValues.begin() ; iter != rawValues.end(); iter++ )
    {
        bool parseResult;
        double tmpVal = DStringUtils::ParseDouble(iter->second, &parseResult);
        if(!parseResult) throw logic_error("Error parsing double in DCalibration::GetCalib(  map<string, double> &, const string &)");
        values[iter->first] = tmpVal;
    }

    return true;
}


//______________________________________________________________________________
bool DCalibration::GetCalib( map<string, int> &values, const string & namepath )
{
    //TODO right now the function works through copy. 
    //one needs to find out, maybe it needs to be reimplemented

    map<string, string> rawValues;
    try
    {
        if(!GetCalib(rawValues, namepath)) return false;
    }
    catch (std::exception &)
    {
        throw;
    }

    assert(values.empty());

    //compose values
    map<string, string>::iterator iter;
    for ( iter=rawValues.begin() ; iter != rawValues.end(); iter++ )
    {
        bool parseResult;
        int tmpVal = DStringUtils::ParseInt(iter->second, &parseResult);
        if(!parseResult) throw logic_error("Error parsing double in DCalibration::GetCalib(  map<string, int> &, const string &)");
        values[iter->first] = tmpVal;
    }

    return true;
}


//______________________________________________________________________________
bool DCalibration::GetCalib( vector<string> &values, const string & namepath )
{
    /** @brief Get constants by namepath
     * 
     * this version of function fills values as one row as vector<string_values>
     * 
     * @parameter [out] values - as vector<string_values>
     * @parameter [in]  namepath - data path
     * @return true if constants were found and filled. false if namepath was not found. raises std::logic_error if any other error acured.
     */

    
    DAssignment* assignment = GetAssignment(namepath);
    
    if(assignment == NULL) return false; //TODO possibly exception throwing?

    //Get data
    assert(values.empty());
    assignment->GetVectorData(values);

    //check data and check that the user will get what he ment...
    if(values.size() == 0)
        throw std::logic_error("DMySQLCalibration::GetCalib(vector<string> &, const string &). Data has no rows. Zero rows are not supposed to be.");

    if(values.size() != assignment->GetTypeTable()->GetNColumns())
        throw std::logic_error("DMySQLCalibration::GetCalib(vector<string> &, const string &). logic_error: Calling of single row vector<dataType> version of GetCalib method on dataset that has more than one rows. Use GetCalib vector<vector<dataType> > instead.");
}


//______________________________________________________________________________
bool DCalibration::GetCalib( vector<double> &values, const string & namepath )
{
    vector<string> rawValues;
    try
    {
        if(!GetCalib(rawValues, namepath)) return false;
    }
    catch (std::exception &)
    {
        throw;
    }

    assert(values.empty());
    int columnsNum = rawValues.size(); //rawTableValues[0] - size was checked in GetCalib

    values.resize(rawValues.size());

    //compose values
    for (int columnsIter = 0; columnsIter < columnsNum; columnsIter++)
    {
        bool parseResult;
        double tmpVal = DStringUtils::ParseDouble(rawValues[columnsIter], &parseResult);
        if(!parseResult) throw logic_error("Error parsing double in DCalibration::GetCalib( vector< vector<double> > &, const string &)");
        values.push_back(tmpVal);
    }
    return true;
}


//______________________________________________________________________________
bool DCalibration::GetCalib( vector<int> &values, const string & namepath )
{
    vector<string> rawValues;
    try
    {
        if(!GetCalib(rawValues, namepath)) return false;
    }
    catch (std::exception &)
    {
        throw;
    }

    assert(values.empty());
    int columnsNum = rawValues.size(); //rawTableValues[0] - size was checked in GetCalib

    values.resize(rawValues.size());

    //compose values
    for (int columnsIter = 0; columnsIter < columnsNum; columnsIter++)
    {
        bool parseResult;
        int tmpVal = DStringUtils::ParseInt(rawValues[columnsIter], &parseResult);
        if(!parseResult) throw logic_error("Error parsing double in DCalibration::GetCalib( vector< vector<int> > &, const string &)");
        values.push_back(tmpVal);
    }
    return true;
}

//______________________________________________________________________________
string DCalibration::GetConnectionString() const
{
    //
    if (mProvider!=NULL) return mProvider->GetConnectionString();
    return string();
}


//______________________________________________________________________________
DAssignment * DCalibration::GetAssignment( const string& namepath )
{
    /** @brief Gets the assignment from provider using namepath
     * namepath is the common ccdb request; @see GetCalib
     *
     * @remark the function is threadsafe
     * 
     * @parameter [in] namepath -  full namepath is /path/to/data:run:variation:time but usually it is only /path/to/data
     * @return   DAssignment *
     */

    DParseRequestResult result = DPathUtils::ParseRequest(namepath);
    string variation = (result.WasParsedVariation ? result.Variation : mDefaultVariation);
    int run  = (result.WasParsedRunNumber ? result.RunNumber : mDefaultRun);
    DAssignment* assigment = NULL;
    Lock();
    if(result.WasParsedTime)
    {   
        assigment = mProvider->GetAssignmentShort(run, result.Path, result.Time, variation);
    }
    else
    {
        assigment = mProvider->GetAssignmentShort(run, result.Path, variation);
    }
    Unlock();
    return assigment;

}


//______________________________________________________________________________
void DCalibration::Lock()
{
    //Thread mutex lock for multithreaded operations
    DCCDBGlobalMutex::Instance()->ReadConstantsLock();
}


//______________________________________________________________________________
void DCalibration::Unlock()
{
    //Thread mutex Unlock lock for multithreaded operations
    DCCDBGlobalMutex::Instance()->ReadConstantsRelease();
}
}

