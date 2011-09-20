/*
 * Directory.cpp
 *
 *  Created on: Sep 28, 2010
 *      Author: romanov
 */

#include "CCDB/Model/Directory.h"

using namespace std;
namespace ccdb
{

Directory::Directory( ObjectsOwner * owner/*=NULL*/, DataProvider *provider/*=NULL*/ ):
StoredObject(owner, provider),
mSubDirectories(0),
mName(""),
mFullPath(""),
mComment("")
{
	mParent = NULL;
	mId = 0;
	mParentId = 0;

}

Directory::Directory():
StoredObject(NULL, NULL),
mSubDirectories(0),
mName(""),
mFullPath(""),
mComment("")
{
	mParent = NULL;
	mId = 0;
	mParentId = 0;
}



Directory::~Directory() {
	// TODO Auto-generated destructor stub
}
}

void ccdb::Directory::DisposeSubdirectories()
{
	if(mSubDirectories.size() > 0 ) //do we have subdirectories at all?
	{
		vector<Directory *>::iterator it;
		for(it=mSubDirectories.begin(); it<mSubDirectories.end(); ++it)
		{
			Directory * subdir = *it; 			//get link
			subdir->DisposeSubdirectories();	//ask to cleanup its subdirectories
			
			delete subdir;						//delete subdir
		}
		mSubDirectories.clear();				//dont forget to erase it
	}
}

void ccdb::Directory::AddSubdirectory(Directory* subdirectory)
{
	subdirectory->mParent = this;
	mSubDirectories.push_back(subdirectory);
}

ccdb::Directory* ccdb::Directory::GetParentDirectory()
{	
	return mParent;
}

const vector<ccdb::Directory*>& ccdb::Directory::GetSubdirectories()
{
	return mSubDirectories;
}

string ccdb::Directory::GetName() const
{
	//TODO: Implement method

	return mName;
}

void ccdb::Directory::SetName( std::string val )
{
	//TODO: Implement method

	mName = val;
}

std::string ccdb::Directory::GetFullPath() const
{
	//TODO: Implement method

	return mFullPath;
}

void ccdb::Directory::SetFullPath( std::string val )
{
	//TODO: Implement method

	mFullPath = val;
}

std::string ccdb::Directory::GetComment() const
{
	//TODO: Implement method

	return mComment;
}

void ccdb::Directory::SetComment( std::string val )
{
	//TODO: Implement method

	mComment = val;
}

dbkey_t ccdb::Directory::GetParentId() const
{
	//TODO: Implement method

	return mParentId;
}

void ccdb::Directory::SetParentId( dbkey_t val )
{
	//TODO: Implement method

	mParentId = val;
}

int ccdb::Directory::GetId() const
{
	//TODO: Implement method

	return mId;
}

void ccdb::Directory::SetId( dbkey_t val )
{
	//TODO: Implement method

	mId = val;
}

time_t ccdb::Directory::GetCreatedTime() const
{
	//TODO: Implement method

	return mCreatedTime;
}

void ccdb::Directory::SetCreatedTime( time_t val )
{
	//TODO: Implement method

	mCreatedTime = val;
}

time_t ccdb::Directory::GetModifiedTime() const
{
	//TODO: Implement method

	return mModifiedTime;
}

void ccdb::Directory::SetModifiedTime( time_t val )
{
	//TODO: Implement method

	mModifiedTime = val;
}















