#include "CCDB/Model/EventRange.h"
#include "CCDB/Model/StoredObject.h"

namespace ccdb{

EventRange::EventRange( ObjectsOwner * owner/*=NULL*/, DataProvider *provider/*=NULL*/ ):
StoredObject(owner, provider)
{
	mId=0;		//database table uniq id;
	mCreatedTime =0;	//creationTime time
	mUpdateTime =0;		//mUpdateTime time
}


EventRange::~EventRange(void)
{
}
}//namespace ccdb{

