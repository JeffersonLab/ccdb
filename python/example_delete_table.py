import ccdb;
from ccdb import MySQLProvider
from ccdb import ConstantsTypeTable

#create data provider object
provider = MySQLProvider()


#Connecting to ccdb
if not provider.connect("mysql://ccdb_user@localhost"): 
    exit("Unable to connect to ccdb")
    

#Get table object
table = provider.get_type_table("/test/region_parms")
if not table: 
    exit("No such table")
assert(isinstance(table, ConstantsTypeTable))


#try delete this table
if provider.delete_type_table(table):
    print "Table deleted successfully"
else:
    print "Unable to delete the table"
    
