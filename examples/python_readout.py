"""

Example of using Low Level python API to readout data from CCDB

"""




import io
import os
import sys

if __name__ == "__main__":
    
    ccdb_home = os.environ["CCDB_HOME"]                      # Should be set!
    sys.path.append(os.path.join(ccdb_home, "python"))       # Set env. variable PYTHONPATH=$CCDB_HOME/python;$PYTHONPATH instead of this line

    import ccdb
    from ccdb import Directory, TypeTable, Assignment

    sqlite_connect_str = "sqlite:///" + os.path.join(ccdb_home,"sql", "ccdb.sqlite")

    # create CCDB api class
    provider = ccdb.AlchemyProvider()                        # this class has all CCDB manipulation functions
    provider.connect(sqlite_connect_str)                     # use usual connection string to connect to database
    provider.authentication.current_user_name = "anonymous"  # to have a name in logs

    # read directory
    directory = provider.get_directory("/test/test_vars")
    print(directory)


    assert (isinstance(directory, Directory))

    print(directory.name)
    print(directory.path)

    for table in directory.type_tables:
        print (table.path)
        print (table.assignments)




    #that is it.
    #check it with
    #[shell]> ccdb vers /test/test_vars/custom_data
