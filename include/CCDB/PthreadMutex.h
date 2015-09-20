#include "CCDB/ISyncObject.h"
#include "CCDB/IMutex.h"
#include "CCDB/PthreadSyncObject.h"

#ifdef _MSC_VER
#include "winpthreads.h"
#else   // GCC?
#include <pthread.h>
#endif

namespace ccdb
{
    /**
     *  Abstract interface for Mutex synchronization 
     */
    class PthreadMutex:public IMutex
    {
    public:
        PthreadMutex(PthreadSyncObject *);
        ~PthreadMutex(){  if(IsLocked()) Release(); if(mSyncObject) delete mSyncObject; }
        
        virtual void Lock();     /// Locks current SyncObject 
        virtual void Release();  /// Releases lock for current SyncObject

    protected:
        virtual bool IsLocked(){return mIsLocked;} ///Check if the Mutex is locked right now

    private:
         PthreadSyncObject * mSyncObject;
         volatile bool mIsLocked;
    };
}
