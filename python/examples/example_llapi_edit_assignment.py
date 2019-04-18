"""
This example shows how to change content of the objects.

WARNING - While this example shows how to change data, CCDB is designed so that existing assignments or data sets
          SHOULD NOT BE CHANGED! By design any changes are done through adding new data and/or assignments.
          CCDB works similar to logging and it is a bad idea to change log records.

(!) REAL WARNING (!) - This should be used extremely carefully!
                       Because manipulations with changing objects relation in database
                       COULD possibly be the way to screw CCDB structure up

"""
import ccdb
import io


if __name__ == "__main__":

    # create CCDB api class
    provider = ccdb.AlchemyProvider()                               # this class has all CCDB manipulation functions
    provider.connect("sqlite:////home/user/ccdb.sqlite")            # use connection string to connect to database
    provider.authentication.current_user_name = "anonymous"         # to have a name in logs

    # CHANGING ASSIGNMENT DETAILS
    assignment = provider.get_assignment_by_id(1)    # get assignment by ID, ID is shown in vers command, for example
    # there are other methods of selecting assignment
    # provider.get_assignment(
    #              path_or_table="/test/test_table",
    #              run=102,
    #              variation="mc",
    #              date_and_time=datetime.datetime(year, month, day))

    # set new run-range
    assignment.run_range = provider.get_or_create_run_range(0, ccdb.INFINITE_RUN)   # set e.g. 0, 100 or 100-150

    # change comment
    assignment.comment = "New comment"

    # change variation example (changing variation of the assignment may lead to WAY more consequences)
    # variation = provider.get_variation("test")
    # assignment.variation = variation

    # save the assignment
    provider.update_assignment(assignment)

    # Provider class has other provider.update_* functions which save new state corresponding objects
    # CHANGING COMMENTS
    type_table = provider.get_type_table("/test/test_table")
    type_table.comment = "New comment"
    provider.update_type_table(type_table)

    variation.comment = "New comment"
    provider.update_variation(variation)

    # Finally here is the thing one should never do. Ever. So don't read further.
    data = assignment.constant_set.data_list
    data[2] = 'new value'
    provider.update_assignment(assignment)




