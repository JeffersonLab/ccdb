#include "Model/DEventRange.h"
#include "DStoredObject.h"

namespace ccdb{

DEventRange::DEventRange( DObjectsOwner * owner/*=NULL*/, DDataProvider *provider/*=NULL*/ ):
DStoredObject(owner, provider)
{
	mId=0;		//database table uniq id;
	mCreatedTime =0;	//creationTime time
	mUpdateTime =0;		//mUpdateTime time
}


DEventRange::~DEventRange(void)
{
}
}//namespace ccdb{

