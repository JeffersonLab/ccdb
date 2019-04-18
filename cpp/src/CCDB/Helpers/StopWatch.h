/*
 * File:   StopWatch.h
 * Author: KjellKod
 * From: https://github.com/KjellKod/StopWatch
 *
 * Created on 2014-02-07
 */


#ifndef STOPWATCH_HEADER_H
#define STOPWATCH_HEADER_H

#include <chrono>

namespace ccdb {
    class StopWatch {
    public:
        typedef std::chrono::high_resolution_clock clock;
        typedef std::chrono::microseconds microseconds;
        typedef std::chrono::milliseconds milliseconds;
        typedef std::chrono::seconds seconds;

        StopWatch(): mStart(clock::now()) {
            //static_assert(std::chrono::steady_clock::is_steady,
            //              "Serious OS/C++ library issues. Steady clock is not steady");
            // FYI:  This would fail static_assert(std::chrono::high_resolution_clock::is_steady(), "High Resolution Clock is NOT steady on CentOS?!");
        };

        uint64_t ElapsedUs() const{
            return (uint64_t)std::chrono::duration_cast<microseconds>(clock::now() - mStart).count();
        }

        uint64_t ElapsedMs() const{
            return (uint64_t)std::chrono::duration_cast<milliseconds>(clock::now() - mStart).count();
        }

        uint64_t ElapsedSec() const{
            return (uint64_t)std::chrono::duration_cast<seconds>(clock::now() - mStart).count();
        }

        std::chrono::high_resolution_clock::time_point Restart() {
            mStart = clock::now();
            return mStart;
        }

    private:
        clock::time_point mStart;
    };
}

#endif //#define STOPWATCH_HEADER_H