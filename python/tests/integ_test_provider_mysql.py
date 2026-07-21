from ccdb.errors import AnonymousUserForbiddenError
from ccdb import testing as helper
import unittest
import ccdb

# Have to import it this way as tests may be considered a package or not depending on context
try:
    from . import provider_fixture
except:
    import provider_fixture


class MySQLAlchemyProviderTest(provider_fixture.AlchemyProviderTest):

    mysql_is_recreated = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not MySQLAlchemyProviderTest.mysql_is_recreated:
            MySQLAlchemyProviderTest.mysql_is_recreated = True
            helper.recreate_mysql_db(helper.mysql_test_connection_str)

    def setUp(self):
        super().setUp()
        self.connection_str = helper.mysql_test_connection_str


class PreventAnonymousUserTest(unittest.TestCase):

    provider = None

    def setUp(self):
        # create CCDB api class
        self.provider = ccdb.AlchemyProvider()  # this class has all CCDB manipulation functions
        self.provider.connect(helper.mysql_test_connection_str)  # respects CCDB_TEST_MYSQL_CONNECTION
        self.provider.authentication.current_user_name = "anonymous"    # to have a name in logs

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