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

Directory::Directory():
    mSubDirectories(0),
    mName(""),
    mComment("")
{
	mParent = nullptr;
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

std::string ccdb::Directory::GetFullPath() const
{
    string parentFullPath = mParent ? mParent->GetFullPath() : "";
	if(!parentFullPath.empty() && parentFullPath[parentFullPath.size()-1] == '/') {
		// We have parent ending '/'
		return parentFullPath + mName;
	}

	return parentFullPath + "/" + mName;
}












