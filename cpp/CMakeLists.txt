cmake_minimum_required(VERSION 3.3)

project(ccdb)

message("=== CCDB CMAKE ===")

if(NOT DEFINED CMAKE_MODULE_PATH)
    set(CMAKE_MODULE_PATH ${CMAKE_MODULE_PATH} "${PROJECT_SOURCE_DIR}/cmake/Modules/")
endif()


if(NOT DEFINED CMAKE_INSTALL_PREFIX)
    set(CMAKE_INSTALL_PREFIX ${CMAKE_SOURCE_DIR}/install)
endif()

message(STATUS "CMAKE_INSTALL_PREFIX=${CMAKE_INSTALL_PREFIX}")
message(STATUS "CMAKE_MODULE_PATH=${CMAKE_MODULE_PATH}")
message(STATUS "CMAKE_VERBOSE_MAKEFILE=${CMAKE_VERBOSE_MAKEFILE}")

# Make C++11 a default
if(NOT "${CMAKE_CXX_STANDARD}")
    set(CMAKE_CXX_STANDARD 11)
endif()

# Remove 'lib' prefix for shared libraries on Windows
if (WIN32)
    set(CMAKE_SHARED_LIBRARY_PREFIX "")
endif ()


#add_subdirectory(src/fmt)
add_subdirectory(src/CCDB)
add_subdirectory(src/tests)
#add_subdirectory(src/Benchmarks)
message("=== END OF CCDB CMAKE ===")
