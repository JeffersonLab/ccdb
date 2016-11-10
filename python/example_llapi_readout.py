"""

Example of using Low Level python API to readout data from CCDB

"""

import os

if __name__ == "__main__":
    
    ccdb_home = os.environ["CCDB_HOME"]                      # Should be set!

    # Set env. variable PYTHONPATH=$CCDB_HOME/python;$PYTHONPATH instead of this line
    # or
    # sys.path.append(os.path.join(ccdb_home, "python"))

    import ccdb
    from ccdb import Directory, TypeTable, Assignment, ConstantSet

    sqlite_connect_str = "sqlite:///" + os.path.join(ccdb_home,"sql", "ccdb.sqlite")

    # create CCDB api class
    provider = ccdb.AlchemyProvider()                        # this class has all CCDB manipulation functions
    provider.connect(sqlite_connect_str)                     # use usual connection string to connect to database
    provider.authentication.current_user_name = "anonymous"  # to have a name in logs

    # read directory
    directory = provider.get_directory("/test/test_vars")
    print(directory)

    # returned directory is python
    assert (isinstance(directory, Directory))

    print(directory.name)           # Name of this directory
    print(directory.path)           # Full path
    print(directory.parent_dir)     # Link to parent directory
    print(directory.sub_dirs)       # Link to child directories

    # directory is SQLAlchemy object, so you can get to its directories right through it
    for table in directory.type_tables:
        print("== TABLE == '{}'".format(table.name))
        print(table.path)
        print(table.comment)
        print(table.created)
        print(table.parent_dir.name)
        print(table.constant_sets)
        print(" ".join([column.name for column in table.columns]))
        print(" ".join([column.type for column in table.columns]))
        print("rows {} x {} columns".format(table.rows_count, table.columns_count))
        print(table.author_id)

    print ("\n\n== Getting tables another way ==")

    # one can get table through a provider
    table = provider.get_type_table("/test/test_vars/test_table2")
    print(table.path)

    # or even through search
    for table in provider.search_type_tables("t??t_tab*"):
        print(table.name)

    # specify directory to search
    for table in provider.search_type_tables("*", "/test/test_vars"):
        print(table.name)

    print("\n\n== Getting all table data ==")

    # As usual, you can querry all data through classes
    table = provider.get_type_table("/test/test_vars/test_table2")

    # The tricky part is:
    # Table has constant sets.
    # Constant set has assignment (like header)
    # Assignment has links to variation, run-range, etc

    for constant_set in table.constant_sets:
        assert (isinstance(constant_set, ConstantSet))
        print(constant_set.assignment.variation.name)
        print(constant_set.assignment.run_range.min)
        print(constant_set.assignment.run_range.max)
        print(constant_set.assignment.request)
        print(constant_set.assignment.author_id)

        # getting data
        print(constant_set.data_table)

        # get data as list?
        print(constant_set.data_list)

    print("\n\n== Getting assignment ==")
    assignment = provider.get_assignment("/test/test_vars/test_table2", 1, "test")  # run, table, variation
    print(assignment)
    print(assignment.constant_set.data_table)

    # One can use previously got objects to do the same
    variation = provider.get_variation("default")                                   # That is how you get variation
    table = provider.get_type_table("/test/test_vars/test_table")
    assignment = provider.get_assignment(table, 1, variation)                       # run, table, variation
    print(assignment)
    print(assignment.constant_set.data_table)

    # getting type table through assignment
    print(assignment.constant_set.type_table.path)

    print("\n\n== Getting variation ==")
    variation = provider.get_variation("test")
    print(variation.name)
    print(variation.comment)
    print(variation.parent.name)

    # Get all data in variation!
    print("\n\n== All data for variation '{}' ==".format(variation.name))
    for assignment in variation.assignments:
        print(assignment.constant_set.type_table.path)
        print(assignment.constant_set.data_table)

    #that is it.
    #check it with
    #[shell]> ccdb vers /test/test_vars/custom_data
