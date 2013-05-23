# script searches for duplicated tables (tables in the same directory with the same name)
#
# This script is to solve duplicate tables issue of CCDB 0.6
# In 0.6 was a situation when user could create several tables with the same name
#


#EDIT the connection string
connection_string = "mysql://ccdb_user@localhost/ccdb"

#-----------------------------------------------------------------------------------------------------------------------
#Next is the script

import collections
import ccdb.provider

if __name__ == "__main__":

    #create ccdb provider
    provider = ccdb.provider.AlchemyProvider()

    #connecting
    try:
        provider.connect(connection_string)
        print("Connected to database")
    except Exception as ex:
        print("ERROR> CCDB provider unable to connect to {0}. Aborting. Exception details: {1}"
              "".format(connection_string, ex))
        exit()

    # it is bug of search_type_tables in 0.7 version.
    # directories are not loaded when search_type_tables is called
    if not provider._are_dirs_loaded:
        provider._load_dirs()

    #use * in table search brings all existing tables
    all_tables = provider.search_type_tables("*")

    #list of full paths of each table
    all_paths = [table.path for table in all_tables]

    #find duplicates
    duplicated_paths = [path for path, count in collections.Counter(all_paths).items() if count > 1]

    if not duplicated_paths:
        print("No duplicated tables found. Nothing to do")
        exit()

    for path in duplicated_paths:
        print("Found: {}".format(path))

    for path in duplicated_paths:
        table = next(table for table in all_tables if table.path == path)

        try:
            provider.delete_type_table(table)
            print("Table is deleted: '{}'".format(path))
        except Exception as ex:
            print("Unable to delete table: '{}'. Error is: {}".format(path, ex))