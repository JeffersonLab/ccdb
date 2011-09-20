#ifndef DCCDBGlobalMutex_h__
#define DCCDBGlobalMutex_h__


#include <string>
#include <stdlib.h>
#include <map>
#include <new>
#include "DCCDBGlobals.h"

using namespace std;

#ifdef WIN32
#include "winpthreads.h"
#else //posix
#include <pthread.h>
#endif



namespace ccdb
{

/** 
 * This class is obsolete concept of constants reading syncronization
 * Don't use it. It will be deleted. 
 * With time...
 *                                                                     
 */
class DCCDBGlobalMutex
{
public:
	/** @brief Singleton instance for global mutex-es
	 *
	 * @return   DConsoleContext* instance
	 */
	static DCCDBGlobalMutex* Instance();
	
	void ReadConstantsLock();
	void ReadConstantsRelease();

	void LogLock();
	void LogRelease();

	static unsigned int GetCurrentThreadId();
	~DCCDBGlobalMutex();
protected:
private:
	DCCDBGlobalMutex();										/// Private so that it can  not be called
	DCCDBGlobalMutex(DCCDBGlobalMutex const&){};			/// copy constructor is private
	DCCDBGlobalMutex& operator=(DCCDBGlobalMutex const&);	/// assignment operator is private
		
	static DCCDBGlobalMutex* mInstance;					    ///Main and only singleton instance

	pthread_mutex_t mReadConstsMutex;	    ///read constants mutex posix

	void Lock(pthread_mutex_t * mutex);     ///locks mutex by handle
	void Release(pthread_mutex_t * mutex);  ///releases mutex by handle


};
}
#endif // DCCDBGlobalMutex_h__