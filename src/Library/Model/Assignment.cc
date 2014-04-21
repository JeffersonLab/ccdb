/*
 * Assignment.cpp
 *
 *  Created on: Sep 28, 2010
 *      Author: romanov
 */
#include <vector>
#include <sstream>
#include <assert.h>

#include "CCDB/Model/Assignment.h"
#include "CCDB/Helpers/StringUtils.h"
#include "CCDB/Globals.h"

using namespace ccdb;
using namespace std;


//______________________________________________________________________________
ccdb::Assignment::Assignment( ObjectsOwner * owner/*=NULL*/, DataProvider *provider/*=NULL*/ )
:StoredObject(owner, provider)
{
	mRawData = string(); 	// data blob
	mId=0;					// id in database
	mDataBlobId   = 0;		// blob id in database
	mVariationId  = 0;		// database ID of variation
	mRunRangeId   = 0;		// database ID of run range
	mDataVaultId  = 0;		// database ID of data blob
	mEventRangeId = 0;		// event range ID
	mRequestedRun = 0;		// Run than was requested for user

	mRunRange   = NULL;		// Run range object, is NULL if not set
	mEventRange = NULL;		// Event range object, is NULL if not set
	mVariation  = NULL;		// Variation object, is NULL if not set
	mTypeTable  = NULL;		// Reference to type table
}


//______________________________________________________________________________
ccdb::Assignment::~Assignment() {
	// TODO Auto-generated destructor stub
}

//______________________________________________________________________________
bool ccdb::Assignment::MapData(vector<map<string,string> > & mappedData, const vector<string>& data, const vector<string>& columns )
{
	//Validate what we have
	assert(columns.size() != 0);
	if (data.size() == 0)
	{
		mappedData.clear();
		return true;
	}

	//loop
	int rows = data.size() / columns.size();
	vector<string>::const_iterator dataIter= data.begin();
	for (int rowIter = 0; rowIter < rows ; rowIter++)
	{	
		map<string,string> line;
		for(vector<string>::const_iterator it=columns.begin(); it<columns.end(); ++it,++dataIter)
		{
			line[*it]=*dataIter;
		}
		mappedData.push_back(line);
	}
	return true;
}

//______________________________________________________________________________
bool ccdb::Assignment::MapData( vector<vector<string> > & mappedData, const vector<string>& data, int columnsNum )
{
	//Validate what we have
	if (data.size() == 0)
	{
		mappedData.clear();
		return true;
	}
    assert(columnsNum!=0);

	//loop
	int rows = data.size() / columnsNum;

    mappedData.resize(rows);	
	for (int rowIter = 0; rowIter < rows ; rowIter++)
	{		
        mappedData[rowIter].resize(columnsNum);
		for(int colIter=0; colIter <columnsNum; colIter++)
		{
            mappedData[rowIter][colIter] = data[rowIter*columnsNum + colIter];
        }
	}
	return true;
}

//______________________________________________________________________________
unsigned int ccdb::Assignment::GetVariationId() const
{
	return mVariationId;
}

//______________________________________________________________________________
void ccdb::Assignment::SetVariationId( unsigned int val )
{
	mVariationId = val;
}

//______________________________________________________________________________
unsigned int ccdb::Assignment::GetRunRangeId() const
{
	return mRunRangeId;
}

//______________________________________________________________________________
void ccdb::Assignment::SetRunRangeId( unsigned int val )
{
	mRunRangeId = val;
}

//______________________________________________________________________________
unsigned int ccdb::Assignment::GetDataVaultId() const
{
	return mDataVaultId;
}

//______________________________________________________________________________
void ccdb::Assignment::SetDataVaultId( unsigned int val )
{
	mDataVaultId = val;
}

//______________________________________________________________________________
unsigned int ccdb::Assignment::GetEventRangeId() const
{
	return mEventRangeId;
}

//______________________________________________________________________________
void ccdb::Assignment::SetEventRangeId( unsigned int val )
{
	mEventRangeId = val;
}

//______________________________________________________________________________
int ccdb::Assignment::GetRequestedRun() const
{
	return mRequestedRun;
}

//______________________________________________________________________________
void ccdb::Assignment::SetRequestedRun( int val )
{
	mRequestedRun = val;
}


//______________________________________________________________________________
RunRange * ccdb::Assignment::GetRunRange() const
{
	return mRunRange;
}

//______________________________________________________________________________
void ccdb::Assignment::SetRunRange( RunRange * val )
{
	mRunRange = val;
}

//______________________________________________________________________________
EventRange * ccdb::Assignment::GetEventRange() const
{
	return mEventRange;
}


