/*
 * DAssignment.cpp
 *
 *  Created on: Sep 28, 2010
 *      Author: romanov
 */

#include "Model/DAssignment.h"
#include "DStringUtils.h"
#include "DCCDBGlobals.h"

#include <vector>
#include <sstream>
#include <assert.h>

using namespace ccdb;
using namespace std;


//______________________________________________________________________________
ccdb::DAssignment::DAssignment( DObjectsOwner * owner/*=NULL*/, DDataProvider *provider/*=NULL*/ )
:DStoredObject(owner, provider)
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
ccdb::DAssignment::~DAssignment() {
	// TODO Auto-generated destructor stub
}

//______________________________________________________________________________
bool ccdb::DAssignment::MapData(vector<map<string,string> > & mappedData, const vector<string>& data, const vector<string>& columns )
{
	//check error
    //TODO print error;
    assert(data.size()!=0);
    assert(columns.size() !=0);

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
bool ccdb::DAssignment::MapData( vector<vector<string> > & mappedData, const vector<string>& data, int columnsNum )
{
	//check error
    //TODO error report?
    assert(data.size()!=0);
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
void ccdb::DAssignment::SplitData( vector<string>& outArray,string blob )
{
	//split blob from DB to tokens and data
	DStringUtils::Split(blob,outArray, "|");
}

//______________________________________________________________________________
unsigned int ccdb::DAssignment::GetVariationId() const
{
	return mVariationId;
}

//______________________________________________________________________________
void ccdb::DAssignment::SetVariationId( unsigned int val )
{
	mVariationId = val;
}

//______________________________________________________________________________
unsigned int ccdb::DAssignment::GetRunRangeId() const
{
	return mRunRangeId;
}

//______________________________________________________________________________
void ccdb::DAssignment::SetRunRangeId( unsigned int val )
{
	mRunRangeId = val;
}

//______________________________________________________________________________
unsigned int ccdb::DAssignment::GetDataVaultId() const
{
	return mDataVaultId;
}

//______________________________________________________________________________
void ccdb::DAssignment::SetDataVaultId( unsigned int val )
{
	mDataVaultId = val;
}

//______________________________________________________________________________
unsigned int ccdb::DAssignment::GetEventRangeId() const
{
	return mEventRangeId;
}

//______________________________________________________________________________
void ccdb::DAssignment::SetEventRangeId( unsigned int val )
{
	mEventRangeId = val;
}

//______________________________________________________________________________
int ccdb::DAssignment::GetRequestedRun() const
{
	return mRequestedRun;
}

//______________________________________________________________________________
void ccdb::DAssignment::SetRequestedRun( int val )
{
	mRequestedRun = val;
}


//______________________________________________________________________________
DRunRange * ccdb::DAssignment::GetRunRange() const
{
	return mRunRange;
}

//______________________________________________________________________________
void ccdb::DAssignment::SetRunRange( DRunRange * val )
{
	mRunRange = val;
}

//______________________________________________________________________________
DEventRange * ccdb::DAssignment::GetEventRange() const
{
	return mEventRange;
}


//______________________________________________________________________________
void ccdb::DAssignment::SetEventRange( DEventRange * val )
{
	mEventRange = val;
}


//______________________________________________________________________________
DVariation * ccdb::DAssignment::GetVariation() const
{
	return mVariation;
}


//______________________________________________________________________________
void ccdb::DAssignment::SetVariation( DVariation * val )
{
	mVariation = val;
}


//______________________________________________________________________________
string ccdb::DAssignment::VectorToBlob(const vector<string>& values)
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
vector<map<string,string> > ccdb::DAssignment::GetMappedData() const
{
	vector<map<string,string> > result;
	GetMappedData(result);
	return result;
}


//______________________________________________________________________________
void ccdb::DAssignment::GetMappedData(vector<map<string, string> >& mappedData) const
{
    assert(mTypeTable !=NULL); // it is DataProvider work
    	
	//fill data
	MapData(mappedData, GetVectorData(), mTypeTable->GetColumnNames() );
	
}


//______________________________________________________________________________
std::vector<std::vector<std::string> > ccdb::DAssignment::GetData() const
{
	std::vector<std::vector<std::string> > result;
	GetData(result);
	return result;
}


//______________________________________________________________________________
void ccdb::DAssignment::GetData(std::vector<std::vector<std::string> >& data) const
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
	MapData(data, GetVectorData(), mTypeTable->GetNColumns());

}


//______________________________________________________________________________
string ccdb::DAssignment::DecodeBlobSeparator(string str)
{
	
	return DStringUtils::Replace("&delimeter;", CCDB_DATA_BLOB_DELIMETER, str);
}


//______________________________________________________________________________
string ccdb::DAssignment::EncodeBlobSeparator(string str)
{
	return DStringUtils::Replace(CCDB_DATA_BLOB_DELIMETER, "&delimeter;", str);
}


//______________________________________________________________________________
vector<string> ccdb::DAssignment::GetVectorData() const
{
	//Just create vector and run it through GetVectorData(vector<string>& vectorData)
	vector<string> vect;
	GetVectorData(vect);
	return vect;
}


//______________________________________________________________________________
void ccdb::DAssignment::GetVectorData(vector<string>& vectorData) const
{
	//split data
	vector<string> values = DStringUtils::Split(mRawData, CCDB_DATA_BLOB_DELIMETER);

	vectorData.clear();
	vector<string>::iterator iter=values.begin();
	while(iter<values.end())
	{	
		vectorData.push_back(DecodeBlobSeparator(*iter));
		iter++;
	}
}


