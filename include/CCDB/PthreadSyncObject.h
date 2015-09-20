
#ifndef PthreadSyncObject_h__
#define PthreadSyncObject_h__

#include "CCDB/Globals.h"
#include "CCDB/ISyncObject.h"


#ifdef _MSC_VER
#include "winpthreads.h"
#else   // GCC?
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
