cmake_minimum_required(VERSION 3.16)
project(CCDB_bn_sqlite)

set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++11")

include_directories("../../include")
include_directories("../../include/SQLite")

find_package (Threads)

set(SOURCE_FILES
        benchmark_SqliteMultiprocess.cc
        )


add_executable(${PROJECT_NAME} ${SOURCE_FILES})
target_link_libraries(${PROJECT_NAME} ${CMAKE_THREAD_LIBS_INIT} CCDB_lib)