#include "CCDB/GlobalMutex.h"
#pragma warning(disable: 4996)
#include <iostream>
#include <stdio.h>

using namespace std;
using namespace ccdb;



// Global static pointer used to ensure a single instance of the class.
CCDBGlobalMutex* ccdb::CCDBGlobalMutex::mInstance = NULL; 


//______________________________________________________________________________
CCDBGlobalMutex* ccdb::CCDBGlobalMutex::Instance()
{
    /** This function is called to create an instance of the class.
    Calling the constructor publicly is not allowed. The constructor
    is private and is only called by this Instance function.
    */
    if (!mInstance)   // Only allow one instance of class to be generated.
		mInstance = new CCDBGlobalMutex();
    
	return mInstance;
}


//______________________________________________________________________________
ccdb::CCDBGlobalMutex::CCDBGlobalMutex()
{   
	int result = pthread_mutex_init(&mReadConstsMutex, NULL);
    
	if (result != 0) 
	{
		fprintf(stderr, "CreateMutex ccdb::DCCDBGlobalMutex::ReadConstsMutex error: %d\n", result);
	}

    result = pthread_mutex_init(&mReadConstsMutex, NULL);

    if (result != 0) 
    {
        fprintf(stderr, "CreateMutex ccdb::DCCDBGlobalMutex::ReadConstsMutex error: %d\n", result);
    }
}


//______________________________________________________________________________
void ccdb::CCDBGlobalMutex::Lock(pthread_mutex_t * mutex)
{
	///locks mutex by handle posix version
	pthread_mutex_lock(mutex);
}


//______________________________________________________________________________
void ccdb::CCDBGlobalMutex::Release(pthread_mutex_t * mutex)
{ 
	///releases mutex by handle posix version
	pthread_mutex_unlock(mutex);
}


//______________________________________________________________________________
void ccdb::CCDBGlobalMutex::ReadConstantsLock()
{
	Lock(&mReadConstsMutex);
}


//______________________________________________________________________________
void ccdb::CCDBGlobalMutex::ReadConstantsRelease()
{
	Release(&mReadConstsMutex);
}


//______________________________________________________________________________
void ccdb::CCDBGlobalMutex::LogLock()
{
	Lock(&mLogMutex);
}


//______________________________________________________________________________
void ccdb::CCDBGlobalMutex::LogRelease()
{
	Release(&mLogMutex);
}


//______________________________________________________________________________
unsigned int ccdb::CCDBGlobalMutex::GetCurrentThreadId()
{
    /*
    Since pthreads do not need to be implemented with Linux threads (or kernel threads at all, for that matter), 
    and some implementations are entirely user-level or mixed, the pthreads interface does not provide functions 
    to access these implementation details, as those would not be portable (even across pthreads implementations 
    on Linux). Thread libraries that use those could provide this as an extension, but there do not seem to be 
    any that do. 

    We will think about better implementation later
    */
    fprintf(stderr, "Not implemented ccdb::GetCurrentThreadId");
    return 0;
}

//______________________________________________________________________________
ccdb::CCDBGlobalMutex::~CCDBGlobalMutex()
{
	pthread_mutex_destroy(&mReadConstsMutex);
    pthread_mutex_destroy(&mLogMutex);
}









