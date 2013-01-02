#include <stdexcept>
#include <assert.h>
#include <iostream>

#include "CCDB/Calibration.h"
#include "CCDB/GlobalMutex.h"
#include "CCDB/Providers/DataProvider.h"
#include "CCDB/Helpers/PathUtils.h"

using namespace std;

namespace ccdb
{

//______________________________________________________________________________
Calibration::Calibration()
{
    //Constructor 

    mProvider = NULL;
    mProviderIsLocked = false; //by default we assume that we own the provider
    mDefaultRun = 0;
	mDefaultTime = 0;
    mDefaultVariation = "default";
    mReadMutex = new PthreadMutex(new PthreadSyncObject());
}


//______________________________________________________________________________
Calibration::Calibration(int defaultRun, string defaultVariation/*="default"*/, time_t defaultTime/*=0*/ )
{	
    //Constructor 

	mDefaultRun = defaultRun;
	mDefaultVariation = defaultVariation;
	mDefaultTime = defaultTime;

    mProvider = NULL;
    mProviderIsLocked = false; //by default we assume that we own the provider
    PthreadSyncObject * x = NULL;
    x = new PthreadSyncObject();
    mReadMutex = new PthreadMutex(x);
}


//______________________________________________________________________________
Calibration::~Calibration()
{
    //Destructor

    if(!mProviderIsLocked && mProvider!=NULL) delete mProvider;
    if(mReadMutex) delete mReadMutex;
}


//______________________________________________________________________________
void Calibration::UseProvider( DataProvider * provider, bool lockProvider/*=true*/ )
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
bool Calibration::GetCalib( vector< map<string, string> > &values, const string & namepath )
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

    auto_ptr<Assignment> assignment(GetAssignment(namepath, true));
        
    if(!assignment.get()) 
    {       
        return false; //TODO possibly exception throwing?
    }

    //Get data
    
    assert(values.empty());
    
    assignment->GetMappedData(values);

    //check data, get columns 
    if(values.size() == 0){
        throw std::logic_error("Calibration::GetCalib( vector< map<string, string> >&, const string&). Data has no rows. Zero rows are not supposed to be.");
    }
    return true;
}


//______________________________________________________________________________
bool Calibration::GetCalib( vector< map<string, double> > &values, const string & namepath )
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
            double tmpVal = StringUtils::ParseDouble(iter->second, &parseResult);
            if(!parseResult) throw logic_error("Error parsing double in DCalibration::GetCalib( vector< map<string, double> > &, const string &)");
            values[rowIter][iter->first] = tmpVal;
        }
    }

    return true;
}


//______________________________________________________________________________
bool Calibration::GetCalib( vector< map<string, int> > &values, const string & namepath )
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
            int intlVal = StringUtils::ParseInt(iter->second, &parseResult);
            if(!parseResult) throw logic_error("Error parsing double in DCalibration::GetCalib( vector< map<string, int> > &, const string &)");
            values[rowIter][iter->first] = intlVal;
        }
    }

    return true;
}


//______________________________________________________________________________
bool Calibration::GetCalib( vector< vector<string> > &values, const string & namepath )
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
    
    Assignment* assignment = GetAssignment(namepath, false);
    
    if(assignment == NULL) 
    {
        //TODO possibly exception throwing?
        return false;
    }
   
    assignment->GetData(values);
        
    delete assignment;

    return true;
}


//______________________________________________________________________________
bool Calibration::GetCalib( vector< vector<double> > &values, const string & namepath )
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
            double tmpVal = StringUtils::ParseDouble(rawValues[rowIter][columnsIter], &parseResult);
            if(!parseResult) throw logic_error("Error parsing double in DCalibration::GetCalib( vector< vector<double> > &, const string &)");
            values[rowIter].push_back(tmpVal);
        }
    }

    return true;
}


//______________________________________________________________________________
bool Calibration::GetCalib( vector< vector<int> > &values, const string & namepath )
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
            int tmpVal = StringUtils::ParseInt(rawValues[rowIter][columnsIter], &parseResult);
            if(!parseResult) throw logic_error("Error parsing double in DCalibration::GetCalib( vector< vector<int> > &, const string &)");
            values[rowIter].push_back(tmpVal);
        }
    }

    return true;
}


//______________________________________________________________________________
bool Calibration::GetCalib( map<string, string> &values, const string & namepath )
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
    
    Assignment* assignment = GetAssignment(namepath, true);
    
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
        throw std::logic_error("Calibration::GetCalib( map<string, string>&, const string&). Data has no rows. Zero rows are not supposed to be.");
    }

    //TODO should we check that rawTableValues have only one row?
    //now we take only first row of table
    vector<string> rawValues = rawTableValues[0];

    //get columns names
    vector<string> columnNames = assignment->GetTypeTable()->GetColumnNames();
    int columnsNum = columnNames.size();
    assert(columnsNum == rawValues.size());

    //VALUES VALIDATION
    assert(values.empty());
    
    //compose values
    for (int i=0; i<columnsNum; i++) values[columnNames[i]] = rawValues[i];
    
    //finishing
    delete assignment;
    return true;
}


//______________________________________________________________________________
bool Calibration::GetCalib( map<string, double> &values, const string & namepath )
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
        double tmpVal = StringUtils::ParseDouble(iter->second, &parseResult);
        if(!parseResult) throw logic_error("Error parsing double in DCalibration::GetCalib(  map<string, double> &, const string &)");
        values[iter->first] = tmpVal;
    }

    return true;
}


