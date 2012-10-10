// @(#)root/base:$Id: TStopwatch.h 20877 2007-11-19 11:17:07Z rdm $
// Author: Fons Rademakers   11/10/95

/*************************************************************************
 * Copyright (C) 1995-2000, Rene Brun and Fons Rademakers.               *
 * All rights reserved.                                                  *
 *                                                                       *
 * For the licensing terms see $ROOTSYS/LICENSE.                         *
 * For the list of contributors see $ROOTSYS/README/CREDITS.             *
 *************************************************************************/

#ifndef Stopwatch_HEADER
#define Stopwatch_HEADER
#include <string>
using namespace std;

//////////////////////////////////////////////////////////////////////////
//                                                                      //
// TStopwatch                                                           //
//                                                                      //
// Stopwatch class. This class returns the real and cpu time between    //
// the start and stop events.                                           //
//                                                                      //
//////////////////////////////////////////////////////////////////////////


namespace ccdb
{
	class Stopwatch 
	{

	private:
	   enum EState { kUndefined, kStopped, kRunning };

	   double     fStartRealTime;   //wall clock start time
	   double     fStopRealTime;    //wall clock stop time
	   double     fStartCpuTime;    //cpu start time
	   double     fStopCpuTime;     //cpu stop time
	   double     fTotalCpuTime;    //total cpu time
	   double     fTotalRealTime;   //total real time
	   int        fState;           //stopwatch state
	   int        fCounter;         //number of times the stopwatch was started

	   static double GetRealTime();
	   static double GetCPUTime();

	public:
	   Stopwatch();
	   void        Start(bool reset = true);
	   void        Stop();
	   void        Continue();
	   int         Counter() const { return fCounter; }
	   double      RealTime();
	   void        Reset() { ResetCpuTime(); ResetRealTime(); }
	   void        ResetCpuTime(double time = 0) { Stop();  fTotalCpuTime = time; }
	   void        ResetRealTime(double time = 0) { Stop(); fTotalRealTime = time; }
	   double      CpuTime();
	   void        Print(const string& option="") const;
	};
}
#endif //Stopwatch_HEADER
