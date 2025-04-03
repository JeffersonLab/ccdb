#
# Top level CMakeLists.txt file for CCDB.
#
#  - Maurik Holtrop  (University of New Hampshire)
#
# To build the CCDB library:
# mkdir build
# cd build
# cmake -DCMAKE_INSTALL_PREFIX=<install_location>  ..
# make install
#
cmake_minimum_required(VERSION 3.5)
project(CCDB_Project)

add_subdirectory(src)

install(PROGRAMS bin/ccdb DESTINATION ${CMAKE_INSTALL_PREFIX}/bin)
install(DIRECTORY python DESTINATION ${CMAKE_INSTALL_PREFIX})
install(DIRECTORY scripts DESTINATION ${CMAKE_INSTALL_PREFIX})

