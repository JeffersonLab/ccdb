cmake_minimum_required(VERSION 3.3)
project(CCDB_sqlite)

set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++11")

find_package (Threads)

include_directories("../../include/SQLite")

set(SOURCE_FILES "sqlite3.c")

add_library(${PROJECT_NAME} STATIC ${SOURCE_FILES})


target_link_libraries(${PROJECT_NAME} ${CMAKE_THREAD_LIBS_INIT} ${CMAKE_DL_LIBS})

# Required on Unix OS family to be able to be linked into shared libraries.
set_target_properties(${PROJECT_NAME}
        PROPERTIES POSITION_INDEPENDENT_CODE ON)

# Expose B's public includes (including Boost transitively) to other
# subprojects through cache variable.
set(${PROJECT_NAME}_INCLUDE_DIRS ${PROJECT_SOURCE_DIR}/include
        CACHE INTERNAL "${PROJECT_NAME}: Include Directories" FORCE)