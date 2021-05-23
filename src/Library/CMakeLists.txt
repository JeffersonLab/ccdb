cmake_minimum_required(VERSION 3.3)
project(ccdb VERSION 1.7)

set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++11")

include_directories("../../include")
include_directories("../../include/SQLite")
include_directories(${MYSQL_INCLUDE_DIR})

set(SOURCE_FILES

        #some global objects
        "Console.cc"
        "Log.cc"
        "CCDBError.cc"
        "GlobalMutex.cc"
        "IMutex.cc"
        "ISyncObject.cc"
        "PthreadMutex.cc"
        "PthreadSyncObject.cc"

        #user api
        "Calibration.cc"
        "CalibrationGenerator.cc"
        "SQLiteCalibration.cc"

        #helper classes
        "Helpers/StringUtils.cc"
        "Helpers/PathUtils.cc"
        "Helpers/WorkUtils.cc"
        "Helpers/TimeProvider.cc"

        #model and provider
        "Model/ObjectsOwner.cc"
        "Model/StoredObject.cc"
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

        #user api
        "MySQLCalibration.cc"

        #model and provider
        "Providers/MySQLConnectionInfo.cc"
        "Providers/MySQLDataProvider.cc"
        )

include(CMakePackageConfigHelpers)

add_library(ccdb_objs OBJECT ${SOURCE_FILES})
add_library(ccdb SHARED $<TARGET_OBJECTS:ccdb_objs>)
add_library(ccdb_static STATIC $<TARGET_OBJECTS:ccdb_objs>)
set_target_properties(ccdb_static PROPERTIES OUTPUT_NAME ccdb)   # So that the lib is not called libhipo4_static.a

target_link_libraries(ccdb ${MYSQL_LIBRARIES} ccdb_sqlite)
target_link_libraries(ccdb_static ${MYSQL_LIBRARIES} ccdb_sqlite_static)

target_include_directories(ccdb PUBLIC
                           $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/ccdb>
                           $<INSTALL_INTERFACE:include/ccdb>
                           $<INSTALL_INTERFACE:include/ccdb/CCDB>
                           )

target_include_directories(ccdb_static PUBLIC
                           $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/ccdb>
                           $<INSTALL_INTERFACE:include/ccdb>
                           $<INSTALL_INTERFACE:include/ccdb/CCDB>
                           )

# Required on Unix OS family to be able to be linked into shared libraries.
set_target_properties(ccdb_objs PROPERTIES POSITION_INDEPENDENT_CODE ON)

add_compile_definitions(BIG_JOINS=1)
add_compile_definitions(NDEBUG)
add_compile_options(-fno-strict-aliasing)

install(TARGETS ccdb
        EXPORT ccdb-exports
        LIBRARY DESTINATION lib
        ARCHIVE DESTINATION lib)

install(TARGETS ccdb_static
        EXPORT ccdb-exports
        LIBRARY DESTINATION lib
        ARCHIVE DESTINATION lib)

#
# List of include files for export.
# For now, all of them.
# The following installs into ../include/ccdb/CCDB and ..include/ccdb/SQLite
foreach(_include_sub "CCDB" "CCDB/Providers" "CCDB/Model" "CCDB/Helpers" "SQLite")
    file(GLOB CCDB_HEADERS_EXPORT_${_include_sub}
     LIST_DIRECTORIES FALSE
     RELATIVE ${CMAKE_CURRENT_LIST_DIR}
     "../../include/${_include_sub}/*.h"
     )
    install(FILES ${CCDB_HEADERS_EXPORT_${_include_sub}}
        DESTINATION ${CMAKE_INSTALL_PREFIX}/include/ccdb/${_include_sub})
endforeach(_include_sub IN CCDB SQLite)

write_basic_package_version_file(
        "${CMAKE_CURRENT_BINARY_DIR}/ccdbConfigVersion.cmake"
        VERSION ${PROJECT_VERSION} COMPATIBILITY AnyNewerVersion)

configure_package_config_file( ccdbConfig.cmake.in
                               ${CMAKE_CURRENT_BINARY_DIR}/ccdbConfig.cmake
                               INSTALL_DESTINATION ${CMAKE_INSTALL_PREFIX}/lib/cmake/ccdb
                               )

install(EXPORT ccdb-exports
        FILE ccdbTargets.cmake
        DESTINATION ${CMAKE_INSTALL_PREFIX}/lib/cmake/ccdb)

install(FILES ${CMAKE_CURRENT_BINARY_DIR}/ccdbConfig.cmake
        ${CMAKE_CURRENT_BINARY_DIR}/ccdbConfigVersion.cmake
        DESTINATION ${CMAKE_INSTALL_PREFIX}/lib/cmake/ccdb)

# SET(GCC_COVERAGE_COMPILE_FLAGS "-I/usr/include/mysql -DBIG_JOINS=1  -fno-strict-aliasing    -g -DNDEBUG")
# SET(GCC_COVERAGE_LINK_FLAGS    "-L/usr/lib/x86_64-linux-gnu -lmysqlclient -lpthread -lz -lm -ldl")
# SET( CMAKE_CXX_FLAGS  "${CMAKE_CXX_FLAGS} ${GCC_COVERAGE_COMPILE_FLAGS}" )
# SET( CMAKE_EXE_LINKER_FLAGS  "${CMAKE_EXE_LINKER_FLAGS} ${GCC_COVERAGE_LINK_FLAGS}" )