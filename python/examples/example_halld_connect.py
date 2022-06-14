import ccdb
#from ccdb import Directory, TypeTable, Assignment, ConstantSet

#sqlite_connect_str = "mysql://ccdb_user@hallddb.jlab.org/ccdb"

sqlite_connect_str = "mysql://ccdb_user@hallddb.jlab.org/ccdb"

# create CCDB api class
provider = ccdb.AlchemyProvider()                        # this class has all CCDB manipulation functions
provider.connect(sqlite_connect_str)                     # use usual connection string to connect to database
provider.authentication.current_user_name = "anonymous"  # to have a name in logs

# read directory
directory = provider.get_directory("/test/test_vars")
print(directory)