from ccdb.errors import DatabaseStructureError
from provider_fixture import AlchemyProviderTest
import os


class SQLiteAlchemyProviderTest(AlchemyProviderTest):


    def setUp(self):
        AlchemyProviderTest.setUp(self)
        self.connection_str = "sqlite:///" + os.path.join(self.ccdb_path, "sql", "ccdb.sqlite")

    def test_sqlite_wrong_file(self):
        """ Test connection to wrong sqlite file """
        self.assertRaises(DatabaseStructureError, self.provider.connect, "sqlite:///some.crap.file")


class MySQLAlchemyProviderTest(AlchemyProviderTest):


    def setUp(self):
        AlchemyProviderTest.setUp(self)
        self.connection_str = "mysql://ccdb_user@127.0.0.1:3306/ccdb"

