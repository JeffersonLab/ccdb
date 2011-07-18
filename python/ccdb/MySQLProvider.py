import ccdb.ccdb_pyllapi
from ccdb.ProviderBase import ProviderBase

class MySQLProvider(ProviderBase):
    """ MySQL database provider 
    
    """
    _provider = ccdb.ccdb_pyllapi.MySQLDataProvider()
    
    def __init__(self):
        _provider = ccdb.ccdb_pyllapi.MySQLDataProvider()
