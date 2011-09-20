#include "CCDB/Model/ObjectsOwner.h"

namespace ccdb
{

ObjectsOwner::ObjectsOwner()
{
}

ObjectsOwner::~ObjectsOwner()
{
	//delete owned objects
	if(mOwnedObjects.size()>0)	//do we need to delete objects?
	{

		//iterate through list and delete
		map<unsigned long, StoredObject *>::iterator it = mOwnedObjects.begin();
		while(it != mOwnedObjects.end())
		{
			StoredObject *obj = it->second;
			mOwnedObjects.erase(it++);
			delete obj;
		}
	}
}


void ObjectsOwner::BeOwner( StoredObject * object )
{
	//check and set
	if(object->GetOwner()!=this || !object->GetIsOwned())
	{
		//this will call this function once again but 
		//with this provider and true flag
		object->SetOwner(this, true);
	}
	else
	{
		//if we are here the only need is to add object to a list
		mOwnedObjects[object->GetTempUID()]=object;
	}
}

void ObjectsOwner::ReleaseOwnership( StoredObject * object )
{
	//get iterator
	map<unsigned long, StoredObject *>::iterator it=mOwnedObjects.find(object->GetTempUID());

	//if it is found
	if(it!=mOwnedObjects.end())
	{	
		//check and release
		if(it->second->GetOwner() == this && it->second->GetIsOwned())
		{
			it->second->SetOwner(this, false);
		}

		//delete from the list
		mOwnedObjects.erase(it);
	}
}

bool ObjectsOwner::IsOwner( StoredObject * object )
{
	if((object!=NULL) && (object->GetOwner()==this) && object->GetIsOwned())	 return true;
	return false;
}

}

