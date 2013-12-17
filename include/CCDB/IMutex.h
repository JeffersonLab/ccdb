/** 
 * Every man should build a house, plant a tree, and have a son.
 * Every programmer in C++ has to implement string operations, synchronization context and pointer/memory management...
 * this is a synchronization context
 */
#ifndef IMutex_h__
#define IMutex_h__
#include "CCDB/ISyncObject.h"

namespace ccdb
{
    /**
     *  Abstract interface for Mutex synchronization 
     */
    class IMutex
    {
    public:
        IMutex(ISyncObject *){}
        virtual ~IMutex(){}

        
        virtual void Lock() = 0;     /// Locks current SyncObject 
        virtual void Release() = 0;  /// Releases lock for current SyncObject

    protected:
        virtual bool IsLocked() = 0; ///Check if the Mutex is locked right now

    };
}
#endif // IMutex_h__

