cmake_minimum_required(VERSION 3.3)
project(CCDB_tests)

set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++11")

find_package (Threads)

set(SOURCE_FILES
        "tests.cc"
        #"test_Console.cc"
        "test_StringUtils.cc"
        "test_PathUtils.cc"
        "test_NoMySqlUserAPI.cc"
        # "test_MySqlUserAPI.cc"
        "test_SQLiteProvider_Assignments.cc"
        "test_SQLiteProvider_Connection.cc"
        "test_SQLiteProvider_Directories.cc"
        "test_SQLiteProvider_TypeTables.cc"
        "test_SQLiteProvider_Variations.cc"
        "test_TimeProvider.cc"
        #"test_MySQLProvider_Assignments.cc"
        #"test_MySQLProvider_Connection.cc"
        #"test_MySQLProvider.cc"
        #"test_MySQLProvider_Directories.cc"
        #"test_MySQLProvider_Other.cc"
        #"test_MySQLProvider_RunRanges.cc"
        #"test_MySQLProvider_TypeTables.cc"
        #"test_MySQLProvider_Variations.cc"
        
        )


add_executable(${PROJECT_NAME} ${SOURCE_FILES})
target_link_libraries(${PROJECT_NAME} ${CMAKE_THREAD_LIBS_INIT} CCDB_lib)

get_filename_component(TESTS_PARENT_DIR ${PROJECT_SOURCE_DIR} DIRECTORY)
message(${TESTS_PARENT_DIR})
target_include_directories(${PROJECT_NAME} PRIVATE ${TESTS_PARENT_DIR})