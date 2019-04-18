#ifndef DCCDBGlobalMutex_h__
#define DCCDBGlobalMutex_h__


#include <string>
#include <stdlib.h>
#include <map>
#include <new>

#include "CCDB/Globals.h"

using namespace std;

#ifdef _MSC_VER
    #include "winpthreads.h"
#else   // GCC?
    #include <pthread.h>
#endif


namespace ccdb
{

/** 
 * This class is obsolete concept of constants reading synchronization
 * Don't use it. It will be deleted. 
 * With time...
 *                                                                     
 */
class CCDBGlobalMutex
{
public:
	/** @brief Singleton instance for global mutex-es
	 *
	 * @return   ConsoleContext* instance
	 */
	static CCDBGlobalMutex* Instance();
	
	void ReadConstantsLock();
	void ReadConstantsRelease();

	void LogLock();
	void LogRelease();

	static unsigned int GetCurrentThreadId();
	~CCDBGlobalMutex();
protected:
private:
	CCDBGlobalMutex();										/// Private so that it can  not be called
	CCDBGlobalMutex(CCDBGlobalMutex const&){}			// / copy constructor is private
	CCDBGlobalMutex& operator=(CCDBGlobalMutex const&);	/// assignment operator is private
		
	static CCDBGlobalMutex* mInstance;					    ///Main and only singleton instance

	pthread_mutex_t mReadConstsMutex;	    ///read constants mutex posix
    pthread_mutex_t mLogMutex;	    ///read constants mutex posix

	void Lock(pthread_mutex_t * mutex);     ///locks mutex by handle
	void Release(pthread_mutex_t * mutex);  ///releases mutex by handle


};
}
#endif // DCCDBGlobalMutex_h__
