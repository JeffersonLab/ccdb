/*
 * RunRange.cpp
 * 
 *
 *  Created on: Sep 28, 2010
 *      Author: romanov
 */

#include "CCDB/Model/RunRange.h"

namespace ccdb {

RunRange::RunRange( ObjectsOwner * owner/*=NULL*/, DataProvider *provider/*=NULL*/ )
:StoredObject(owner, provider)
{
	mId = 0;
	mMin = 0;
	mMax = 0;
	mCreatedTime =0;
	mModifiedTime =0;

}

RunRange::RunRange(): StoredObject(NULL, NULL)
{
	mId = 0;
	mMin = 0;
	mMax = 0;
	mCreatedTime =0;
	mModifiedTime =0;
}

RunRange::~RunRange() {
	// TODO Auto-generated destructor stub
}
int RunRange::GetId() const
{
	//returns database id

	return mId;
}
int RunRange::GetMax() const
{
	//returns maximal run number for this range
	return mMax;
}

int RunRange::GetMin() const
{
	//returns the minimal run number of this range
	return mMin;
}

std::string RunRange::GetName() const
{
	//gets the name of the run range

	return mName;
}

void RunRange::SetMax( int val )
{
	//sets the maximal run number of this range

	SetIsChanged(true);
	mMax = val;
}

void RunRange::SetMin( int val )
{
	//sets the minimal run number of this range

	SetIsChanged(true);
	mMin = val;
}

void RunRange::SetName( std::string val )
{
	//sets the name of the run range
	
	SetIsChanged(true);
	mName = val;
}



void RunRange::SetId( int val )
{
	//
	SetIsChanged(true);
	mId = val;
}

void RunRange::SetRange( int min, int max )
{
	//sets the range window

	SetIsChanged(true);
	mMax = max;
	mMin = min;
}

std::string RunRange::GetComment() const
{
	return mComment;
}

void RunRange::SetComment( std::string val )
{
	mComment = val;
}




}
