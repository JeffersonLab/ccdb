"""

The problem: One wants to hold an XML in CCDB. But 'add' command allows only to load tabled files.
             How to load the XML to the database?

The solution: use python API to load such custom data to CCDB


Suppose we want to store xml file content in CCDB
we created the table with one string column and one row for it

to create a test table use command:
[shell]> ccdb mktbl /test/test_vars/custom_data -r 1 xml_data=string "#Store xml in ccdb"

to check the table exists
[shell]> ccdb info /test/test_vars/custom_data

Now, how to add data...
"""
import ccdb
import io


if __name__ == "__main__":

    #create CCDB api class
    provider = ccdb.AlchemyProvider()                        # this class has all CCDB manipulation functions
    provider.connect("mysql://ccdb_user@localhost/ccdb")     # use usual connection string to connect to database
    provider.authentication.current_user_name = "anonymous"  # to have a name in logs

    #read file
    xml_content = io.open("tt.xml", "r").read()

    #prepare content
    #create_assignment accepts tabled data
    #rows and columns number must correspond to table definition
    tabled_data = [[xml_content]]

    #add data to database
    provider.create_assignment(
        data=tabled_data,
        path="/test/test_vars/custom_data",
        variation_name="default",
        min_run=0,
        max_run=ccdb.INFINITE_RUN,
        comment="Sample adding some data to ")

    #that is it.
    #check it with
    #[shell]> ccdb vers /test/test_vars/custom_data