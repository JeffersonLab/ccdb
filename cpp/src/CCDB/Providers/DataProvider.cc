#include <stdio.h>


#include "CCDB/Providers/DataProvider.h"
#include "CCDB/Log.h"
#include "CCDB/Helpers/StringUtils.h"
#include "CCDB/Helpers/PathUtils.h"

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
#pragma region Directory management
//______________________________________________________________________________
Directory* DataProvider::GetDirectory( const string& path )
{
	/** @brief Gets directory by its full path
    *
    * @param   Full path of the directory
    * @return DDirectory object if directory exists, NULL otherwise
    */

	//maybe we need to update our directories?
	UpdateDirectoriesIfNeeded();

	//search full path
	map<string, Directory*>::iterator it = mDirectoriesByFullPath.find(string(path));

	//found?
	if(it == mDirectoriesByFullPath.end()) return NULL; //not found
	return it->second; //found
}


//______________________________________________________________________________
void DataProvider::BuildDirectoryDependencies()
{
    /** @brief Builds directory relational structure. Used right at the end of RetriveDirectories().
    *   this method is supposed to be called after new directories are loaded, but dont have hierarchical structure
    */

	//clear the full path dictionary
	mDirectoriesByFullPath.clear();
	mDirectoriesByFullPath[mRootDir->GetFullPath()] = mRootDir;

	//begin loop through the directories
	vector<Directory *>::iterator dirIter = mDirectories.begin();
	for(;dirIter < mDirectories.end(); dirIter++)
	{
		// retrieve parent id 
		// and check if it have parent directory
		Directory *dir = *dirIter; //(*dirIter) cool it is C++, baby

		if(dir->GetParentId() >0)
		{
			//this directory must have a parent! so now search it
			map<int,Directory *>::iterator parentDirIter = mDirectoriesById.find(dir->GetParentId()) ;
			if(parentDirIter!=mDirectoriesById.end())
			{
				//We found parent
				parentDirIter->second->AddSubdirectory(*dirIter);
			}
			else
			{
				//TODO : ADD error, parent Id not found
				Error(CCDB_ERROR_NO_PARENT_DIRECTORY,"MySQLDataProvider::BuildDirectoryDependences", "Parent directory with wrong id");
				continue; //we have to stop operate this directory...
			}
		}
		else
		{
			// this directory doesn't have parent 
			// (means it doesn't have parentId so it lays in root directory)
			// so we place it to root directory
			mRootDir->AddSubdirectory(*dirIter);
		}

		//creating full path for this directory
		string fullpath = PathUtils::CombinePath(dir->GetParentDirectory()->GetFullPath(), dir->GetName());
		dir->SetFullPath(fullpath);


		//add to our full path map
		mDirectoriesByFullPath[dir->GetFullPath()] = dir;
	}
}


//______________________________________________________________________________
Directory*const DataProvider::GetRootDirectory()
{
     /** @brief return reference to root directory
     * 
     * Root directory contains all other directories. It is not stored in any database
     *
     * @warning User should not delete this object 
     *
     * @return   DDirectory object pointer
     */

	UpdateDirectoriesIfNeeded();
	return mRootDir;
}


//______________________________________________________________________________
bool DataProvider::CheckDirectoryListActual()
{
    //Checks if directory list is actual i.e. nobody changed directories in database
	//TODO: method should check the database if the directories was updated in DB. Now it only checks if directories were loaded

	if(!mDirsAreLoaded) return false; //directories are not loaded

	return !mNeedCheckDirectoriesUpdate; 
}


//______________________________________________________________________________
bool DataProvider::UpdateDirectoriesIfNeeded()
{	
    //Update directories structure if this is required

	//Logic to check directories...
	if(!this->mDirsAreLoaded) return LoadDirectories();
	return true;
}



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

#pragma endregion Directory management

//----------------------------------------------------------------------------------------
//	C O N S T A N T   T Y P E   T A B L E
//----------------------------------------------------------------------------------------

#pragma region Type tables

//______________________________________________________________________________
ConstantsTypeTable * DataProvider::GetConstantsTypeTable(const string& path, bool loadColumns/*=false*/ )
{
	/** @brief Gets ConstantsType information from the DB
     *
     * @param  [in] name name of ConstantsTypeTable
     * @param  [in] parentDir directory that contains type table
     * @return new object of ConstantsTypeTable
     */
    
	//get directory path
	string dirPath = PathUtils::ExtractDirectory(path);

	//and directory
	Directory *dir = GetDirectory(dirPath.c_str());
	//probably one may wish to check dir to be !=NULL,
	//but such check is in GetConstantsTypeTable(const char* name, DDirectory *parentDir);

	//retrieve name of our constant table 
	string name = PathUtils::ExtractObjectname(path);

	//get it from db etc...
	return GetConstantsTypeTable(name, dir, loadColumns);
}

#pragma endregion Type tables

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


//----------------------------------------------------------------------------------------
//	V A R I A T I O N
//----------------------------------------------------------------------------------------

//______________________________________________________________________________
bool DataProvider::GetVariations(vector<Variation*>& resultVariations, const string& path, int run, int take, int startWith)
{

    ConstantsTypeTable* table = GetConstantsTypeTable(path); 
    return GetVariations(resultVariations, table, run, take, startWith);
}




//----------------------------------------------------------------------------------------
//	A S S I G N M E N T S
//----------------------------------------------------------------------------------------
#pragma region Assignments


Assignment* DataProvider::GetAssignmentFull( int run, const string& path, const string& variation )
{
	/** @brief Get last Assignment with all related objects
     *
     * @param     int run
     * @param     path to constant path
     * @return NULL if no assignment is found or error
     */
	
	vector<Assignment *> assigments;
	if(!GetAssignments(assigments, path, run,run, "", variation, 0, 0, 0, 1, 0))
	{
		return NULL;
	}

	if(assigments.size()<=0) return NULL;

	return *assigments.begin();

}

Assignment* DataProvider::GetAssignmentFull( int run, const string& path,int version, const string& variation/*= "default"*/)
{
	/** @brief  Get specified version of Assignment with all related objects
     *
     * @param     int run
     * @param     const char * path
     * @param     const char * variation
     * @param     int version
     * @return   DAssignment*
     */

	//get table! 
	vector<Assignment *> assigments;
	if(!GetAssignments(assigments, path, run,run, "", variation, 0, 0, 1, 1, version))
	{
		return NULL;
	}

	if(assigments.size()<=0) return NULL;

	return *assigments.begin();
}

//______________________________________________________________________________

#pragma endregion Assignments


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

