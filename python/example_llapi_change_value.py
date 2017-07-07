"""

The problem: One wants to read some table, change values and add a new assignment with the new values

"""
import ccdb
import os

if __name__ == "__main__":

    # Will connect to demo sqlite DB
    connection = "sqlite:///" + os.path.join(ccdb.get_ccdb_home_path(), 'sql', 'ccdb.sqlite')

    # create CCDB api class
    provider = ccdb.AlchemyProvider()                        # this class has all CCDB manipulation functions
    provider.connect(connection)     # use usual connection string to connect to database
    provider.authentication.current_user_name = "anonymous"  # to have a name in logs

    # get assignment
    assignment = provider.get_assignment("/test/test_vars/test_table2", 1, "test")  # table, run, variation

    # get data in the form of table of strings
    data = assignment.constant_set.data_table

    print("Original data")
    print(data)

    # change the value
    data[0][2] = int(data[0][2])*2

    # add data to database
    provider.create_assignment(
        data=data,
        path="/test/test_vars/test_table2",
        variation_name="test",                                 # here one can add data to different variation
        min_run=0,
        max_run=ccdb.INFINITE_RUN,
        comment="Changed value of the previous assignment")

    # lets read the assignment once again. We will get the latest assignment ==> the assignment we just added
    assignment = provider.get_assignment("/test/test_vars/test_table2", 1, "test")  # table, run, variation
    print("Updated data")
    print(assignment.constant_set.data_table)

    # that is it.
    # check it with
    # [shell]> ccdb vers /test/test_vars/test_table2
    # [shell]> ccdb cat /test/test_vars/test_table2
