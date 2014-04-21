/*
 * TableHeader.cpp
 *
 *  Created on: Sep 29, 2010
 *      Author: romanov
 */
#include <algorithm>

#include "CCDB/Model/ConstantsTypeTable.h"
#include "CCDB/Helpers/StringUtils.h"
#include "CCDB/Helpers/PathUtils.h"

namespace ccdb {
	class DConstantsType;

ConstantsTypeTable::ConstantsTypeTable( ObjectsOwner * owner/*=NULL*/, DataProvider *provider/*=NULL*/ ):
StoredObject(owner, provider)
{
	mName = "";				//Name of the table of constants
	mFullPath = "";		//Full path of the constant
	mDirectory = NULL;	//Link to the directory that holds this constant
	mDirectoryId = 0;		//Parent directory ID in the DB
	mId = 0;					//db id
	mComment = "";			//comment
	mCreatedTime = 0;		//creation time
	mUpdateTime = 0;		//update time
	mNRows = 0;
	mNColumnsFromDB = 0;		//
	mColumns.clear();
}


ConstantsTypeTable::~ConstantsTypeTable() 
{
	
}


/** @brief GetColumns
 *
 * @return   vector<ConstantsTypeColumn *>
 */
const vector<ConstantsTypeColumn *>& ConstantsTypeTable::GetColumns() const
{
	//TODO: Implement method

	return mColumns;
}

int ConstantsTypeTable::GetColumnsCount() const
{
	//Here is a trick. Maybe we loaded it from db with no columns objects
	if(mColumns.size() ==0 && IsLoaded()) return mNColumnsFromDB;

	//but otherwise number of objects must indicate...
	return mColumns.size();
}

void ConstantsTypeTable::AddColumn( ConstantsTypeColumn *col, int order )
{
	if(order > mColumns.size())
	{
		//TODO print error;
		return;
	}

	if(mColumns.size()>0)
	{
		std::sort(mColumns.begin(), mColumns.end()); //sort vector by order;
		if(order <= (mColumns.size() - 1))
		{
			/*mColumns.insert()*/ //C++ are surprisingly dump language...
			vector<ConstantsTypeColumn *>::iterator it= mColumns.begin();
			for(;it<mColumns.end();++it)
			{
				ConstantsTypeColumn *column = *it;
				if((int)column->GetOrder() >= order) column->SetOrder(column->GetOrder()+1); 
			}

			it= mColumns.begin();
			mColumns.insert(it + order, col);
		}
		else
		{
			mColumns.push_back(col);
		}
	}
	else
	{
		mColumns.push_back(col);
	}
	col->SetTypeTable(this);
}

void ConstantsTypeTable::AddColumn( ConstantsTypeColumn *col )
{
	mColumns.push_back(col);
	col->SetOrder(mColumns.size()-1);
	col->SetTypeTable(this);
}

void ConstantsTypeTable::AddColumn( const std::string& name, const std::string& type )
{
	ConstantsTypeColumn *column = new ConstantsTypeColumn(this);
	column->SetName(name);
	column->SetType(type);
	AddColumn(column);
}


void ccdb::ConstantsTypeTable::AddColumn(const string& name, ConstantsTypeColumn::ColumnTypes type)
{
	ConstantsTypeColumn *column = new ConstantsTypeColumn(this);
	column->SetName(name);
	column->SetType(type);
	AddColumn(column);
}

ConstantsTypeColumn * ConstantsTypeTable::RemoveColumn( int order )
{
	if(order > mColumns.size() && mColumns.size()>0)
	{
		//TODO print error;
		return NULL;
	}

	std::sort(mColumns.begin(), mColumns.end()); //sort vector by order;

	//C++ are surprisingly dump language...
	vector<ConstantsTypeColumn *>::iterator it= mColumns.begin();
	ConstantsTypeColumn *col = *it;
	mColumns.erase(it + order);
	return *it;

}

int ConstantsTypeTable::GetRowsCount() const
{
	return mNRows;
}

void ConstantsTypeTable::SetNRows( int val )
{
	mNRows = val;
}

#pragma region Setters and getters

