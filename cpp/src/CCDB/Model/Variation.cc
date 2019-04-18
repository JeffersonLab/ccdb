/*
 * Variation.cpp
 *
 *  Created on: Sep 28, 2010
 *      Author: romanov
 */

#include "CCDB/Model/Variation.h"
#include "CCDB/Model/ObjectsOwner.h"

namespace ccdb {

Variation::Variation( ObjectsOwner * owner/*=NULL*/, DataProvider *provider/*=NULL*/ )
:StoredObject(owner, provider)
{
	mId=0;			//! database table uniq id;
	mCreatedTime=0;	//! Creation Time 
	mUpdateTime=0;		//! Update Time 
    mParentDbId = 0;
    mParent = NULL;
}



Variation::~Variation() {
	// TODO Auto-generated destructor stub
}

}
