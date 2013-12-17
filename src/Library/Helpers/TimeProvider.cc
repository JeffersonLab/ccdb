/********************* */
/*! \file clock_gettime.c
** \verbatim
** Original author: Morgan Deters
** Major contributors: none
** Minor contributors (to current version): none
** This file is part of the CVC4 project.
** Copyright (c) 2009-2013 New York University and The University of Iowa
** See the file COPYING in the top-level source directory for licensing
** information.\endverbatim
**
** \brief Replacement for clock_gettime() for systems without it (like
** Mac OS X)
**
** Replacement for clock_gettime() for systems without it (like Mac
** OS X).
**/


#include "CCDB/Helpers/TimeProvider.h"
#include "CCDB/Globals.h"

#if defined(D__MACOSX)
#  include <mach/clock.h>
#  include <mach/mach.h>
#  include <mach/mach_time.h>
#  include <unistd.h>
#elif defined(D__WIN32)
#  include <time.h>
#  include <windows.h>
#  include <stdint.h>
#else
#  include <time.h>
#  include <unistd.h>
#endif

time_t ccdb::TimeProvider::mUnitTestTime=0;     ///@see TimeUnitTest and SetUnitTestTime
bool ccdb::TimeProvider::mIsTimeUnitTest=false; ///@see TimeUnitTest and SetUnitTestTime


time_t ccdb::TimeProvider::GetUnixTimeStamp(ccdb::ClockSourcesEnum source)
{
    if(mIsTimeUnitTest) return mUnitTestTime;

#if defined(D__MACOSX)
	static double s_clockconv = 0.0;

	if( s_clockconv == 0.0 ) {
		mach_timebase_info_data_t tb;
		kern_return_t err = mach_timebase_info(&tb);
		if(err == 0) {
			s_clockconv = ((double) tb.numer) / tb.denom;
		} else {
			return 0;
		}
	}

	return (mach_absolute_time() * s_clockconv)/1000000000ul;

#elif defined(D__WIN32)

	FILETIME ft;
	GetSystemTimeAsFileTime(&ft);
	uint64_t nanos = ((((uint64_t)ft.dwHighDateTime) << 32) | ft.dwLowDateTime) * 100;
	return nanos / 1000000000ul;
	
#else //POSIX
	struct timespec spec;

	if(clock_gettime(source, &spec)) return 0;

	return spec.tv_sec;
#endif //D__MACOSX,D__WIN32 or POSIX
}


void ccdb::TimeProvider::Delay( time_t ms )
{
    /** @brief Delay in ms*/

#if defined(D__WIN32)
        Sleep( ms );
#else  /* presume POSIX */
        usleep( ms * 1000 );
#endif 
}