    Directory *ConstantsTypeTable::GetDirectory() const
    {
        return mDirectory;
    }

    int ConstantsTypeTable::GetDirectoryId() const
    {
        return mDirectoryId;
    }

    string ConstantsTypeTable::GetFullPath() const
    {
        return mFullPath;
    }

    int ConstantsTypeTable::GetId() const
    {
        return mId;
    }

    string ConstantsTypeTable::GetName() const
    {
        return mName;
    }

void ConstantsTypeTable::SetDirectory(Directory *fDirectory)
{
	this->mDirectory = fDirectory;
	
	 //now this name affects full path...
	if(mDirectory!=NULL)	
	{
		mFullPath.assign(PathUtils::CombinePath(mDirectory->GetFullPath(), mName));
	}
	else
	{
		mFullPath.assign("");
	}
}

void ConstantsTypeTable::SetDirectoryId(int fDirectoryId)
{
	this->mDirectoryId = fDirectoryId;
}

void ConstantsTypeTable::SetFullPath(string fFullPath)
{
	this->mFullPath = fFullPath;
}

void ConstantsTypeTable::SetId(dbkey_t id)
{
	this->mId = id;
	
	//now this new id should be set for all the columns
	if(mColumns.size()>0)
	{
		for(int i=0; i<mColumns.size(); i++)
		{
			mColumns[i]->SetDBTypeTableId(id);
		}
	}
}

void ConstantsTypeTable::SetName(const string& name)
{
	mName.assign(name);
	
	//now this name affects full path...
	if(mDirectory!=NULL)	
	{
		mFullPath.assign(PathUtils::CombinePath(mDirectory->GetFullPath(), name));
	}
	else
	{
		mFullPath.assign("");
	}
}

	time_t ConstantsTypeTable::GetCreatedTime() const
	{
		return mCreatedTime;
	}

	void ConstantsTypeTable::SetCreatedTime( time_t val )
	{
		mCreatedTime = val;
	}

	std::string ConstantsTypeTable::GetComment() const
	{
		return mComment;
	}

	void ConstantsTypeTable::SetComment(const string& val )
	{
		mComment.assign(val);
	}

	time_t ConstantsTypeTable::GetModifiedTime() const
	{
		return mUpdateTime;
	}

	void ConstantsTypeTable::SetModifiedTime( time_t val )
	{
		mUpdateTime = val;
	}

	void ConstantsTypeTable::ClearColumns()
	{
		mColumns.clear();
	}

	int ConstantsTypeTable::GetNColumnsFromDB() const
	{
		return mNColumnsFromDB;
	}

	void ConstantsTypeTable::SetNColumnsFromDB( int val )
	{
		mNColumnsFromDB = val;
	}

	vector<string> ConstantsTypeTable::GetColumnNames() const
	{
		//future result
		vector<string> names;

		//and just a loop through columns
		vector<ConstantsTypeColumn *>::const_iterator iter = mColumns.begin();
		while(iter<mColumns.end())
		{
			names.push_back((*iter)->GetName());
			iter++;
		}
		return names;
	}

	vector<string> ConstantsTypeTable::GetColumnTypeStrings() const
	{
		//future result
		vector<string> types;

		//and just a loop through columns
		vector<ConstantsTypeColumn *>::const_iterator iter = mColumns.begin();
		while(iter<mColumns.end())
		{
			types.push_back((*iter)->GetTypeString());
			iter++;
		}
		return types;
	}

	map<string, ConstantsTypeColumn *> & ConstantsTypeTable::GetColumnsByName()
	{
		if (mColumnsByName.size() == 0)
		{
			for (size_t i = 0; i < mColumns.size(); i++){
				mColumnsByName[mColumns[i]->GetName()] = mColumns[i];
			}
		}
		return mColumnsByName;
	}





#pragma endregion Setters and getters


}

