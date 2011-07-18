import ccdb

if __name__ == "__main__":
    
    # the base class that provides access to ccdb data is 
    # ccdb.ProviderBase
    # the class that manages data access for MySQL storage is called
    # ccdb.MySQLProvider
    # lets create one and try to connect to database
    
    provider = ccdb.MySQLProvider()
    
    # To connect to database one should use connect() method of the provider
    # 
    # One can just use 
    # 1. provider.connect() - in tis case the function will try to extract
    #    connection string  from CCDB_CONNECTION environment variable 
    #
    # or one can specify the connection string
    # 2. provider.connect(connection_string) will try to use
    #    user connection string
    
    result = provider.connect()
    
    if not result:  
        #we were unable to connect. 
        #maybe CCDB_CONNECTION environment variable is not set
        #trying to connect with explicit connection string
        result = provider.connect("mysql://ccdb_user@localhost")
        
        if not result:
            #were unable to login again
            exit("Unable to connect to ccdb database")
    
    print "Connected to CCDB database"
    
    # one can use provider.is_connected
    # to check connection status 
    #
    # function provider.disconnect() closes the database
    # and frees some resources used by connection/ 
    #
    # at the programm exit all opened connection will be autoclosed closed
    
    print "Are we connected to database? ", provider.is_connected
    
    
    provider.disconnect() # disconnecting
    
    print "Are we connected to database now? ", provider.is_connected
    
    
    # when the provider is connected we can retrieve data from it
    # see next examples
    
    
    
    
            
        
        