//______________________________________________________________________________
bool Calibration::GetCalib( map<string, int> &values, const string & namepath )
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
        int tmpVal = StringUtils::ParseInt(iter->second, &parseResult);
        if(!parseResult) throw logic_error("Error parsing double in DCalibration::GetCalib(  map<string, int> &, const string &)");
        values[iter->first] = tmpVal;
    }

    return true;
}


//______________________________________________________________________________
bool Calibration::GetCalib( vector<string> &values, const string & namepath )
{
    /** @brief Get constants by namepath
     * 
     * this version of function fills values as one row as vector<string_values>
     * 
     * @parameter [out] values - as vector<string_values>
     * @parameter [in]  namepath - data path
     * @return true if constants were found and filled. false if namepath was not found. raises std::logic_error if any other error acured.
     */

    
    Assignment* assignment = GetAssignment(namepath);
    
    if(assignment == NULL) return false; //TODO possibly exception throwing?

    //Get data
    assert(values.empty());
    assignment->GetVectorData(values);

    delete assignment;
    //check data and check that the user will get what he ment...
    if(values.size() == 0)
        throw std::logic_error("Calibration::GetCalib(vector<string> &, const string &). Data has no rows. Zero rows are not supposed to be.");

    if(values.size() != assignment->GetTypeTable()->GetNColumns())
        throw std::logic_error("Calibration::GetCalib(vector<string> &, const string &). logic_error: Calling of single row vector<dataType> version of GetCalib method on dataset that has more than one rows. Use GetCalib vector<vector<dataType> > instead.");
}


//______________________________________________________________________________
bool Calibration::GetCalib( vector<double> &values, const string & namepath )
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
        double tmpVal = StringUtils::ParseDouble(rawValues[columnsIter], &parseResult);
        if(!parseResult) throw logic_error("Error parsing double in DCalibration::GetCalib( vector< vector<double> > &, const string &)");
        values.push_back(tmpVal);
    }
    return true;
}


//______________________________________________________________________________
bool Calibration::GetCalib( vector<int> &values, const string & namepath )
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
        int tmpVal = StringUtils::ParseInt(rawValues[columnsIter], &parseResult);
        if(!parseResult) throw logic_error("Error parsing double in DCalibration::GetCalib( vector< vector<int> > &, const string &)");
        values.push_back(tmpVal);
    }
    return true;
}

//______________________________________________________________________________
string Calibration::GetConnectionString() const
{
    //
    if (mProvider!=NULL) return mProvider->GetConnectionString();
    return string();
}


//______________________________________________________________________________
Assignment * Calibration::GetAssignment(const string& namepath, bool loadColumns /*=false*/)
{
    /** @brief Gets the assignment from provider using namepath
     * namepath is the common ccdb request; @see GetCalib
     *
     * @remark the function is thread safe
     * 
     * @parameter [in] namepath -  full namepath is /path/to/data:run:variation:time but usually it is only /path/to/data
     * @return   DAssignment *
     */

    RequestParseResult result = PathUtils::ParseRequest(namepath);
    string variation = (result.WasParsedVariation ? result.Variation : mDefaultVariation);
    int run  = (result.WasParsedRunNumber ? result.RunNumber : mDefaultRun);
    Assignment* assigment = NULL;
    if(!this->IsConnected()) throw std::logic_error("Calibration class is not connected to data source. Connect to the data source first");
    
	
    //Lock();Unlock();
    mReadMutex->Lock();
    if(result.WasParsedTime)
    {   
        assigment = mProvider->GetAssignmentShort(run, PathUtils::MakeAbsolute(result.Path), result.Time, variation,loadColumns);
    }
	else if (mDefaultTime>0)
	{
		assigment = mProvider->GetAssignmentShort(run, PathUtils::MakeAbsolute(result.Path), mDefaultTime, variation,loadColumns);
	}
    else
    {
        assigment = mProvider->GetAssignmentShort(run, PathUtils::MakeAbsolute(result.Path), variation,loadColumns);
    }
	
    mReadMutex->Release();
    return assigment;

}


//______________________________________________________________________________
void Calibration::Lock()
{
    //Thread mutex lock for multithreaded operations
    CCDBGlobalMutex::Instance()->ReadConstantsLock();
}


//______________________________________________________________________________
void Calibration::Unlock()
{
    //Thread mutex Unlock lock for multithreaded operations
    CCDBGlobalMutex::Instance()->ReadConstantsRelease();
}


//______________________________________________________________________________
void Calibration::GetListOfNamepaths( vector<string> &namepaths )
{
   /** @brief Get list of all type tables with full path
    *
    * @parameter [in] vector<string> & namepaths
    * @return   void
    */

    vector<ConstantsTypeTable*> tables;
    if(!mProvider->SearchConstantsTypeTables(tables, "*"))
    {
        throw logic_error("Error selecting all type tables");
    }

    for (int i=0; i< tables.size(); i++)
    {
        // we use substr(1) because JANA users await list
        // without '/' in the beginning of each string,
        // while GetFullPath() returns strings that start with '/'
        namepaths.push_back(tables[i]->GetFullPath().substr(1));
        delete tables[i];
    }
}

}

