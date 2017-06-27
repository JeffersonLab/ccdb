//
// Created by romanov on 6/27/17.
//

#ifndef CCDB_PERFLOG_H
#define CCDB_PERFLOG_H

#include <iostream>
#include <string>

#include "StopWatch.h"

namespace ccdb{
    class PerfLog{
    public:
        PerfLog(const std::string& name):
                _name(name)
        {
        }



        ~PerfLog(){
            std::cout<<"CCDB_PERF_LOG: "<<_name<<" us: "<<_sw.ElapsedUs()<<std::endl;
        }
    private:
        ccdb::StopWatch _sw;
        std::string _name;

    };
}
#endif //CCDB_PERFLOG_H
