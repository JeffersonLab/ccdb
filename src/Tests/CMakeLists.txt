cmake_minimum_required(VERSION 3.3)
project(CCDB_tests)

set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS}")

include_directories("../../include")
include_directories("../../include/SQLite")

find_package (Threads)

set(SOURCE_FILES
        "tests.cc"
        #"test_Console.cc"
        "test_StringUtils.cc"
        "test_PathUtils.cc"
        "test_ModelObjects.cc"
        "test_NoMySqlUserAPI.cc"
        "test_Authentication.cc"
        "test_SQLiteProvider_Assignments.cc"
        "test_SQLiteProvider_Connection.cc"
        "test_SQLiteProvider_Directories.cc"
        "test_SQLiteProvider_TypeTables.cc"
        "test_SQLiteProvider_Variations.cc"
        "test_TimeProvider.cc"
        "test_MySQLProvider_Assignments.cc"
        "test_MySQLProvider_Connection.cc"
        "test_MySQLProvider.cc"
        "test_MySQLProvider_Directories.cc"
        "test_MySQLProvider_Other.cc"
        "test_MySQLProvider_RunRanges.cc"
        "test_MySQLProvider_TypeTables.cc"
        "test_MySQLProvider_Variations.cc"
        
        )


add_executable(${PROJECT_NAME} ${SOURCE_FILES})
target_link_libraries(${PROJECT_NAME} ${CMAKE_THREAD_LIBS_INIT} CCDB_lib)

