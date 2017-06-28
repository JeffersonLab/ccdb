//
// Created by romanov on 6/27/17.
//

#ifndef CCDB_PERFLOG_H
#define CCDB_PERFLOG_H

#include <iostream>
#include <string>
#include <thread>

#include "StopWatch.h"

#if CCDB_PERFLOG_ON
#define CCDB_PERFLOG(x) (PerfLog(x))
#else
#define CCDB_PERF_LOG(x) 0
#endif

namespace ccdb{
    class PerfLog{
    public:
        explicit PerfLog (const std::string& name):
                _sw(),
                _name(name)
        {
            _startTime = _sw.Restart();
        }

        PerfLog(PerfLog&) = default;
        PerfLog(PerfLog&&) noexcept;

        uint64_t GetTimeSinceEpochUs()
        {
            return static_cast<uint64_t>
            (std::chrono::duration_cast<std::chrono::microseconds>
                            (_startTime.time_since_epoch()).count());
        }


        virtual ~PerfLog(){
            std::cout<<"CCDB_PERF_LOG:{\"thread_id\":"<<std::this_thread::get_id()<<","
                     <<"\"descr\":\""<<_name<<"\","
                     <<"\"start_stamp\":"<<GetTimeSinceEpochUs()<<","
                     <<"\"elapsed\":"<<_sw.ElapsedUs()<<","
                     <<"\"t_units\":\"us\"}"<<std::endl;

        }
    private:
        ccdb::StopWatch _sw{};
        std::string _name;
        std::chrono::high_resolution_clock::time_point _startTime;

    };

    inline PerfLog::PerfLog(PerfLog&&) noexcept = default;
}
#endif //CCDB_PERFLOG_H
