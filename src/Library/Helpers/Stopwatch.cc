// @(#)root/base:$Id: TStopwatch.cxx 37631 2010-12-17 15:24:29Z rdm $
// Author: Fons Rademakers   11/10/95

/*************************************************************************
 * Copyright (C) 1995-2000, Rene Brun and Fons Rademakers.               *
 * All rights reserved.                                                  *
 *                                                                       *
 * For the licensing terms see $ROOTSYS/LICENSE.                         *
 * For the list of contributors see $ROOTSYS/README/CREDITS.             *
 *************************************************************************/

//////////////////////////////////////////////////////////////////////////
//                                                                      //
// TStopwatch                                                           //
//                                                                      //
// Stopwatch class. This class returns the real and cpu time between    //
// the start and stop events.                                           //
//                                                                      //
//////////////////////////////////////////////////////////////////////////

#include "CCDB/Helpers/Stopwatch.h"

#if defined(D__UNIX)
#include <sys/times.h>
#include <sys/time.h>
#include <unistd.h>

static double gTicks = 0;
#elif defined(WIN32)
//#include "TError.h"
const double gTicks = 1.0e-7;
#include <windows.h>
#endif

#include "stdio.h"

namespace ccdb
{


//______________________________________________________________________________
Stopwatch::Stopwatch()
{
   // Create a stopwatch and start it.

#ifdef D__UNIX
   if (gTicks <= 0.0)
      gTicks = (double)sysconf(_SC_CLK_TCK);
#endif

   fStopRealTime = 0;
   fStopCpuTime  = 0;

   Start();
}

//______________________________________________________________________________
void Stopwatch::Start(bool reset)
{
   // Start the stopwatch. If reset is kTRUE reset the stopwatch before
   // starting it (including the stopwatch counter).
   // Use kFALSE to continue timing after a Stop() without
   // resetting the stopwatch.

   if (reset) {
      fState         = kUndefined;
      fTotalCpuTime  = 0;
      fTotalRealTime = 0;
      fCounter       = 0;
   }
   if (!fState) 
   {
      fStartRealTime = GetRealTime();
      fStartCpuTime  = GetCPUTime();
   }
   fState = true;
   fCounter++;
}

//______________________________________________________________________________
void Stopwatch::Stop()
{
   // Stop the stopwatch.

   fStopRealTime = GetRealTime();
   fStopCpuTime  = GetCPUTime();

   if (fState) 
   {
      fTotalCpuTime  += fStopCpuTime  - fStartCpuTime;
      fTotalRealTime += fStopRealTime - fStartRealTime;
   }
   fState = false;
}

//______________________________________________________________________________
void Stopwatch::Continue()
{
   // Resume a stopped stopwatch. The stopwatch continues counting from the last
   // Start() onwards (this is like the laptimer function).

   if (!fState)  //stopped
   {
      fTotalCpuTime  -= fStopCpuTime  - fStartCpuTime;
      fTotalRealTime -= fStopRealTime - fStartRealTime;
   }

   fState = true;
}

//______________________________________________________________________________
double Stopwatch::RealTime()
{
   // Stop the stopwatch (if it is running) and return the realtime (in
   // seconds) passed between the start and stop events.
	   
   if (fState == kRunning) Stop();

   return fTotalRealTime;
}

//______________________________________________________________________________
double Stopwatch::CpuTime()
{
   // Stop the stopwatch (if it is running) and return the cputime (in
   // seconds) passed between the start and stop events.

   
   if (fState) Stop();

   return fTotalCpuTime;
}

//______________________________________________________________________________
double Stopwatch::GetRealTime()
{
   // Private static method returning system realtime.

#if defined(D__UNIX)
	struct timeval start;
	gettimeofday(&start, NULL);
	return start.tv_sec + start.tv_usec/1000.0;
#elif defined(WIN32)
   union {
      FILETIME ftFileTime;
      __int64  ftInt64;
   } ftRealTime; // time the process has spent in kernel mode
   SYSTEMTIME st;
   GetSystemTime(&st);
   SystemTimeToFileTime(&st,&ftRealTime.ftFileTime);
   return (double)ftRealTime.ftInt64 * gTicks;
#endif
}

//______________________________________________________________________________
double Stopwatch::GetCPUTime()
{
   // Private static method returning system CPU time.

#if defined(D__UNIX)
   struct tms cpt;
   times(&cpt);
   return (double)(cpt.tms_utime+cpt.tms_stime) / gTicks;
#elif defined(WIN32)

   OSVERSIONINFO OsVersionInfo;

   //         Value                      Platform
   //----------------------------------------------------
   //  VER_PLATFORM_WIN32s          Win32s on Windows 3.1
   //  VER_PLATFORM_WIN32_WINDOWS   Win32 on Windows 95
   //  VER_PLATFORM_WIN32_NT        Windows NT
   //
   OsVersionInfo.dwOSVersionInfoSize=sizeof(OSVERSIONINFO);
   GetVersionEx(&OsVersionInfo);
   if (OsVersionInfo.dwPlatformId == VER_PLATFORM_WIN32_NT) {
      DWORD       ret;
      FILETIME    ftCreate,       // when the process was created
                  ftExit;         // when the process exited

      union {
         FILETIME ftFileTime;
         __int64  ftInt64;
      } ftKernel; // time the process has spent in kernel mode

      union {
         FILETIME ftFileTime;
         __int64  ftInt64;
      } ftUser;   // time the process has spent in user mode

      HANDLE hThread = GetCurrentThread();
      ret = GetThreadTimes (hThread, &ftCreate, &ftExit,
                                     &ftKernel.ftFileTime,
                                     &ftUser.ftFileTime);
      if (ret != TRUE) {
         ret = GetLastError ();
		 //TODO report error here ::Error ("GetCPUTime", " Error on GetProcessTimes 0x%lx", (int)ret);
      }

      // Process times are returned in a 64-bit structure, as the number of
      // 100 nanosecond ticks since 1 January 1601.  User mode and kernel mode
      // times for this process are in separate 64-bit structures.
      // To convert to floating point seconds, we will:
      //
      // Convert sum of high 32-bit quantities to 64-bit int

      return (double) (ftKernel.ftInt64 + ftUser.ftInt64) * gTicks;
   } else
      return GetRealTime();
#endif
}

//______________________________________________________________________________
void Stopwatch::Print(const string& option/* ="" */) const
{
   // Print the real and cpu time passed between the start and stop events.
   // and the number of times (slices) this TStopwatch was called
   // (if this number > 1). If opt="m" print out realtime in milli second
   // precision. If opt="u" print out realtime in micro second precision.

   double  realt = const_cast<Stopwatch*>(this)->RealTime();
   double  cput  = const_cast<Stopwatch*>(this)->CpuTime();

   int  hours = int(realt / 3600);
   realt -= hours * 3600;
   int  min   = int(realt / 60);
   realt -= min * 60;
   int  sec   = int(realt);

   if (realt < 0) realt = 0;
   if (cput  < 0) cput  = 0;

   if (option == "m") {
      if (Counter() > 1) {
         printf("Real time %d:%02d:%06.3f, CP time %.3f, %d slices", hours, min, realt, cput, Counter());
      } else {
         printf("Real time %d:%02d:%06.3f, CP time %.3f", hours, min, realt, cput);
      }
   } else if (option == "u") {
      if (Counter() > 1) {
         printf("Real time %d:%02d:%09.6f, CP time %.3f, %d slices", hours, min, realt, cput, Counter());
      } else {
         printf("Real time %d:%02d:%09.6f, CP time %.3f", hours, min, realt, cput);
      }
   } else {
      if (Counter() > 1) {
         printf("Real time %d:%02d:%02d, CP time %.3f, %d slices", hours, min, sec, cput, Counter());
      } else {
         printf("Real time %d:%02d:%02d, CP time %.3f", hours, min, sec, cput);
      }
   }
}
}