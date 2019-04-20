cmake_minimum_required(VERSION 3.3)
project(CCDB_lib)

set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++11")


include_directories(${MYSQL_INCLUDE_DIR})

set(SOURCE_FILES

        #some global objects
        "Console.cc"
        "Log.cc"
        "CCDBError.cc"

        #user api
        "Calibration.cc"
        "CalibrationGenerator.cc"
        "SQLiteCalibration.cc"
        "MySQLCalibration.cc"

        #helper classes
        "Helpers/StringUtils.cc"
        "Helpers/PathUtils.cc"
        "Helpers/WorkUtils.cc"
        "Helpers/TimeProvider.cc"

        "Model/Assignment.cc"
        "Model/ConstantsTypeColumn.cc"
        "Model/ConstantsTypeTable.cc"
        "Model/Directory.cc"
        "Model/EventRange.cc"
        "Model/RunRange.cc"
        "Model/Variation.cc"

        "Providers/DataProvider.cc"
        "Providers/FileDataProvider.cc"
        "Providers/SQLiteDataProvider.cc"
        "Providers/IAuthentication.cc"
        "Providers/EnvironmentAuthentication.cc"


        #model and provider
        "Providers/MySQLConnectionInfo.cc"
        "Providers/MySQLDataProvider.cc"
        )


add_library(${PROJECT_NAME} STATIC ${SOURCE_FILES})

get_filename_component(CCDB_LIB_PARENT_DIR ${PROJECT_SOURCE_DIR} DIRECTORY)
message(${CCDB_LIB_PARENT_DIR})
target_include_directories(${PROJECT_NAME} PRIVATE ${CCDB_LIB_PARENT_DIR})



# Required on Unix OS family to be able to be linked into shared libraries.
set_target_properties(${PROJECT_NAME}
        PROPERTIES POSITION_INDEPENDENT_CODE ON)


SET(GCC_COVERAGE_COMPILE_FLAGS "-I/usr/include/mysql -DBIG_JOINS=1  -fno-strict-aliasing    -g -DNDEBUG")
SET(GCC_COVERAGE_LINK_FLAGS    "-L/usr/lib/x86_64-linux-gnu -lmysqlclient -lpthread -lz -lm -ldl")
SET( CMAKE_CXX_FLAGS  "${CMAKE_CXX_FLAGS} ${GCC_COVERAGE_COMPILE_FLAGS}" )
SET( CMAKE_EXE_LINKER_FLAGS  "${CMAKE_EXE_LINKER_FLAGS} ${GCC_COVERAGE_LINK_FLAGS}" )