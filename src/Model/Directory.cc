/*
 * Directory.cpp
 *
 *  Created on: Sep 28, 2010
 *      Author: romanov
 */

#include "Model/DDirectory.h"
using namespace std;
namespace ccdb
{

DDirectory::DDirectory( DObjectsOwner * owner/*=NULL*/, DDataProvider *provider/*=NULL*/ ):
DStoredObject(owner, provider),
mSubDirectories(0),
mName(""),
mFullPath(""),
mComment("")
{
	mParent = NULL;
	mId = 0;
	mParentId = 0;

}

DDirectory::DDirectory():
DStoredObject(NULL, NULL),
mSubDirectories(0),
mName(""),
mFullPath(""),
mComment("")
{
	mParent = NULL;
	mId = 0;
	mParentId = 0;
}



DDirectory::~DDirectory() {
	// TODO Auto-generated destructor stub
}
}

void ccdb::DDirectory::DisposeSubdirectories()
{
	if(mSubDirectories.size() > 0 ) //do we have subdirectories at all?
	{
		vector<DDirectory *>::iterator it;
		for(it=mSubDirectories.begin(); it<mSubDirectories.end(); ++it)
		{
			DDirectory * subdir = *it; 			//get link
			subdir->DisposeSubdirectories();	//ask to cleanup its subdirectories
			
			delete subdir;						//delete subdir
		}
		mSubDirectories.clear();				//dont forget to erase it
	}
}

void ccdb::DDirectory::AddSubdirectory(DDirectory* subdirectory)
{
	subdirectory->mParent = this;
	mSubDirectories.push_back(subdirectory);
}

ccdb::DDirectory* ccdb::DDirectory::GetParentDirectory()
{	
	return mParent;
}

const vector<ccdb::DDirectory*>& ccdb::DDirectory::GetSubdirectories()
{
	return mSubDirectories;
}

string ccdb::DDirectory::GetName() const
{
	//TODO: Implement method

	return mName;
}

void ccdb::DDirectory::SetName( std::string val )
{
	//TODO: Implement method

	mName = val;
}

std::string ccdb::DDirectory::GetFullPath() const
{
	//TODO: Implement method

	return mFullPath;
}

void ccdb::DDirectory::SetFullPath( std::string val )
{
	//TODO: Implement method

	mFullPath = val;
}

std::string ccdb::DDirectory::GetComment() const
{
	//TODO: Implement method

	return mComment;
}

void ccdb::DDirectory::SetComment( std::string val )
{
	//TODO: Implement method

	mComment = val;
}

dbkey_t ccdb::DDirectory::GetParentId() const
{
	//TODO: Implement method

	return mParentId;
}

void ccdb::DDirectory::SetParentId( dbkey_t val )
{
	//TODO: Implement method

	mParentId = val;
}

int ccdb::DDirectory::GetId() const
{
	//TODO: Implement method

	return mId;
}

void ccdb::DDirectory::SetId( dbkey_t val )
{
	//TODO: Implement method

	mId = val;
}

time_t ccdb::DDirectory::GetCreatedTime() const
{
	//TODO: Implement method

	return mCreatedTime;
}

void ccdb::DDirectory::SetCreatedTime( time_t val )
{
	//TODO: Implement method

	mCreatedTime = val;
}

time_t ccdb::DDirectory::GetModifiedTime() const
{
	//TODO: Implement method

	return mModifiedTime;
}

void ccdb::DDirectory::SetModifiedTime( time_t val )
{
	//TODO: Implement method

	mModifiedTime = val;
}















