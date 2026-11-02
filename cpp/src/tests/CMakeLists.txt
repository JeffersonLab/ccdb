cmake_minimum_required(VERSION 3.16)
project(ccdb_tests)

find_package (Threads)

add_executable(${PROJECT_NAME}
        "tests.cc"
        #"test_Console.cc"
        "test_StringUtils.cc"
        "test_PathUtils.cc"
        )

# Add SQLITE3
find_package (SQLite3 REQUIRED)
if (SQLite3_FOUND)
        target_include_directories(${PROJECT_NAME} SYSTEM PRIVATE ${SQLite3_INCLUDE_DIR})
        target_link_libraries(${PROJECT_NAME} ${SQLite3_LIBRARY})
        target_sources(${PROJECT_NAME} PRIVATE
                "test_Calibration_Tags.cc"
                "test_ConnectionLifecycle.cc"
                "test_NoMySqlUserAPI.cc"
                "test_SQLiteProvider_Assignments.cc"
                "test_SQLiteProvider_Connection.cc"
                "test_SQLiteProvider_Directories.cc"
                "test_SQLiteProvider_SharedSets.cc"
                "test_SQLiteProvider_Tags.cc"
                "test_SQLiteProvider_TypeTables.cc"
                "test_SQLiteProvider_Variations.cc"
                "test_TimeProvider.cc"
        )
endif (SQLite3_FOUND)

# Add MySQL/MariaDB
find_package (MySQL)
if (MySQL_FOUND)
        target_include_directories(${PROJECT_NAME} SYSTEM PRIVATE ${MySQL_INCLUDE_DIRS})
        target_link_libraries(${PROJECT_NAME} ${MySQL_LIBRARIES})
        target_sources(${PROJECT_NAME} PRIVATE
                "test_MySqlUserAPI.cc"
                "test_MySQLProvider_Assignments.cc"
                "test_MySQLProvider_Connection.cc"
                "test_MySQLProvider_NoServer.cc"
                "test_MySQLProvider.cc"
                "test_MySQLProvider_Directories.cc"
                "test_MySQLProvider_Other.cc"
                "test_MySQLProvider_RunRanges.cc"
                "test_MySQLProvider_Tags.cc"
                "test_MySQLProvider_TypeTables.cc"
                "test_MySQLProvider_Variations.cc"
        )
        target_compile_definitions(${PROJECT_NAME} PUBLIC "CCDB_MYSQL=1")
endif (MySQL_FOUND)

# The [jana2] tests of the JANA2 service; they read the database of scripts/eic/make_jana2_test_db.py
if(CCDB_BUILD_JANA2)
        target_sources(${PROJECT_NAME} PRIVATE "test_JANA2_Service.cc" "test_JANA2_Factory.cc")
        target_link_libraries(${PROJECT_NAME} ccdb_jana2)
        # the example factory is header only; C++20 as JANA2's factory generator needs it
        target_include_directories(${PROJECT_NAME} PRIVATE "${CMAKE_SOURCE_DIR}/../jana2/examples")
        target_compile_features(${PROJECT_NAME} PRIVATE cxx_std_20)
        target_compile_definitions(${PROJECT_NAME} PRIVATE "CCDB_JANA2_PLUGIN_DIR=\"$<TARGET_FILE_DIR:CCDB_service>\"")
        add_dependencies(${PROJECT_NAME} CCDB_service ccdb_jana2_example)
endif()

target_link_libraries(${PROJECT_NAME} ${CMAKE_THREAD_LIBS_INIT} ccdb)

get_filename_component(TESTS_PARENT_DIR ${PROJECT_SOURCE_DIR} DIRECTORY)
target_include_directories(${PROJECT_NAME} PRIVATE ${TESTS_PARENT_DIR})

install(TARGETS ccdb_tests DESTINATION bin)
