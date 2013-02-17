
#ifndef PthreadSyncObject_h__
#define PthreadSyncObject_h__

#include "CCDB/Globals.h"
#include "CCDB/ISyncObject.h"


#ifdef WIN32
#include "winpthreads.h"
#else //posix
#include <pthread.h>
#endif

namespace ccdb
{

    /**
     *  Synchronization object for PThread 
     */
    class PthreadSyncObject: public ISyncObject
    {
    public:
        PthreadSyncObject();
        virtual ~PthreadSyncObject();
        pthread_mutex_t *GetPthreadMutex() { return &mPthreadMutex; }
    private:
        pthread_mutex_t mPthreadMutex;	    ///mutex object posix
    };
}
#endif // PthreadSyncObject_h__
