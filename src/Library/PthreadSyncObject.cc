#include "CCDB/PthreadSyncObject.h"

//______________________________________________________________________________
ccdb::PthreadSyncObject::PthreadSyncObject():ISyncObject()
{
    //CREATE sync object
    int result = pthread_mutex_init(&mPthreadMutex, NULL);

    //check object properly created
    if (result != 0) throw("ISyncObject* ccdb::PthreadSyncObject::CreateSyncObject() error creating mutex: %d\n", result);

}
//______________________________________________________________________________
ccdb::PthreadSyncObject::~PthreadSyncObject()
{
    //free mutex...
    pthread_mutex_destroy(&mPthreadMutex);
}

