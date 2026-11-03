# CCDB in DD4hep, added by cpp/CMakeLists.txt when -DCCDB_BUILD_DD4HEP=ON (docs/apis/dd4hep.md):
#   ccdb_dd4hep   plugin library: CCDB_Constants (compact XML constants from a CCDB table) and CCDB_ConditionsLoader
#                 (a DDCond loader of detector element conditions and alignment deltas); the header CCDB_DD4hep.h
#                 (inline AddCondition) is all a program needs at compile time
# Built and tested in the eic-shell image (scripts/eic/dd4hep_tests.sh).

find_package(DD4hep REQUIRED COMPONENTS DDCore DDCond DDAlign)
message(STATUS "CCDB DD4hep plugins: DD4hep ${DD4hep_VERSION} from ${DD4hep_DIR}")

# dd4hep_generate_rootmap writes the .components file into LIBRARY_OUTPUT_PATH, which must be the library's directory
set(CCDB_DD4HEP_LIB_DIR "${CMAKE_BINARY_DIR}/lib/CCDB/dd4hep")
set(LIBRARY_OUTPUT_PATH "${CCDB_DD4HEP_LIB_DIR}")

add_library(ccdb_dd4hep SHARED src/CCDB_Constants.cc src/CCDB_ConditionsLoader.cc)
add_library(ccdb::ccdb_dd4hep ALIAS ccdb_dd4hep)
target_include_directories(ccdb_dd4hep PUBLIC
        "$<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/src>"
        "$<INSTALL_INTERFACE:include/CCDB/DD4hep>")
target_link_libraries(ccdb_dd4hep PUBLIC ccdb DD4hep::DDCore DD4hep::DDCond DD4hep::DDAlign)
target_compile_features(ccdb_dd4hep PUBLIC cxx_std_17)
set_target_properties(ccdb_dd4hep PROPERTIES
        LIBRARY_OUTPUT_DIRECTORY "${CCDB_DD4HEP_LIB_DIR}"
        INSTALL_RPATH_USE_LINK_PATH TRUE)
# libccdb_dd4hep.components next to the library (target Components_ccdb_dd4hep, part of all): the plugin manager finds
# the factories through it on LD_LIBRARY_PATH; DD4hep's function also installs it to lib
dd4hep_generate_rootmap(ccdb_dd4hep)

install(TARGETS ccdb_dd4hep EXPORT ccdbDD4hepTargets
        LIBRARY DESTINATION lib
        ARCHIVE DESTINATION lib
        RUNTIME DESTINATION bin)
install(FILES src/CCDB_DD4hep.h DESTINATION include/CCDB/DD4hep)
install(EXPORT ccdbDD4hepTargets
        NAMESPACE ccdb::
        DESTINATION lib/cmake/ccdb)

# The tests link DD4hep only, not the plugin library: the plugins must be found through the .components file, as in
# any DD4hep program, so building the tests also builds that file
# The tutorial's program (docs/apis/dd4hep-tutorial.md): geometry constants, conditions and alignment from CCDB tables;
# built here, run by scripts/eic/dd4hep_example.sh, not installed
add_executable(ccdb_dd4hep_example examples/ccdb_dd4hep_example.cc)
target_link_libraries(ccdb_dd4hep_example PRIVATE ccdb_dd4hep DD4hep::DDCore DD4hep::DDCond DD4hep::DDAlign)
target_compile_features(ccdb_dd4hep_example PRIVATE cxx_std_17)
add_dependencies(ccdb_dd4hep_example Components_ccdb_dd4hep)

if(CCDB_BUILD_TESTS)
    add_executable(ccdb_dd4hep_tests tests/test_dd4hep.cc)
    target_include_directories(ccdb_dd4hep_tests PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/src" "${CMAKE_CURRENT_SOURCE_DIR}/../cpp/src")
    target_link_libraries(ccdb_dd4hep_tests PRIVATE DD4hep::DDCore DD4hep::DDCond DD4hep::DDAlign)
    add_dependencies(ccdb_dd4hep_tests Components_ccdb_dd4hep)
endif()
