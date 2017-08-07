from ccdb.errors import DatabaseStructureError
from ccdb.errors import AnonymousUserForbiddenError
from provider_fixture import AlchemyProviderTest
import os
import helper
import unittest
import ccdb
import io


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


class PreventAnonymousUserTest(unittest.TestCase):

    provider = None

    def setUp(self):
        # create CCDB api class
        self.provider = ccdb.AlchemyProvider()  # this class has all CCDB manipulation functions
        self.provider.connect("mysql://ccdb_user@localhost/ccdb_test")  # use usual connection string to connect to database
        self.provider.authentication.current_user_name = "anonymous"  # to have a name in logs

    def test_preventAssignmentCreation(self):

        data = [[0, 1, 2], [3, 4, 5]]
        path = '/test/test_vars/test_table'

        self.assertRaises(AnonymousUserForbiddenError, self.provider.create_assignment,
                          data, path, 0, ccdb.INFINITE_RUN, 'default', 'test comment')

    def test_preventVariationCreation(self):

        self.assertRaises(AnonymousUserForbiddenError, self.provider.create_variation,
                          'test_variation', 'test comment', 'default')

    def test_preventDirectoryCreation(self):

        self.assertRaises(AnonymousUserForbiddenError, self.provider.create_directory,
                          'new_directory', '/test', 'test comment')

    def test_preventTableTypeCreation(self):

        col = [("name", "string")]
        num_rows = 1
        self.assertRaises(AnonymousUserForbiddenError, self.provider.create_type_table,
                          'test_table', '/test/subtest', num_rows, col, 'test comment')