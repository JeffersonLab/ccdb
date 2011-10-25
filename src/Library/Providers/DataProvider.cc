#include <stdio.h>


#include "CCDB/Providers/DataProvider.h"
#include "CCDB/Log.h"
#include "CCDB/Helpers/StringUtils.h"
#include "CCDB/Globals.h"
#include "CCDB/Providers/EnvironmentAuthentication.h"

using namespace ccdb;
using namespace std;

namespace ccdb
{


//______________________________________________________________________________
DataProvider::DataProvider(void):
    mMaximumErrorsToHold(100)
{
    //Constructor
    mAuthentication = new EnvironmentAuthentication();
    mLogUserName = mAuthentication->GetLogin();

	ClearErrorsOnFunctionStart();
    mConnectionString="";
}


//______________________________________________________________________________
DataProvider::~DataProvider(void)
{
	//Guess what is it?
}


//______________________________________________________________________________
bool DataProvider::ValidateName(const string& name )
{
	//Validates that name has a-zA-Z0-9_- symbols
    //TODO move this function to Path API

	for(string::const_iterator charIter = name.begin(); charIter<name.end(); ++charIter)
	{
		char letter = *charIter;
		if(
			(letter<'a' || letter>'z')&&
			(letter<'A' || letter>'Z')&&
			(letter<'0' || letter>'9')&&
			(letter!='_')&& 
			(letter!='-'))
		{
			return false;
		}
	}
	return true;
}


//______________________________________________________________________________
void DataProvider::SetObjectLoaded( StoredObject* obj )
{

    //TODO possibly we dont use it anymore...
	if(obj!=NULL)
	{
		obj->SetIsLoaded(true);
		obj->SetIsChanged(false);
	}
}


//----------------------------------------------------------------------------------------
//	C O N N E C T I O N
//----------------------------------------------------------------------------------------


//______________________________________________________________________________
std::string DataProvider::GetConnectionString()
{
    /** @brief Conection string that was used on last successfull connect.
     *
     * Conection string that was used on last successfull connect.
     * If no any successfull connects were done string::empty will be returned
     *
     * @return  Last connection string or string::empty if no successfull connection was done
     */

    return mConnectionString;
}

//----------------------------------------------------------------------------------------
//	D I R E C T O R Y   M A N G E M E N T
//----------------------------------------------------------------------------------------

//______________________________________________________________________________
vector<Directory *> DataProvider::SearchDirectories( const string& searchPattern, const string& parentPath/*=""*/, int startWith/*=0*/, int select/*=0*/ )
{
    /** @brief Searches for directory 
     *
     * Searches directories that matches the pattern 
     * inside parent directory with path @see parentPath 
     * or globally through all type tables if parentPath is empty
     * The pattern might contain
     * '*' - any character sequence 
     * '?' - any single character
     *
     * paging could be done with @see startWith  @see take
     * startWith=0 and take=0 means select all records;
     *
     * objects that are contained in vector<DDirectory *>& resultDirectories will be
     * 1) if this provider owned - deleted (@see ReleaseOwnership)
     * 2) if not owned - just leaved on user control
     *
     * @param  [out] resultDirectories	search result
     * @param  [in]  searchPattern		Pattern to search
     * @param  [in]  parentPath			Parent path. If NULL search through all directories
     * @param  [in]  startRecord		record number to start with
     * @param  [in]  selectRecords		number of records to select. 0 means select all records
     * @return bool true if there were error (even if 0 directories found) 
     */

	vector<Directory *> result;
	SearchDirectories(result, searchPattern, parentPath, startWith, select);
	return result;
}


//______________________________________________________________________________
bool DataProvider::RecursiveDeleteDirectory( Directory *dir )
{
    //  NEVER USE IT UNLESS YOU KNOW
    //  Deletes directory and all tables and subdirectories in it
    // 
    //  @remarks This function is here to use ccdb as a general data storage only 
    //  this function is against the phylosofy "No delete. Any change by adding New"
    // 
    // 

    std::cerr<<"RecursiveDeleteDirectory( DDirectory *dir ) is not implemented"<<endl;
    return false;
}

//----------------------------------------------------------------------------------------
//	C O N S T A N T   T Y P E   T A B L E
//----------------------------------------------------------------------------------------


//______________________________________________________________________________
bool DataProvider::RecursiveDeleteTypeTable( ConstantsTypeTable *dir )
{
    //
    /** NEVER USE IT UNLESS YOU KNOW
     *  Deletes type table and all assignments in it
     *
     *  @remarks This function is here to use ccdb as a general data storage only 
     *  this function is against the philosofy "No delete. Any change by adding New"
     *
     */
    std::cerr<<"RecursiveDeleteTypeTable( ConstantsTypeTable *dir ) is not implemented"<<endl;
    return false;
}


//----------------------------------------------------------------------------------------
//	R U N   R A N G E S
//----------------------------------------------------------------------------------------

//______________________________________________________________________________
bool DataProvider::GetRunRanges(vector<RunRange*>& resultRunRanges, const string& typeTablePath, const string& variation/*=""*/, int take/*=0*/, int startWith/*=0*/)
{
	ConstantsTypeTable *table=GetConstantsTypeTable(typeTablePath);
	//dont look for table to be NULL, it will be checked in GetRunRanges;
	
	return GetRunRanges(resultRunRanges, table, variation, take, startWith);
}

//______________________________________________________________________________
bool DataProvider::RecursiveDeleteRunRange( RunRange *dir )
{
    /** NEVER USE IT UNLESS YOU KNOW
     *  Deletes run range and all assignments in it
     *
     *  @remarks This function is here to use ccdb as a general data storage only 
     *  this function is against the philosophy "No delete. Any change by adding New"
     *
     */
    std::cerr<<"RecursiveDeleteRunRange( DRunRange *dir ) is not implemented"<<endl;
    return false;

}

//----------------------------------------------------------------------------------------
//	V A R I A T I O N
//----------------------------------------------------------------------------------------

//______________________________________________________________________________
bool DataProvider::GetVariations(vector<Variation*>& resultVariations, const string& path, int run, int take, int startWith)
{

    ConstantsTypeTable* table = GetConstantsTypeTable(path); 
    return GetVariations(resultVariations, table, run, take, startWith);
}


//______________________________________________________________________________
bool DataProvider::RecursiveDeleteVariation( Variation *dir )
{
    /** NEVER USE IT UNLESS YOU KNOW
     *  Deletes variation and all assignments that belongs to it 
     *
     *  @remarks This function is here to use ccdb as a general data storage only 
     *  this function is against the philosophy "No delete. Any change by adding New"
     *
     */
    std::cerr<<"RecursiveDeleteVariation( DVariation *dir ) is not implemented"<<endl;
    return false;

}

//----------------------------------------------------------------------------------------
//	A S S I G N M E N T S
//----------------------------------------------------------------------------------------

//______________________________________________________________________________
Assignment* DataProvider::CreateAssignment(const vector<vector<string> >& data, const string& path, int runMin, int runMax, const string& variationName, const string& comments)
{
	/* Creates Assignment using related object.
	* Validation:
	* If no such run range found, the new will be created (with no name)
	* No action will be done (and NULL will be returned):
	* 
	* -- If no type table with such path exists
	* -- If data is inconsistant with columns number and rows number
	* -- If no variation with such name found */

	
	Variation* variation = GetVariation(variationName);
	if(variation == NULL)
	{
		 //TODO error message
		return NULL;
	}
	 
	ConstantsTypeTable* table=GetConstantsTypeTable(path);
	if(!table)
	{
		//TODO error message
		return NULL;
	}
	 
	//check that we have right rows number
	if(data.size()!= table->GetNRows())
	{
		 //TODO error message
		return NULL;
	}

	//fill data blob vector
	vector<string> vectorBlob;
	for (size_t rowIter=0; rowIter<data.size(); rowIter++)
	{
		const vector<string> &row = data[rowIter];
		if(row.size() != table->GetNColumns())
		{
			//TODO error handle
			return NULL;
		}

		for (int i=0; i<row.size(); i++)
		{
			vectorBlob.push_back(row[i]);
		}
	}
	
	//last one we need is a run range
	RunRange * runRange = GetOrCreateRunRange(runMin, runMax, "", "");
	if(runRange == NULL)
	{
        //error report is in GetOrCreateRunRange
		return NULL;
	}

	Assignment * assignment=new Assignment(this, this);
	assignment->SetRawData(Assignment::VectorToBlob(vectorBlob));
	
	assignment->SetVariation(variation);
	assignment->BeOwner(variation);

	assignment->SetRunRange(runRange);
	assignment->BeOwner(runRange);

	assignment->SetTypeTable(table);	//set this table
	assignment->BeOwner(table);			//new table should be owned by assignment

	if(CreateAssignment(assignment))
	{
		return assignment;
	}
	else 
	{
		delete assignment;
		return NULL;
	}
}

//______________________________________________________________________________
Assignment* DataProvider::CreateAssignment( const vector<vector<string> > &data, const string& path, const string& runRangeName, const string& variationName, const string& comments )
{
	/* Creates Assignment using related object.
	* Validation:
	* If no such run range found, the new will be created (with no name)
	* No action will be done (and NULL will be returned):
	* 
	* -- If no type table with such path exists
	* -- If data is inconsistant with columns number and rows number
	* -- If no variation with such name found */

	
	Variation* variation = GetVariation(variationName);
	if(variation == NULL)
	{
		 //TODO error message
		return NULL;
	}
	 
	ConstantsTypeTable* table=GetConstantsTypeTable(path);
	if(!table)
	{
		//TODO error message
		return NULL;
	}
	 
	//check that we have right rows number
	if(data.size()!= table->GetNRows())
	{
		 //TODO error message
		return NULL;
	}

	//fill data blob vector
	vector<string> vectorBlob;
	for (int rowIter=0; rowIter<data.size(); rowIter++)
	{
		const vector<string> &row = data[rowIter];
		if(row.size() != table->GetNColumns())
		{
			//TODO error handle
			return NULL;
		}

		for (int i=0; i<row.size(); i++)
		{
			vectorBlob.push_back(row[i]);
		}
	}
	
	//last one we need is a run range
	RunRange * runRange = GetRunRange(runRangeName);
	if(runRange == NULL)
	{
		//TODO report cannot creat runrange
		return NULL;
	}

	Assignment * assignment=new Assignment(this, this);
	assignment->SetRawData(Assignment::VectorToBlob(vectorBlob));
	
	assignment->SetVariation(variation);
	assignment->BeOwner(variation);

	assignment->SetRunRange(runRange);
	assignment->BeOwner(runRange);

	assignment->SetTypeTable(table);	//set this table
	assignment->BeOwner(table);			//new table should be owned by assignment

	if(CreateAssignment(assignment))
	{
		return assignment;
	}
	else 
	{
		delete assignment;
		return NULL;
	}
}

//----------------------------------------------------------------------------------------
//	E R R O R   H A N D L I N G 
//----------------------------------------------------------------------------------------

//______________________________________________________________________________
int DataProvider::GetNErrors()
{
	//Get number of errors 
	return mErrorCodes.size();
}


//______________________________________________________________________________
const vector<int>& DataProvider::GetErrorCodes()
{
	//Get vector of last errors 
	return mErrorCodes;
}


//______________________________________________________________________________
int DataProvider::GetLastError()
{
	//Gets last of the last error
	return mLastError;
}


//______________________________________________________________________________
void DataProvider::Error(int errorCode, const string& module, const string& message)
{
	//Logs error 
	CCDBError * error  = new CCDBError();
	error->SetId(errorCode);
	error->SetSource(module);
	error->SetMessage(message);
	error->SetLevel(1);
	//add error 
	mErrorCodes.push_back(errorCode);
	mLastError = errorCode;
	
	//cut array if needed
	while(mErrorCodes.size()> mMaximumErrorsToHold) mErrorCodes.erase(mErrorCodes.begin());
	
	//do log error
	Log::Error(errorCode, module, message);
}


//______________________________________________________________________________
void DataProvider::ClearErrorsOnFunctionStart()
{
	//Clear error state on start of each function that emmits error
	mErrorCodes.clear();
	mLastError = CCDB_NO_ERRORS;
}


//______________________________________________________________________________
void DataProvider::Warning( int errorCode, const string& module, const string& message )
{
	//add error 
	mErrorCodes.push_back(errorCode);
	mLastError = errorCode;

	//cut array if needed
	while(mErrorCodes.size()> mMaximumErrorsToHold) mErrorCodes.erase(mErrorCodes.begin());

	//do log error
	Log::Warning(errorCode, module, message);
}


//______________________________________________________________________________
void DataProvider::ClearErrors()
{
	mErrorCodes.clear();
	mLastError = CCDB_NO_ERRORS;
}


//______________________________________________________________________________
std::vector<CCDBError *> DataProvider::GetErrors()
{
	return mErrors;
}








} //namespace ccdb

