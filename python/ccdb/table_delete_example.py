import ccdb
import ccdb.MySQLProvider

provider = ccdb.MySQLProvider()

if not provider.connect("mysql://ccdb_user@localhost"): exit()

#one can call connect without arguments, CCDB_CONNECTION environment variable woild be used in such case
#provider.connect()  