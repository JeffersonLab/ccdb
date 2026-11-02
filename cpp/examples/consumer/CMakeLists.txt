# A project outside the CCDB tree that uses the installed library through its CMake package.
#
#     cmake -S cpp -B build -DCMAKE_INSTALL_PREFIX=$HOME/ccdb   # CCDB itself
#     cmake --build build && cmake --install build
#     cmake -S cpp/examples/consumer -B consumer-build -DCMAKE_PREFIX_PATH=$HOME/ccdb
#     cmake --build consumer-build
#     consumer-build/ccdb_consumer sqlite:///path/to/ccdb.sqlite /test/test_vars/test_table
#
# cpp-tests.yml runs these steps in its consumer job.
cmake_minimum_required(VERSION 3.16)
project(ccdb_consumer CXX)

find_package(ccdb 2.5 CONFIG REQUIRED)
message(STATUS "Found ccdb ${ccdb_VERSION} in ${ccdb_DIR}, MySQL support: ${ccdb_WITH_MYSQL}")

add_executable(ccdb_consumer main.cc)
target_link_libraries(ccdb_consumer PRIVATE ccdb::ccdb)
