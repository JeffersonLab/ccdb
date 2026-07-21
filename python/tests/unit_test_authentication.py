import unittest
import os
from ccdb.authentication import EnvironmentAuthentication
from ccdb import AlchemyProvider
from ccdb import testing as helper


class AuthenticationTest(unittest.TestCase):

    def setUp(self):
        helper.recreate_test_sqlite_db()
        self.sqlite_connection_str = helper.sqlite_test_connection_str

        self.provider = AlchemyProvider()

    def test_environment_auth(self):
        self.provider.connect(self.sqlite_connection_str)

        if "CCDB_USER" in os.environ:
            del os.environ["CCDB_USER"]
        if "USER" in os.environ:
            del os.environ["USER"]

        os.environ["CCDB_USER"] = "test_user"

        auth = EnvironmentAuthentication(self.provider)
        self.assertEqual(auth.current_user_name, "test_user")
        self.assertTrue(auth.validate_current_user())





