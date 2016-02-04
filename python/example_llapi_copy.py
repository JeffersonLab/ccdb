"""

In this example we want to copy all tables with all data from
/test/test_vars

to a new directory
/test/new

in normal file shell it would be something like
cp /test/test_vars /test/new

in ccdb it is a little more complicated

"""

import os

import datetime

from ccdb.model import ConstantSet

if __name__ == "__main__":

    source_dir = '/test/test_vars'                              # Directory to copy from
    dest_dir = '/test/new'                                      # Directory to copy to

    ccdb_home = os.environ["CCDB_HOME"]  # This environment variable should be set!

    # Set env. variable PYTHONPATH=$CCDB_HOME/python;$PYTHONPATH
    # or sys.path.append(os.path.join(ccdb_home, "python"))
    import ccdb
    from ccdb import TypeTable, Assignment
    from ccdb import path_utils
    from sqlalchemy import desc

    sqlite_connect_str = "sqlite:///" + os.path.join(ccdb_home, "sql", "ccdb.sqlite")

    # create CCDB api class
    provider = ccdb.AlchemyProvider()                           # this class has all CCDB manipulation functions
    provider.connect(sqlite_connect_str)                        # use usual connection string to connect to database
    provider.authentication.current_user_name = "test_user"    # to have a name in logs

    # create new directory
    provider.create_directory('new', '/test')

    # find all tables in /test/test_vars
    source_tables = provider.search_type_tables("*", source_dir)

    # iterate over tables
    for source_table in source_tables:
        assert isinstance(source_table, TypeTable)
        print("copy table '{}' to '{}'".format(source_table.path, dest_dir))

        # create a new table the same as old
        # select column names and column types of the original table
        new_columns = [(column.name, column.type) for column in source_table.columns]
        new_table = provider.create_type_table(source_table.name,           # Name of the table
                                               dest_dir,                    # Parent directory
                                               source_table.rows_count,     # Rows count
                                               new_columns,                 # Columns it should have
                                               source_table.comment)        # Comment

        # now lets copy the data
        for constant_set in source_table.constant_sets:
            assignment = constant_set.assignment

            assert isinstance(constant_set, ConstantSet)
            assert isinstance(assignment, Assignment)

            # create new assignment for the data
            new_assignment = provider.create_assignment(constant_set.data_table,      # Data
                                                        new_table.path,               # Source table
                                                        assignment.run_range.min,     # Run range min run
                                                        assignment.run_range.max,     # Run range max run
                                                        assignment.variation.name,    # variation
                                                        assignment.comment)           # comment

            # Finally we copy creation time because it is used in requests
            new_assignment.created = assignment.created
            provider.update_assignment(new_assignment)

            print("   copy assignment id={} to new (id={} created={})"
                  .format(assignment.id, new_assignment.id, new_assignment.created))







