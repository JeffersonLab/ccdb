#include "CCDB/Model/StoredObject.h"
#include "CCDB/Providers/DataProvider.h"

using namespace ccdb;
//class DDataProvider;

unsigned long ccdb::StoredObject::mLastTempId=0;

ccdb::StoredObject::StoredObject( ObjectsOwner * owner/*=NULL*/, DataProvider *provider/*=NULL*/ )
{
	mOwner = NULL;
	mTempId = ++mLastTempId;
	mProvider = provider;
	SetOwner(owner, owner!=NULL);
}

ccdb::StoredObject::~StoredObject(void)
{
	//Ok! The object is going to be deleted!
	//Maybe somebody called a destructor, but 
	// the object is provider owned?
	if(mIsOwned && mOwner!=NULL)
	{	
		//If so, We must release the ownship...
		mOwner->ReleaseOwnership(this);
	}
}

void ccdb::StoredObject::SetOwner( ObjectsOwner * val, bool isOwned )
{
	//save old provider
	ObjectsOwner *oldOwner = mOwner;
	
	// It is important to set mOwner and mIsProviderOwned here!!!
	// When something call this function, it calls mOwner->BeOwner(this);
	// BeOwner() looks if the provider of stored objects is 'this' and isOwned is 'true'
	// Then it adds (checks) the objects to its owning list. Othervise it first calls 
	// SetProvider( DDataProvider * val, bool isOwned ) to be shure that all is set. 
	// Thus if you dont set mOwner and mIsProviderOwned here you'll get infinite recursion
	mOwner = val;					
	mIsOwned = isOwned; 
	
	if(val!=NULL && isOwned)
	{
		// Now we check maybe the object was owned by another provider
		// thus we may want to release the ownership...
		if(val!=NULL && oldOwner!=0 && oldOwner!=val)
		{
			oldOwner->ReleaseOwnership(this);
			
			//lets set the flag after ReleaseOwnership()
			mIsOwned = true;
		}

		//add object to provider's ownership list
		mOwner->BeOwner(this);
	}
	else
	{
		mIsOwned = false;
	}

}

void ccdb::StoredObject::ReleaseOwning()
{
	//if we have provider to release...
	if(mOwner!=NULL)
	{
		mOwner->ReleaseOwnership(this);
		//lets set the flag after ReleaseOwnership()
		mIsOwned = false;
	}

}

void ccdb::StoredObject::ReleaseOwningRecursive()
{
	//TODO: Impement method for objects like directories
	ReleaseOwning();
}

unsigned long ccdb::StoredObject::GetTempUID() const
{
	return mTempId;
}
