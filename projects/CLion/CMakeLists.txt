cmake_minimum_required(VERSION 3.3)
project(CCDB)

include_directories(
        ../../include
        ../../include/SQLite
        Source
        Tests
        ../Utilities/Source
)

find_package (Threads)
SET(GCC_COVERAGE_LINK_FLAGS    "-pthread")

set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++11")

set(SOURCE_FILES

#some global objects
        ../../src/Library/Console.cc
        ../../src/Library/Log.cc
        ../../src/Library/CCDBError.cc
        ../../src/Library/GlobalMutex.cc
        ../../src/Library/IMutex.cc
        ../../src/Library/ISyncObject.cc
        ../../src/Library/PthreadMutex.cc
        ../../src/Library/PthreadSyncObject.cc

#user api
        ../../src/Library/Calibration.cc
        ../../src/Library/CalibrationGenerator.cc
        ../../src/Library/SQLiteCalibration.cc

#helper classes
        ../../src/Library/Helpers/StringUtils.cc
        ../../src/Library/Helpers/PathUtils.cc
        ../../src/Library/Helpers/WorkUtils.cc
        ../../src/Library/Helpers/TimeProvider.cc

#model and provider
        ../../src/Library/Model/ObjectsOwner.cc
        ../../src/Library/Model/StoredObject.cc
        ../../src/Library/Model/Assignment.cc
        ../../src/Library/Model/ConstantsTypeColumn.cc
        ../../src/Library/Model/ConstantsTypeTable.cc
        ../../src/Library/Model/Directory.cc
        ../../src/Library/Model/EventRange.cc
        ../../src/Library/Model/RunRange.cc
        ../../src/Library/Model/Variation.cc
        ../../src/Library/Providers/DataProvider.cc
        ../../src/Library/Providers/FileDataProvider.cc
        ../../src/Library/Providers/SQLiteDataProvider.cc
        ../../src/Library/Providers/IAuthentication.cc
        ../../src/Library/Providers/EnvironmentAuthentication.cc

# Tests
        ../../src/Tests/tests.cc

        ../../src/Tests/test_TimeProvider.cc
        ../../src/Tests/test_PathUtils.cc

# SQLite
        ../../src/SQLite/sqlite3.c

        )
add_executable(CCDB ${SOURCE_FILES})
target_link_libraries (CCDB)