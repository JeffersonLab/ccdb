#include "CCDB/PthreadMutex.h"
#include <stdexcept>



//______________________________________________________________________________
ccdb::PthreadMutex::PthreadMutex( PthreadSyncObject * obj) : IMutex(obj)
{
    //
    if(obj==NULL) throw std::logic_error("PthreadSyncObject == NULL in ccdb::PthreadMutex::PthreadMutex( PthreadSyncObject * obj)");
    mSyncObject = obj;
    mIsLocked = false;
}

///locks mutex by handle posix version


//______________________________________________________________________________
void ccdb::PthreadMutex::Lock()
{
    pthread_mutex_lock(mSyncObject->GetPthreadMutex());
    mIsLocked = true;
}

//______________________________________________________________________________
void ccdb::PthreadMutex::Release()
{ 
    ///releases mutex by handle posix version
    pthread_mutex_unlock(mSyncObject->GetPthreadMutex());
    mIsLocked = false;
}