//______________________________________________________________________________
void ccdb::Assignment::SetEventRange( EventRange * val )
{
	mEventRange = val;
}


//______________________________________________________________________________
Variation * ccdb::Assignment::GetVariation() const
{
	return mVariation;
}


//______________________________________________________________________________
void ccdb::Assignment::SetVariation( Variation * val )
{
	mVariation = val;
}


//______________________________________________________________________________
string ccdb::Assignment::VectorToBlob(const vector<string>& values)
{
	string result("");
	if(values.size() <=0)
	{
		//TODO report error
		return result;
	}
	//stringstream sstream;
	
	//loop through blob
	vector<string>::const_iterator iter=values.begin();
	while(iter<values.end())
	{
		result.append(EncodeBlobSeparator(*iter));
		iter++;
		if(iter!=values.end()) result.append(CCDB_DATA_BLOB_DELIMETER); //see CCDB_DATA_BLOB_DELIMETER in CCDBGlobals.h
	}
	
	return result;
}


//______________________________________________________________________________
vector<map<string,string> > ccdb::Assignment::GetMappedData() const
{
	vector<map<string,string> > result;
	GetMappedData(result);
	return result;
}


//______________________________________________________________________________
void ccdb::Assignment::GetMappedData(vector<map<string, string> >& mappedData) const
{
    assert(mTypeTable !=NULL); // it is DataProvider work
    	
	//fill data
	MapData(mappedData, GetVectorData(), mTypeTable->GetColumnNames() );
	
}


//______________________________________________________________________________
std::vector<std::vector<std::string> > ccdb::Assignment::GetData() const
{
	std::vector<std::vector<std::string> > result;
	GetData(result);
	return result;
}


//______________________________________________________________________________
void ccdb::Assignment::GetData(std::vector<std::vector<std::string> >& data) const
{
	if(mTypeTable == NULL)
	{
		//WARNING table type not loaded
		return;
	}

	if(mTypeTable->GetColumns().size()<=0)
	{
		//WARNING columns not loaded
	}

	//clear before filling
	data.clear();

	//fill data
	MapData(data, GetVectorData(), mTypeTable->GetColumnsCount());
}


//______________________________________________________________________________
string ccdb::Assignment::DecodeBlobSeparator(string str)
{
	
	return StringUtils::Replace("&delimiter;", CCDB_DATA_BLOB_DELIMETER, str);
}


//______________________________________________________________________________
string ccdb::Assignment::EncodeBlobSeparator(string str)
{
	return StringUtils::Replace(CCDB_DATA_BLOB_DELIMETER, "&delimiter;", str);
}


//______________________________________________________________________________
vector<string> ccdb::Assignment::GetVectorData() const
{
	//Just create vector and run it through GetVectorData(vector<string>& vectorData)
	vector<string> vect;
	GetVectorData(vect);
	return vect;
}


//______________________________________________________________________________
void ccdb::Assignment::GetVectorData(vector<string>& vectorData) const
{
	//split data
	vectorData.clear();
	vector<string>::const_iterator iter = mVectorData.begin();
	while (iter<mVectorData.end())
	{	
		vectorData.push_back(DecodeBlobSeparator(*iter));
		iter++;
	}
}

//______________________________________________________________________________
void ccdb::Assignment::SetRawData(std::string val)
{
	mVectorData.clear();
	mRows.clear();
	mRawData = val;

	mVectorData = StringUtils::Split(mRawData, CCDB_DATA_BLOB_DELIMETER);
	for (size_t i = 0; i < mVectorData.size(); i++)
	{
		mVectorData[i] = DecodeBlobSeparator(mVectorData[i]); //Decode blob separators
	}
}

std::string ccdb::Assignment::GetValue(string columnName)
{
	if (mRows.size() == 0)
	{
		//fill data
		MapData(mRows, GetVectorData(), mTypeTable->GetColumnNames());
	}
	return mRows[0][columnName];
}

std::string ccdb::Assignment::GetValue(size_t rowIndex, string columnName)
{
	if (mRows.size() == 0)
	{
		//fill data
		MapData(mRows, GetVectorData(), mTypeTable->GetColumnNames());
	}
	return GetMappedData()[0][columnName];
}

std::string ccdb::Assignment::GetValue(size_t rowIndex, size_t columnIndex)
{
	return GetData()[rowIndex][columnIndex];
}

std::string ccdb::Assignment::GetValue(size_t columnIndex)
{
	return GetVectorData()[columnIndex];
}

ConstantsTypeColumn::ColumnTypes ccdb::Assignment::GetValueType(const string& columnName)
{
	return mTypeTable->GetColumnsByName()[columnName]->GetType();
}








