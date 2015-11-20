"""

Example of using Low Level python API to readout data from CCDB

"""
import ccdb
import io


if __name__ == "__main__":
    
    ccdb_home = os.environ["CCDB_HOME"]

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
        comment="Sample adding some XML data to CCDB")

    #that is it.
    #check it with
    #[shell]> ccdb vers /test/test_vars/custom_data
