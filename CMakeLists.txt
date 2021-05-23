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
cmake_minimum_required(VERSION 3.3)
project(CCDB_Project)

add_subdirectory(src)
