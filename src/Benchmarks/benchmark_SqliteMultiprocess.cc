#include <iostream>
#include <iomanip>
#include <thread>
#include <chrono>
#include <vector>
#include <string>
#include <random>

#include <CCDB/Helpers/PathUtils.h>
#include <CCDB/CalibrationGenerator.h>
#include <CCDB/Helpers/PerfLog.h>
#include "CCDB/Helpers/StopWatch.h"

std::string con_str = "sqlite:///D:\\ccdb.sqlite";
//std::string con_str = "mysql://ccdb_user@hallddb.jlab.org/ccdb";
uint64_t run_min = 30200;
uint64_t run_max = 30900;
std::string tableName[] = {"TOF/timing_offsets", "CDC/timing_offsets"};


int main()
{
    using namespace std;
    using namespace std::chrono;

    std::random_device rd;
    std::uniform_int_distribution<int> runRandomDistr(run_min, run_max);
    int run = runRandomDistr(rd);
    std::cout << "Randomly-chosen run: " << run << '\n';


    auto now = system_clock::now();
    auto now_c = system_clock::to_time_t(now);

    bool isParsedOk = false;
    auto parsedTime_c = ccdb::PathUtils::ParseTime("2017-06-26 19:41:10", &isParsedOk);
    auto parsedTime = system_clock::from_time_t(parsedTime_c);
    cout << "Now is: " << std::put_time(std::localtime(&now_c), "%F %T") << '\n';
    cout << "Req is: " << std::put_time(std::localtime(&parsedTime_c), "%F %T") << '\n';
    cout << "Now > Req: " << (now > parsedTime) << '\n';

    while(now<parsedTime) {
        std::this_thread::sleep_for(milliseconds(10));
        now = system_clock::now();
    }
    now_c = system_clock::to_time_t(now);
    cout << "Now is: " << std::put_time(std::localtime(&now_c), "%F %T") << '\n';
    cout << "Done"<<std::endl;


    // Get run

    auto con = ccdb::CalibrationGenerator::CreateCalibration(con_str, 30100, "default");

    std::uniform_int_distribution<int> tableRandom(0, 1);
    vector<vector<double>> result;

    double sum = 0; // Trick the optimization;



    for(int i=0; i<1000; i++) {
        ccdb::PerfLog plog("GetCalib");
        result.clear();

        con->GetCalib(result, tableName[tableRandom(rd)]);
        sum+=result[0][0];

    }







    // >oO DEBUG list of name-paths vector<string> namePaths;con->GetListOfNamepaths(namePaths);for(auto s:namePaths) { cout<<s<<endl; }


/*
    std::cout << "24 hours ago, the time was "
              << std::put_time(std::localtime(&now_c), "%F %T") << '\n';

    std::chrono::steady_clock::time_point start = std::chrono::steady_clock::now();
    std::cout << "Hello World\n";
    std::chrono::steady_clock::time_point end = std::chrono::steady_clock::now();
    std::cout << "Printing took "
              << std::chrono::duration_cast<std::chrono::microseconds>(end - start).count()
              << "us.\n";

*/
}