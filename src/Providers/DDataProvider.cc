#include "Providers/DDataProvider.h"
#include "DLog.h"
using namespace ccdb;

namespace ccdb
{



DDataProvider::DDataProvider(void):
mMaximumErrorsToHold(100)
{
	ClearErrorsOnFunctionStart();
    mConnectionString="";
}


DDataProvider::~DDataProvider(void)
{
	
}


bool DDataProvider::ValidateName(const string& name )
{
	//Validates that name has a-zA-Z0-9_- symbols
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

void DDataProvider::SetObjectLoaded( DStoredObject* obj )
{
	if(obj!=NULL)
	{
		obj->SetIsLoaded(true);
		obj->SetIsChanged(false);
	}
}


//______________________________________________________________________________
std::string ccdb::DDataProvider::GetConnectionString()
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



vector<DDirectory *> DDataProvider::SearchDirectories( const string& searchPattern, const string& parentPath/*=""*/, int startWith/*=0*/, int select/*=0*/ )
{
	vector<DDirectory *> result;
	SearchDirectories(result, searchPattern, parentPath, startWith, select);
	return result;
}

}


bool ccdb::DDataProvider::GetRunRanges(vector<DRunRange*>& resultRunRanges, const string& typeTablePath, const string& variation/*=""*/, int take/*=0*/, int startWith/*=0*/)
{
	DConstantsTypeTable *table=GetConstantsTypeTable(typeTablePath);
	//dont look for table to be NULL, it will be checked in GetRunRanges;
	
	return GetRunRanges(resultRunRanges, table, variation, take, startWith);
}

DAssignment* ccdb::DDataProvider::CreateAssignment(const vector<vector<string> >& data, const string& path, int runMin, int runMax, const string& variationName, const string& comments)
{
	/* Creates Assignment using related object.
	* Validation:
	* If no such run range found, the new will be created (with no name)
	* No action will be done (and NULL will be returned):
	* 
	* -- If no type table with such path exists
	* -- If data is inconsistant with columns number and rows number
	* -- If no variation with such name found */

	
	DVariation* variation = GetVariation(variationName);
	if(variation == NULL)
	{
		 //TODO error message
		return NULL;
	}
	 
	DConstantsTypeTable* table=GetConstantsTypeTable(path);
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
	DRunRange * runRange = GetOrCreateRunRange(runMin, runMax, "", comments);
	if(runRange == NULL)
	{
		//TODO report cannot creat runrange
		return NULL;
	}

	DAssignment * assignment=new DAssignment(this, this);
	assignment->SetRawData(DAssignment::VectorToBlob(vectorBlob));
	
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

DAssignment* ccdb::DDataProvider::CreateAssignment( const vector<vector<string> > &data, const string& path, const string& runRangeName, const string& variationName, const string& comments )
{
	/* Creates Assignment using related object.
	* Validation:
	* If no such run range found, the new will be created (with no name)
	* No action will be done (and NULL will be returned):
	* 
	* -- If no type table with such path exists
	* -- If data is inconsistant with columns number and rows number
	* -- If no variation with such name found */

	
	DVariation* variation = GetVariation(variationName);
	if(variation == NULL)
	{
		 //TODO error message
		return NULL;
	}
	 
	DConstantsTypeTable* table=GetConstantsTypeTable(path);
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
	DRunRange * runRange = GetRunRange(runRangeName);
	if(runRange == NULL)
	{
		//TODO report cannot creat runrange
		return NULL;
	}

	DAssignment * assignment=new DAssignment(this, this);
	assignment->SetRawData(DAssignment::VectorToBlob(vectorBlob));
	
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


bool ccdb::DDataProvider::GetVariations(vector<DVariation*>& resultVariations, const string& path, int run, int take, int startWith)
{

	DConstantsTypeTable* table = GetConstantsTypeTable(path); 
	return GetVariations(resultVariations, table, run, take, startWith);
}

int ccdb::DDataProvider::GetNErrors()
{
	//Get number of errors 
	return mErrorCodes.size();
}
const vector<int>& ccdb::DDataProvider::GetErrorCodes()
{
	//Get vector of last errors 
	return mErrorCodes;
}

int ccdb::DDataProvider::GetLastError()
{
	//Gets last of the last error
	return mLastError;
}


void ccdb::DDataProvider::Error(int errorCode, const string& module, const string& message)
{
	//Logs error 
	DCCDBError * error  = new DCCDBError();
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
	DLog::Error(errorCode, module, message);
}

void ccdb::DDataProvider::ClearErrorsOnFunctionStart()
{
	//Clear error state on start of each function that emmits error
	mErrorCodes.clear();
	mLastError = CCDB_NO_ERRORS;
}

void ccdb::DDataProvider::Warning( int errorCode, const string& module, const string& message )
{
	//add error 
	mErrorCodes.push_back(errorCode);
	mLastError = errorCode;

	//cut array if needed
	while(mErrorCodes.size()> mMaximumErrorsToHold) mErrorCodes.erase(mErrorCodes.begin());

	//do log error
	DLog::Warning(errorCode, module, message);
}

void ccdb::DDataProvider::ClearErrors()
{
	mErrorCodes.clear();
	mLastError = CCDB_NO_ERRORS;
}

std::vector<DCCDBError *> ccdb::DDataProvider::GetErrors()
{
	return mErrors;
}

