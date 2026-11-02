# The JANA2 service of CCDB, added by cpp/CMakeLists.txt when -DCCDB_BUILD_JANA2=ON:
#   ccdb_jana2     shared library with the class CCDB_service (link it to use the class in your code)
#   CCDB_service   JANA2 plugin that provides the service (-Pplugins=CCDB_service)
# It depends on JANA2 and the ccdb library only. Built and tested in the eic-shell image
# (scripts/eic/jana2_tests.sh).

find_package(JANA REQUIRED)
message(STATUS "CCDB JANA2 service: JANA ${JANA_VERSION} from ${JANA_DIR}")

add_library(ccdb_jana2 SHARED src/CCDB_service.cc)
add_library(ccdb::ccdb_jana2 ALIAS ccdb_jana2)
target_include_directories(ccdb_jana2 PUBLIC
        "$<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/src>"
        "$<INSTALL_INTERFACE:include/CCDB/JANA2>")
target_link_libraries(ccdb_jana2 PUBLIC ccdb JANA::jana2_shared_lib)
target_compile_features(ccdb_jana2 PUBLIC cxx_std_17)
set_target_properties(ccdb_jana2 PROPERTIES INSTALL_RPATH_USE_LINK_PATH TRUE)

# The plugin: a shared object without the 'lib' prefix, as JANA2 loads plugins by name from JANA_PLUGIN_PATH
add_library(CCDB_service SHARED src/CCDB_service_plugin.cc)
target_link_libraries(CCDB_service PRIVATE ccdb_jana2)
set_target_properties(CCDB_service PROPERTIES
        PREFIX ""
        LIBRARY_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/lib/CCDB/plugins"
        INSTALL_RPATH "$ORIGIN/../.."
        INSTALL_RPATH_USE_LINK_PATH TRUE)

install(TARGETS ccdb_jana2 EXPORT ccdbJana2Targets
        LIBRARY DESTINATION lib
        ARCHIVE DESTINATION lib
        RUNTIME DESTINATION bin)
install(FILES src/CCDB_service.h DESTINATION include/CCDB/JANA2)
install(TARGETS CCDB_service LIBRARY DESTINATION lib/CCDB/plugins)

# find_package(ccdb CONFIG COMPONENTS jana2) loads this file; plain find_package(ccdb) does not need JANA2
install(EXPORT ccdbJana2Targets
        NAMESPACE ccdb::
        DESTINATION lib/cmake/ccdb)
