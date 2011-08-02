#!/bin/csh
#set our environment
if ( ! $?CCDB_HOME ) then
    echo "Error: CCDB_HOME not set, should point to location of this script"
    exit 1
endif
if (! $?LD_LIBRARY_PATH) then
    setenv LD_LIBRARY_PATH $CCDB_HOME/lib
else
    setenv LD_LIBRARY_PATH "$CCDB_HOME/lib":$LD_LIBRARY_PATH
endif
if ( ! $?PYTHONPATH ) then
    setenv PYTHONPATH "$CCDB_HOME/python":"$CCDB_HOME/python/ccdb/ccdb_pyllapi/"
else
    setenv PYTHONPATH "$CCDB_HOME/python":"$CCDB_HOME/python/ccdb/ccdb_pyllapi/":$PYTHONPATH
endif
setenv PATH "$CCDB_HOME/bin":$PATH
