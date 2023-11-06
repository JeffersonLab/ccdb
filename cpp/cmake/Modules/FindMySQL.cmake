# FindMySQL.cmake
# Attempt to find MySQL or MariaDB
#
# This module will set the following variables in your project:
#   MySQL_FOUND - System has MySQL
#   MySQL_INCLUDE_DIRS - the MySQL include directories
#   MySQL_LIBRARIES - the MySQL libraries

# Find mysql_config or mariadb_config executables
find_program(MySQL_CONFIG_EXECUTABLE NAMES mysql_config mariadb_config
        HINTS ENV MySQL_DIR
        PATH_SUFFIXES bin
)

macro(get_mysql_config_flag FLAG OUTPUT_VARIABLE)
    execute_process(COMMAND "${MySQL_CONFIG_EXECUTABLE}" "${FLAG}"
            RESULT_VARIABLE MySQL_CONFIG_RESULT
            OUTPUT_VARIABLE "${OUTPUT_VARIABLE}"
            OUTPUT_STRIP_TRAILING_WHITESPACE)
    if(NOT MySQL_CONFIG_RESULT EQUAL "0")
        message(STATUS "Unable to obtain ${FLAG} from mysql_config/mariadb_config")
    endif()
    separate_arguments("${OUTPUT_VARIABLE}" UNIX_COMMAND "${${OUTPUT_VARIABLE}}")
endmacro()

if(MySQL_CONFIG_EXECUTABLE)
    get_mysql_config_flag("--cflags" MySQL_CFLAGS)
    get_mysql_config_flag("--include" MySQL_INCLUDE_DIRS)
    get_mysql_config_flag("--libs" MySQL_LIBRARIES)

    # For version we don't need separate_output so we don't user the above function
    execute_process(COMMAND "${MySQL_CONFIG_EXECUTABLE}" "--version"
            RESULT_VARIABLE MySQL_CONFIG_RESULT
            OUTPUT_VARIABLE MySQL_VERSION
            OUTPUT_STRIP_TRAILING_WHITESPACE)

    string(REGEX REPLACE "-I" "" MySQL_INCLUDE_DIRS "${MySQL_INCLUDE_DIRS}")
    string(REGEX MATCHALL "-L[^;]+" MySQL_LINK_DIRS "${MySQL_LIBRARIES}")
    string(REGEX MATCHALL "-l[^;]+" MySQL_LINK_LIBS "${MySQL_LIBRARIES}")

    set(MySQL_LIBRARIES) # Clear before appending properly formatted libraries
    foreach(DIR ${MySQL_LINK_DIRS})
        string(REPLACE "-L" "" DIR "${DIR}")
        list(APPEND MySQL_LIBRARIES "-L${DIR}")
    endforeach()
    foreach(LIB ${MySQL_LINK_LIBS})
        string(REPLACE "-l" "" LIB "${LIB}")
        list(APPEND MySQL_LIBRARIES "-l${LIB}")
    endforeach()
else()
    # Fallback to default paths and find the header and libraries manually
    find_path(MySQL_INCLUDE_DIR NAMES mysql.h
            HINTS ENV MySQL_DIR
            PATH_SUFFIXES include/mysql include/mariadb
    )

    find_library(MySQL_LIBRARY NAMES mysqlclient mariadb
            HINTS ENV MySQL_DIR
            PATH_SUFFIXES lib lib/mysql lib/mariadb
    )

    include(FindPackageHandleStandardArgs)
    find_package_handle_standard_args(MySQL DEFAULT_MSG MySQL_INCLUDE_DIR MySQL_LIBRARY)
    set(MySQL_VERSION "Not Known")

    if(MySQL_FOUND)
        set(MySQL_INCLUDE_DIRS "${MySQL_INCLUDE_DIR}")
        set(MySQL_LIBRARIES "${MySQL_LIBRARY}")
    endif()
endif()

mark_as_advanced(MySQL_CONFIG_EXECUTABLE MySQL_INCLUDE_DIR MySQL_LIBRARY)