cmake_minimum_required(VERSION 3.16)

# The version of the C++ library is the release version of CCDB (python/ccdb/version.py without its
# .devN suffix); unit_test_metadata_files checks that the two agree.
project(ccdb_main VERSION 2.5.0)

message("=== CCDB CMAKE ===")

if(NOT DEFINED CMAKE_MODULE_PATH)
    set(CMAKE_MODULE_PATH ${CMAKE_MODULE_PATH} "${PROJECT_SOURCE_DIR}/cmake/Modules/")
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

# The JANA2 service (library ccdb_jana2 and plugin CCDB_service) lives in ../jana2 and needs JANA2
option(CCDB_BUILD_JANA2 "Build the JANA2 service CCDB_service (needs JANA2)" OFF)
if(CCDB_BUILD_JANA2)
    add_subdirectory("${PROJECT_SOURCE_DIR}/../jana2" "${PROJECT_BINARY_DIR}/jana2")
endif()

# The Catch2 suite; a package build may switch it off. When on, ccdb_tests is installed to <prefix>/bin as in 2.4.
option(CCDB_BUILD_TESTS "Build the Catch2 test suite ccdb_tests" ON)
if(CCDB_BUILD_TESTS)
    add_subdirectory(src/tests)
endif()

# CMake package: find_package(ccdb CONFIG) gives the imported target ccdb::ccdb
include(CMakePackageConfigHelpers)
set(CCDB_CMAKE_DIR lib/cmake/ccdb)
install(EXPORT ccdbTargets
        NAMESPACE ccdb::
        DESTINATION ${CCDB_CMAKE_DIR})
configure_package_config_file(
        "${PROJECT_SOURCE_DIR}/cmake/ccdbConfig.cmake.in"
        "${PROJECT_BINARY_DIR}/ccdbConfig.cmake"
        INSTALL_DESTINATION ${CCDB_CMAKE_DIR})
write_basic_package_version_file(
        "${PROJECT_BINARY_DIR}/ccdbConfigVersion.cmake"
        VERSION ${ccdb_main_VERSION}
        COMPATIBILITY SameMajorVersion)
install(FILES
        "${PROJECT_BINARY_DIR}/ccdbConfig.cmake"
        "${PROJECT_BINARY_DIR}/ccdbConfigVersion.cmake"
        DESTINATION ${CCDB_CMAKE_DIR})
#add_subdirectory(src/Benchmarks)
message("=== END OF CCDB CMAKE ===")
