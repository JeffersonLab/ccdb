cmake_minimum_required(VERSION 3.3)

# CCDB library
project(ccdb_lib)

message(STATUS "===START OF CCDB CMAKE====")

# Set C++11 if NOT set by user
if (NOT DEFINED(CMAKE_CXX_STANDARD))
    set(CMAKE_CXX_STANDARD 11)
endif()
message(STATUS "CMAKE_CXX_STANDARD: ${CMAKE_CXX_STANDARD}")


# Find SQLite3
find_package (SQLite3 REQUIRED)
if (SQLITE3_FOUND)
    include_directories(${SQLITE3_INCLUDE_DIRS})
endif (SQLITE3_FOUND)

# Source files
set(SOURCE_FILES

        #user api
        Calibration.cc
        CalibrationGenerator.cc
        SQLiteCalibration.cc
        # MySQLCalibration.cc

        #helper classes
        Helpers/StringUtils.cc
        Helpers/PathUtils.cc
        Helpers/TimeProvider.cc
        Helpers/SQLite.h

        Model/Assignment.cc
        Model/ConstantsTypeColumn.cc
        Model/ConstantsTypeTable.cc
        Model/Directory.cc
        Model/RunRange.cc

        Providers/DataProvider.cc
        Providers/SQLiteDataProvider.cc

        #model and provider
        # Providers/MySQLDataProvider.cc
        )


add_library(ccdb STATIC ${SOURCE_FILES})

get_filename_component(CCDB_LIB_PARENT_DIR ${PROJECT_SOURCE_DIR} DIRECTORY)
message(STATUS "CCDB_LIB_PARENT_DIR = ${CCDB_LIB_PARENT_DIR}")

target_include_directories(ccdb PRIVATE ${CCDB_LIB_PARENT_DIR})
target_link_libraries(ccdb LINK_PUBLIC fmt sqlite3)


# Required on Unix OS family to be able to be linked into shared libraries.
set_target_properties(ccdb PROPERTIES POSITION_INDEPENDENT_CODE ON)

find_package(MySQL)



if (MYSQL_FOUND)
    message(STATUS "MySQL FOUND !!!!!!!!!!!!!!!!!!!!!!!!!!")
else()
    message(STATUS "MySQL NOT FOUND !!!!!!!!!!!!!!!!!!!!!!!!!!")
endif()


#SET(GCC_COVERAGE_COMPILE_FLAGS "-I/usr/include/mysql -DBIG_JOINS=1  -fno-strict-aliasing    -g -DNDEBUG")
#SET(GCC_COVERAGE_LINK_FLAGS    "-L/usr/lib/x86_64-linux-gnu -lmysqlclient -lpthread -lz -lm -ldl")
#SET( CMAKE_CXX_FLAGS  "${CMAKE_CXX_FLAGS} ${GCC_COVERAGE_COMPILE_FLAGS}" )
#SET( CMAKE_EXE_LINKER_FLAGS  "${CMAKE_EXE_LINKER_FLAGS} ${GCC_COVERAGE_LINK_FLAGS}" )

install(DIRECTORY "${PROJECT_SOURCE_DIR}/" # source directory
        DESTINATION "include/CCDB" # target directory
        FILES_MATCHING # install only matched files
        PATTERN "*.h" # select header files
)

install(TARGETS ccdb DESTINATION lib)

message(STATUS "===END OF CCDB CMAKE====")