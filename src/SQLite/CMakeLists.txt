cmake_minimum_required(VERSION 3.5)
project(ccdb_sqlite)

set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++11")

find_package (Threads REQUIRED)

include_directories("../../include/SQLite")

set(SOURCE_FILES "sqlite3.c")

add_library(ccdb_sqlite_objs OBJECT ${SOURCE_FILES})
add_library(ccdb_sqlite SHARED  $<TARGET_OBJECTS:ccdb_sqlite_objs>)
add_library(ccdb_sqlite_static STATIC  $<TARGET_OBJECTS:ccdb_sqlite_objs>)
set_target_properties(ccdb_sqlite_static PROPERTIES OUTPUT_NAME ccdb_sqlite)

target_link_libraries(ccdb_sqlite ${CMAKE_THREAD_LIBS_INIT} ${CMAKE_DL_LIBS})
target_link_libraries(ccdb_sqlite_static ${CMAKE_THREAD_LIBS_INIT} ${CMAKE_DL_LIBS})

target_include_directories(ccdb_sqlite PUBLIC
                           $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/ccdb>
                           $<INSTALL_INTERFACE:include/ccdb>
                           $<INSTALL_INTERFACE:include/ccdb/SQLite>
                           )

target_include_directories(ccdb_sqlite_static PUBLIC
                           $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/ccdb>
                           $<INSTALL_INTERFACE:include/ccdb>
                           $<INSTALL_INTERFACE:include/ccdb/SQLite>
                           )


# Required on Unix OS family to be able to be linked into shared libraries.
set_target_properties(ccdb_sqlite_objs PROPERTIES POSITION_INDEPENDENT_CODE ON)

#set(ccdb_sqlite_INCLUDE_DIRS ${PROJECT_SOURCE_DIR}/include
#        CACHE INTERNAL "ccdb_sqlite: Include Directories" FORCE)

# Install the library, but add it to the exports of ccdb. That way there is only *one* ccdbConfig.cmake
install(TARGETS ccdb_sqlite
        EXPORT ccdb-exports
        LIBRARY DESTINATION lib
        ARCHIVE DESTINATION lib)

install(TARGETS ccdb_sqlite_static
        EXPORT ccdb-exports
        LIBRARY DESTINATION lib
        ARCHIVE DESTINATION lib)

#
