cmake_minimum_required(VERSION 3.3)
project(CCDB)

set(CMAKE_DISABLE_IN_SOURCE_BUILD ON)
set(CMAKE_DISABLE_SOURCE_CHANGES  ON)

if ("${CMAKE_SOURCE_DIR}" STREQUAL "${CMAKE_BINARY_DIR}")
    message(SEND_ERROR "In-source builds are not allowed.")
endif ()

set(CMAKE_VERBOSE_MAKEFILE ON)
set(CMAKE_COLOR_MAKEFILE   ON)

# Remove 'lib' prefix for shared libraries on Windows
if (WIN32)
    set(CMAKE_SHARED_LIBRARY_PREFIX "")
endif ()



INCLUDE(${CMAKE_SOURCE_DIR}/FindMySQL.cmake)

add_definitions(-DCCDB_MYSQL)

add_subdirectory(SQLite)
add_subdirectory(Library)
add_subdirectory(Tests)
