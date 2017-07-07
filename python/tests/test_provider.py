from ccdb.errors import DatabaseStructureError
from provider_fixture import AlchemyProviderTest
import os
import helper

class SQLiteAlchemyProviderTest(AlchemyProviderTest):

    def setUp(self):
        AlchemyProviderTest.setUp(self)
        self.connection_str = helper.sqlite_test_connection_str

    def test_sqlite_wrong_file(self):
        """ Test connection to wrong sqlite file """
        self.assertRaises(DatabaseStructureError, self.provider.connect, "sqlite:///some.crap.file")


class MySQLAlchemyProviderTest(AlchemyProviderTest):

    def setUp(self):
        AlchemyProviderTest.setUp(self)
        self.connection_str = helper.mysql_test_connection_str

