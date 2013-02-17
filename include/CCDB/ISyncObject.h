/** 
 * Every man should build a house, plant a tree, and have a son.
 * Every programmer in C++ has to implement string operations, synchronization context and pointer/memory management...
 * this is a synchronization context
 */

#ifndef ISyncObject_h__
#define ISyncObject_h__

namespace ccdb
{
    class ISyncObject
    {
    public:
        ISyncObject(){}
        virtual ~ISyncObject(){}
        //virtual static ISyncObject* CreateSyncObject() = 0;

    };
}
#endif // ISyncObject_h__
