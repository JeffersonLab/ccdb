/*
 * RunRange.cpp
 * 
 *
 *  Created on: Sep 28, 2010
 *      Author: romanov
 */

#include "Model/DRunRange.h"

namespace ccdb {

DRunRange::DRunRange( DObjectsOwner * owner/*=NULL*/, DDataProvider *provider/*=NULL*/ )
:DStoredObject(owner, provider)
{
	mId = 0;
	mMin = 0;
	mMax = 0;
	mCreatedTime =0;
	mModifiedTime =0;

}

DRunRange::DRunRange(): DStoredObject(NULL, NULL)
{
	mId = 0;
	mMin = 0;
	mMax = 0;
	mCreatedTime =0;
	mModifiedTime =0;
}

DRunRange::~DRunRange() {
	// TODO Auto-generated destructor stub
}
int DRunRange::GetId() const
{
	//returns database id

	return mId;
}
int DRunRange::GetMax() const
{
	//returns maximal run number for this range
	return mMax;
}

int DRunRange::GetMin() const
{
	//returns the minimal run number of this range
	return mMin;
}

std::string DRunRange::GetName() const
{
	//gets the name of the run range

	return mName;
}

void DRunRange::SetMax( int val )
{
	//sets the maximal run number of this range

	SetIsChanged(true);
	mMax = val;
}

void DRunRange::SetMin( int val )
{
	//sets the minimal run number of this range

	SetIsChanged(true);
	mMin = val;
}

void DRunRange::SetName( std::string val )
{
	//sets the name of the run range
	
	SetIsChanged(true);
	mName = val;
}



void DRunRange::SetId( int val )
{
	//
	SetIsChanged(true);
	mId = val;
}

void DRunRange::SetRange( int min, int max )
{
	//sets the range window

	SetIsChanged(true);
	mMax = max;
	mMin = min;
}

std::string DRunRange::GetComment() const
{
	return mComment;
}

void DRunRange::SetComment( std::string val )
{
	mComment = val;
}




}
