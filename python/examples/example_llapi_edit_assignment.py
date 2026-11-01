"""
This example shows what can be changed in stored objects, and how data is changed.

CCDB works like a log: data that was once stored stays as it was, and a new assignment overrides it.
- An assignment's comment, run range and variation, and the comments of tables and variations, can be updated in place.
- The data of an assignment cannot: a stored constant set may be shared by several assignments of a table
  (assignments with byte-equal data use one set), so changing it would change all of them. CCDB refuses with
  ConstantSetIsImmutableError. Data changes by adding a new assignment with the changed values.

(!) Even the allowed changes should be made with care: requests with a time in the past resolve differently
    after an assignment's run range or variation changes.

(!) The example changes the database it runs on: assignment 1 of /test/test_vars/test_table gets the run range
    0-inf, and a newer assignment with one changed value is added. Run it on a demo database.
"""
import os

import ccdb
from ccdb.errors import ConstantSetIsImmutableError


if __name__ == "__main__":

    # Connection string from environment. To create a demo sqlite DB run:
    #   ccdb -c sqlite:////full/path/to/ccdb.sqlite db init --init-i-am-sure
    connection = os.environ["CCDB_CONNECTION"]

    # create CCDB api class
    provider = ccdb.AlchemyProvider()                           # this class has all CCDB manipulation functions
    provider.connect(connection)                                # use usual connection string to connect to database
    provider.authentication.current_user_name = "test_user"     # anonymous user is not allowed to change data

    # CHANGING ASSIGNMENT DETAILS
    assignment = provider.get_assignment_by_id(1)    # get assignment by ID, ID is shown in vers command, for example
    # there are other methods of selecting assignment
    # provider.get_assignment(
    #              path_or_table="/test/test_vars/test_table",
    #              run=102,
    #              variation="mc",
    #              date_and_time=datetime.datetime(year, month, day))

    # set new run-range
    assignment.run_range = provider.get_or_create_run_range(0, ccdb.INFINITE_RUN)   # set e.g. 0, 100 or 100-150

    # change comment
    assignment.comment = "New comment"

    # change variation example (changing variation of the assignment may lead to WAY more consequences)
    # assignment.variation = provider.get_variation("test")

    # save the assignment
    provider.update_assignment(assignment)

    # Provider class has other provider.update_* functions which save new state corresponding objects
    # CHANGING COMMENTS
    type_table = provider.get_type_table("/test/test_vars/test_table")
    type_table.comment = "New comment"
    provider.update_type_table(type_table)

    variation = provider.get_variation("test")
    variation.comment = "New comment"
    provider.update_variation(variation)

    # CHANGING DATA
    # The data of a stored assignment cannot be changed in place
    data = assignment.constant_set.data_table
    data[0][2] = "42.42"
    try:
        assignment.constant_set.data_table = data
    except ConstantSetIsImmutableError as error:
        print("Refused as expected: {}".format(error))

    # The changed values are added as a new assignment. It overrides the old one for the same run range and
    # variation, while requests with an earlier time still get the old data
    new_assignment = provider.create_assignment(
        data=data,
        path=type_table.path,
        min_run=assignment.run_range.min,
        max_run=assignment.run_range.max,
        variation_name=assignment.variation.name,
        comment="Changed one value of assignment {}".format(assignment.id))

    print("Assignment {} has the changed data: {}".format(new_assignment.id, new_assignment.constant_set.data_table))

    # check it with
    # [shell]> ccdb vers /test/test_vars/test_table
    # [shell]> ccdb cat /test/test_vars/test_table
