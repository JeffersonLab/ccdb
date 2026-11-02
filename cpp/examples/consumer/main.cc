// Reads one table through the installed CCDB library: ccdb_consumer CONNECTION REQUEST [RUN]
// Prints the shape and the values of the table, one row per line.

#include <CCDB/Calibration.h>
#include <CCDB/CalibrationGenerator.h>

#include <cstdlib>
#include <iostream>
#include <memory>
#include <string>
#include <vector>

int main(int argc, char** argv)
{
    if (argc < 3) {
        std::cerr << "usage: ccdb_consumer CONNECTION REQUEST [RUN]" << std::endl;
        return 2;
    }
    const std::string connection = argv[1];
    const std::string request = argv[2];
    const int run = argc > 3 ? std::atoi(argv[3]) : 0;

    try {
        std::unique_ptr<ccdb::Calibration> calibration(ccdb::CalibrationGenerator::CreateCalibration(connection, run));
        std::vector<std::vector<std::string>> rows;
        if (!calibration->GetCalib(rows, request)) {
            std::cerr << "no data for " << request << std::endl;
            return 1;
        }
        std::cout << request << ": " << rows.size() << " rows, " << (rows.empty() ? 0 : rows[0].size()) << " columns" << std::endl;
        for (const auto& row : rows) {
            for (size_t i = 0; i < row.size(); ++i) {
                std::cout << (i ? " " : "") << row[i];
            }
            std::cout << std::endl;
        }
    }
    catch (const std::exception& error) {
        std::cerr << "error: " << error.what() << std::endl;
        return 1;
    }
    return 0;
}
