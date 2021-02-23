cmake_minimum_required(VERSION 3.3)

project(ccdb)

set(CMAKE_MODULE_PATH ${CMAKE_MODULE_PATH} "${CMAKE_SOURCE_DIR}/cmake/Modules/")

set(CMAKE_VERBOSE_MAKEFILE ON)
set(CMAKE_COLOR_MAKEFILE   ON)
set(CMAKE_INSTALL_PREFIX ${CMAKE_SOURCE_DIR}/..)

# Remove 'lib' prefix for shared libraries on Windows
if (WIN32)
    set(CMAKE_SHARED_LIBRARY_PREFIX "")
endif ()

FIND_PACKAGE(MySQL)

#add_definitions(-DCCDB_MYSQL)
#add_definitions(-DCCDB_PERFLOG_ON=1)
add_subdirectory(src/fmt)
add_subdirectory(src/CCDB)
add_subdirectory(src/Tests)
#add_subdirectory(src/Benchmarks)
