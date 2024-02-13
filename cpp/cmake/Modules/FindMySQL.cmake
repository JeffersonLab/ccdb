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
    get_mysql_config_flag("--libs" MySQL_LIB_CONFIGS)

    # For version we don't need separate_output so we don't user the above function
    execute_process(COMMAND "${MySQL_CONFIG_EXECUTABLE}" "--version"
            RESULT_VARIABLE MySQL_CONFIG_RESULT
            OUTPUT_VARIABLE MySQL_VERSION
            OUTPUT_STRIP_TRAILING_WHITESPACE)


    string(REGEX REPLACE "-I" "" MySQL_INCLUDE_DIRS "${MySQL_INCLUDE_DIRS}")
    string(REGEX MATCHALL "-L[^;]+" MySQL_LINK_DIRS "${MySQL_LIB_CONFIGS}")
    string(REGEX REPLACE "-L" "" MySQL_LINK_DIRS "${MySQL_LINK_DIRS}")

    # (!) We now need to remove -L<whatever> from the list before we proceed
    foreach(DIR ${MySQL_LINK_DIRS})
        list(REMOVE_ITEM MySQL_LIB_CONFIGS ${DIR})
    endforeach()

    # Now select -l result
    string(REGEX MATCHALL "-l[^;]+" MySQL_LINK_LIBS "${MySQL_LIB_CONFIGS}")
    string(REGEX REPLACE "-l" "" MySQL_LINK_LIBS "${MySQL_LINK_LIBS}")

    message(DEBUG " FindMySQL MySQL_LIBRARIES=${MySQL_LIB_CONFIGS}")
    message(DEBUG " FindMySQL MySQL_LINK_LIBS=${MySQL_LINK_LIBS}")
    message(DEBUG " FindMySQL MySQL_LINK_DIRS=${MySQL_LINK_DIRS}")
    message(DEBUG " ^^^^^^^^^^^^^^^^^")

    unset(MySQL_LIBRARIES) # Clear before appending properly formatted libraries
    foreach(LIB ${MySQL_LINK_LIBS})
        unset(DEP_LIB)
        find_library(DEP_LIB ${LIB} PATHS ${MySQL_LINK_DIRS} NO_CACHE)
        message(DEBUG "   LIB ${LIB} DEP_LIB ${DEP_LIB}")

        if(DEP_LIB)
            list(APPEND MySQL_LIBRARIES "${DEP_LIB}")
        endif (DEP_LIB)
    endforeach()
    message(DEBUG "MySQL_LIBRARIES ${MySQL_LIBRARIES}")
    message(DEBUG "^^^^^^^^^^^^^^^^^")
else()
    # Fallback to default paths and find the header and libraries manually
    find_path(MySQL_INCLUDE_DIRS NAMES mysql.h
            HINTS ENV MySQL_DIR
            PATH_SUFFIXES include/mysql include/mariadb
    )

    find_library(MySQL_LIBRARIES NAMES mysqlclient mariadb
            HINTS ENV MySQL_DIR
            PATH_SUFFIXES lib lib/mysql lib/mariadb
    )

    include(FindPackageHandleStandardArgs)
    set(MySQL_VERSION "Not Known")
endif()

find_package_handle_standard_args(MySQL REQUIRED_VARS MySQL_INCLUDE_DIRS MySQL_LIBRARIES)