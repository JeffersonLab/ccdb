/*
 * Variation.cpp
 *
 *  Created on: Sep 28, 2010
 *      Author: romanov
 */

#include "Model/DVariation.h"
#include "DObjectsOwner.h"

namespace ccdb {

DVariation::DVariation( DObjectsOwner * owner/*=NULL*/, DDataProvider *provider/*=NULL*/ )
:DStoredObject(owner, provider)
{
	mId=0;			//! database table uniq id;
	mCreatedTime=0;	//! Creation Time 
	mUpdateTime=0;		//! Update Time 
}



DVariation::~DVariation() {
	// TODO Auto-generated destructor stub
}

}
