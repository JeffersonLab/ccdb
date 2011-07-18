#include "UserAPI/DCCDBGlobalMutex.h"
#pragma warning(disable: 4996)
#include <iostream>
#include <stdio.h>

using namespace std;
using namespace ccdb;

//pthread_mutex_t ccdb::DCCDBGlobalMutex::mReadConstsMutex;	///read constants mutex posix

// Global static pointer used to ensure a single instance of the class.
DCCDBGlobalMutex* ccdb::DCCDBGlobalMutex::mInstance = NULL; 


//______________________________________________________________________________
DCCDBGlobalMutex* ccdb::DCCDBGlobalMutex::Instance()
{
    /** This function is called to create an instance of the class.
    Calling the constructor publicly is not allowed. The constructor
    is private and is only called by this Instance function.
    */
    if (!mInstance)   // Only allow one instance of class to be generated.
		mInstance = new DCCDBGlobalMutex();
    
	return mInstance;
}


//______________________________________________________________________________
ccdb::DCCDBGlobalMutex::DCCDBGlobalMutex()
{   
	int result = pthread_mutex_init(&mReadConstsMutex, NULL);
    
	if (result != 0) 
	{
		fprintf(stderr, "CreateMutex ccdb::DCCDBGlobalMutex::ReadConstsMutex error: %d\n", result);
	}
}


//______________________________________________________________________________
void ccdb::DCCDBGlobalMutex::Lock(pthread_mutex_t * mutex)
{
	///locks mutex by handle posix version
	pthread_mutex_lock(mutex);
}


//______________________________________________________________________________
void ccdb::DCCDBGlobalMutex::Release(pthread_mutex_t * mutex)
{ 
	///releases mutex by handle posix version
     cout<<"Release"<<endl;
	pthread_mutex_unlock(mutex);
}


//______________________________________________________________________________
void ccdb::DCCDBGlobalMutex::ReadConstantsLock()
{
	Lock(&mReadConstsMutex);
}


//______________________________________________________________________________
void ccdb::DCCDBGlobalMutex::ReadConstantsRelease()
{
	Release(&mReadConstsMutex);
}


//______________________________________________________________________________
void ccdb::DCCDBGlobalMutex::LogLock()
{
	fprintf(stderr, "Not implemented ccdb::DCCDBGlobalMutex::LogLock()");
}


//______________________________________________________________________________
void ccdb::DCCDBGlobalMutex::LogRelease()
{
	fprintf(stderr, "Not implemented ccdb::DCCDBGlobalMutex::LogRelease()");
}


//______________________________________________________________________________
unsigned int ccdb::DCCDBGlobalMutex::GetCurrentThreadId()
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
}

//______________________________________________________________________________
ccdb::DCCDBGlobalMutex::~DCCDBGlobalMutex()
{
	pthread_mutex_destroy(&mReadConstsMutex);
}









