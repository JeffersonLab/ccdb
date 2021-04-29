#include <stdio.h>


#include "CCDB/Providers/DataProvider.h"
#include "CCDB/Helpers/StringUtils.h"
#include "CCDB/Helpers/PathUtils.h"

#include "CCDB/Globals.h"

using namespace ccdb;
using namespace std;

namespace ccdb
{

//______________________________________________________________________________
DataProvider::DataProvider()
{
    //Constructor
    mConnectionString="";
}


//______________________________________________________________________________
DataProvider::~DataProvider()
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
	auto it = mDirectoriesByFullPath.find(string(path));

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
	auto dirIter = mDirectories.begin();
	for(;dirIter < mDirectories.end(); dirIter++)
	{
		// retrieve parent id 
		// and check if it have parent directory
		Directory *dir = *dirIter; //(*dirIter) cool it is C++, baby

		if(dir->GetParentId() >0)
		{
			//this directory must have a parent! so now search it
			auto parentDirIter = mDirectoriesById.find(dir->GetParentId()) ;
			if(parentDirIter!=mDirectoriesById.end())
			{
				//We found parent
				parentDirIter->second->AddSubdirectory(*dirIter);
			}
			else
			{
				throw runtime_error("ccdb::DataProvider::BuildDirectoryDependencies=>Parent directory with wrong id");
			}
		}
		else
		{
			// this directory doesn't have parent 
			// (means it doesn't have parentId so it lays in root directory)
			// so we place it to root directory
			mRootDir->AddSubdirectory(*dirIter);
		}

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
void DataProvider::UpdateDirectoriesIfNeeded()
{	
    //Update directories structure if this is required

	//Logic to check directories...
	if(!this->mDirsAreLoaded) LoadDirectories();
}



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
	Directory *dir = GetDirectory(dirPath);
	//probably one may wish to check dir to be !=NULL,
	//but such check is in GetConstantsTypeTable(const char* name, DDirectory *parentDir);

	//retrieve name of our constant table 
	string name = PathUtils::ExtractObjectname(path);

	//get it from db etc...
	return GetConstantsTypeTable(name, dir, loadColumns);
}


} //namespace ccdb

