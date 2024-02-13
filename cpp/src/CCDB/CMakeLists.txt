cmake_minimum_required(VERSION 3.16)

# CCDB library
project(ccdb_lib)
message(STATUS "=== Configuring CCDB library ===")

add_library(ccdb SHARED

        #user api
        Calibration.cc
        CalibrationGenerator.cc

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
        )

target_include_directories(ccdb PUBLIC "${PROJECT_SOURCE_DIR}/..")
set_target_properties(ccdb PROPERTIES POSITION_INDEPENDENT_CODE ON)

# Add SQLITE3
find_package (SQLite3 REQUIRED)
if (SQLite3_FOUND)
    message(STATUS "SQLite3_FOUND")
    message(STATUS "SQLite3_INCLUDE_DIR = ${SQLite3_INCLUDE_DIRS}")
    message(STATUS "SQLite3_LIBRARY     = ${SQLite3_LIBRARY}")
    message(STATUS "SQLite3_VERSION     = ${SQLite3_VERSION}")

    target_include_directories(ccdb SYSTEM PRIVATE ${SQLite3_INCLUDE_DIR})
    target_link_libraries(ccdb PUBLIC ${SQLite3_LIBRARY})
    target_sources(ccdb PRIVATE
            SQLiteCalibration.cc
            Providers/SQLiteDataProvider.cc
    )
endif (SQLite3_FOUND)

# Add MySQL/MariaDB
find_package(MySQL)
if (MySQL_FOUND)
    message(STATUS "MySQL_FOUND")
    message(STATUS "MySQL_INCLUDE_DIRS = ${MySQL_INCLUDE_DIRS}")
    message(STATUS "MySQL_LIBRARIES    = ${MySQL_LIBRARIES}")
    message(STATUS "MySQL_VERSION      = ${MySQL_VERSION}")

    target_include_directories(ccdb SYSTEM PRIVATE ${MySQL_INCLUDE_DIRS})
    target_link_libraries(ccdb PUBLIC ${MySQL_LIBRARIES})
    target_sources(ccdb PRIVATE
            MySQLCalibration.cc
            MySQLCalibration.h
            Providers/MySQLDataProvider.cc
    )
    target_compile_definitions(ccdb PUBLIC "CCDB_MYSQL=1")
elseif (MySQL_FOUND)
    message(STATUS "(!) MySQL IS NOT FOUND. Building without MySQL")
endif (MySQL_FOUND)


find_package(Threads)

message(STATUS "CMAKE_THREAD_LIBS_INIT = ${CMAKE_THREAD_LIBS_INIT}")
# If you need to set properties specific to the shared or static library, do it here
#target_compile_definitions(ccdb_shared PRIVATE SHARED_LIBRARY_DEFINITION)
#target_compile_definitions(ccdb_static PRIVATE STATIC_LIBRARY_DEFINITION)
#target_compile_definitions(ccdb_obj PUBLIC SOME_DEFINITION)
#target_include_directories(ccdb_obj PUBLIC ${INCLUDE_DIRS})

#    # Get all variables
#    GET_CMAKE_PROPERTY(vars VARIABLES)
#
#    # Filter by prefix and build the "res" list
#    FOREACH(var ${vars})
#        STRING(REGEX MATCH "^(SQLITE3|SQLite3)" item ${var})
#        IF(item)
#            message("FOUND: ${var}=${${var}}")
#        ENDIF(item)
#    ENDFOREACH(var)

#
#
#add_library(ccdb_static STATIC ${SOURCE_FILES})
#
#
#
#
#
#get_filename_component(CCDB_LIB_PARENT_DIR ${PROJECT_SOURCE_DIR} DIRECTORY)
#message(STATUS "CCDB_LIB_PARENT_DIR = ${CCDB_LIB_PARENT_DIR}")
#
#message("SQLite3_INCLUDE_DIRS = ${SQLite3_INCLUDE_DIRS}")
#target_include_directories(ccdb PRIVATE ${CCDB_LIB_PARENT_DIR}
#    ${SQLite3_INCLUDE_DIRS})
#target_link_libraries(ccdb LINK_PUBLIC fmt sqlite3)
#
#
## Required on Unix OS family to be able to be linked into shared libraries.
#set_target_properties(ccdb PROPERTIES POSITION_INDEPENDENT_CODE ON)
#
#find_package(MySQL)
#
#if (MySQL_FOUND)
#    message(STATUS "MySQL FOUND")
#else()
#    message(STATUS "MySQL NOT FOUND")
#endif()
#
#
##SET(GCC_COVERAGE_COMPILE_FLAGS "-I/usr/include/mysql -DBIG_JOINS=1  -fno-strict-aliasing    -g -DNDEBUG")
##SET(GCC_COVERAGE_LINK_FLAGS    "-L/usr/lib/x86_64-linux-gnu -lmysqlclient -lpthread -lz -lm -ldl")
##SET( CMAKE_CXX_FLAGS  "${CMAKE_CXX_FLAGS} ${GCC_COVERAGE_COMPILE_FLAGS}" )
##SET( CMAKE_EXE_LINKER_FLAGS  "${CMAKE_EXE_LINKER_FLAGS} ${GCC_COVERAGE_LINK_FLAGS}" )
#
install(DIRECTORY "${PROJECT_SOURCE_DIR}/" # source directory
        DESTINATION "include/CCDB" # target directory
        FILES_MATCHING # install only matched files
        PATTERN "*.h" # select header files
)
install(TARGETS ccdb DESTINATION lib)
#
#message(STATUS "===END OF CCDB CMAKE====")