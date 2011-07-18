  
  // stopwatch - Implements CStopWatch, used to debug timing.
  
   
  
#pragma once

#include <time.h>

   
  
class DStopWatch
{
  
private:
	clock_t start;
	clock_t finish;
public:
	double GetDuration() { return (double)(finish - start) / CLOCKS_PER_SEC; }
	void Start() { start = clock(); }
	void Stop() { finish = clock(); }
}; // class CStopWatch