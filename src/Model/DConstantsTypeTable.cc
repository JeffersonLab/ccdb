/*
 * TableHeader.cpp
 *
 *  Created on: Sep 29, 2010
 *      Author: romanov
 */

#include "Model/DConstantsTypeTable.h"
#include <algorithm>
#include "DStringUtils.h"

namespace ccdb {
	class DConstantsType;

DConstantsTypeTable::DConstantsTypeTable( DObjectsOwner * owner/*=NULL*/, DDataProvider *provider/*=NULL*/ ):
DStoredObject(owner, provider)
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


}


DConstantsTypeTable::~DConstantsTypeTable() 
{
	
}


/** @brief GetColumns
 *
 * @return   vector<DConstantsTypeColumn *>
 */
const vector<DConstantsTypeColumn *>& DConstantsTypeTable::GetColumns() const
{
	//TODO: Implement method

	return mColumns;
}

int DConstantsTypeTable::GetNColumns() const
{
	//Here is a trick. Maybe we loaded it from db with no columns objects
	if(mColumns.size() ==0 && IsLoaded()) return mNColumnsFromDB;

	//but otherwise number of objects must indicate...
	return mColumns.size();
}

void DConstantsTypeTable::AddColumn( DConstantsTypeColumn *col, int order )
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
			vector<DConstantsTypeColumn *>::iterator it= mColumns.begin();
			for(;it<mColumns.end();++it)
			{
				DConstantsTypeColumn *column = *it;
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

void DConstantsTypeTable::AddColumn( DConstantsTypeColumn *col )
{
	mColumns.push_back(col);
	col->SetOrder(mColumns.size()-1);
	col->SetTypeTable(this);
}

void DConstantsTypeTable::AddColumn( const std::string& name, const std::string& type )
{
	DConstantsTypeColumn *column = new DConstantsTypeColumn(this);
	column->SetName(name);
	column->SetType(type);
	AddColumn(column);
}


void ccdb::DConstantsTypeTable::AddColumn(const string& name, DConstantsTypeColumn::DColumnTypes type)
{
	DConstantsTypeColumn *column = new DConstantsTypeColumn(this);
	column->SetName(name);
	column->SetType(type);
	AddColumn(column);
}

DConstantsTypeColumn * DConstantsTypeTable::RemoveColumn( int order )
{
	if(order > mColumns.size() && mColumns.size()>0)
	{
		//TODO print error;
		return NULL;
	}

	std::sort(mColumns.begin(), mColumns.end()); //sort vector by order;

	//C++ are surprisingly dump language...
	vector<DConstantsTypeColumn *>::iterator it= mColumns.begin();
	DConstantsTypeColumn *col = *it;
	mColumns.erase(it + order);
	return *it;

}

int DConstantsTypeTable::GetNRows() const
{
	return mNRows;
}

void DConstantsTypeTable::SetNRows( int val )
{
	mNRows = val;
}

#pragma region Setters and getters

    DDirectory *DConstantsTypeTable::GetDirectory() const
    {
        return mDirectory;
    }

    int DConstantsTypeTable::GetDirectoryId() const
    {
        return mDirectoryId;
    }

    string DConstantsTypeTable::GetFullPath() const
    {
        return mFullPath;
    }

    int DConstantsTypeTable::GetId() const
    {
        return mId;
    }

    string DConstantsTypeTable::GetName() const
    {
        return mName;
    }

void DConstantsTypeTable::SetDirectory(DDirectory *fDirectory)
{
	this->mDirectory = fDirectory;
	
	 //now this name affects full path...
	if(mDirectory!=NULL)	
	{
		mFullPath.assign(DStringUtils::CombinePath(mDirectory->GetFullPath(), mName));
	}
	else
	{
		mFullPath.assign("");
	}
}

void DConstantsTypeTable::SetDirectoryId(int fDirectoryId)
{
	this->mDirectoryId = fDirectoryId;
}

void DConstantsTypeTable::SetFullPath(string fFullPath)
{
	this->mFullPath = fFullPath;
}

void DConstantsTypeTable::SetId(dbkey_t id)
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

void DConstantsTypeTable::SetName(const string& name)
{
	mName.assign(name);
	
	//now this name affects full path...
	if(mDirectory!=NULL)	
	{
		mFullPath.assign(DStringUtils::CombinePath(mDirectory->GetFullPath(), name));
	}
	else
	{
		mFullPath.assign("");
	}
}

	time_t DConstantsTypeTable::GetCreatedTime() const
	{
		return mCreatedTime;
	}

	void DConstantsTypeTable::SetCreatedTime( time_t val )
	{
		mCreatedTime = val;
	}

	std::string DConstantsTypeTable::GetComment() const
	{
		return mComment;
	}

	void DConstantsTypeTable::SetComment(const string& val )
	{
		mComment.assign(val);
	}

	time_t DConstantsTypeTable::GetModifiedTime() const
	{
		return mUpdateTime;
	}

	void DConstantsTypeTable::SetModifiedTime( time_t val )
	{
		mUpdateTime = val;
	}

	void DConstantsTypeTable::ClearColumns()
	{
		mColumns.clear();
	}

	int DConstantsTypeTable::GetNColumnsFromDB() const
	{
		return mNColumnsFromDB;
	}

	void DConstantsTypeTable::SetNColumnsFromDB( int val )
	{
		mNColumnsFromDB = val;
	}

	vector<string> DConstantsTypeTable::GetColumnNames() const
	{
		//future result
		vector<string> names;

		//and just a loop through columns
		vector<DConstantsTypeColumn *>::const_iterator iter = mColumns.begin();
		while(iter<mColumns.end())
		{
			names.push_back((*iter)->GetName());
			iter++;
		}
		return names;
	}

	vector<string> DConstantsTypeTable::GetColumnTypeStrings() const
	{
		//future result
		vector<string> types;

		//and just a loop through columns
		vector<DConstantsTypeColumn *>::const_iterator iter = mColumns.begin();
		while(iter<mColumns.end())
		{
			types.push_back((*iter)->GetTypeString());
			iter++;
		}
		return types;
	}




#pragma endregion Setters and getters


}

