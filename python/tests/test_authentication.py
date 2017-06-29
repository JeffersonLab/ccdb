import unittest
import os
from ccdb import get_ccdb_home_path
from ccdb.authentication import EnvironmentAuthentication
from ccdb import AlchemyProvider


class AuthenticationTest(unittest.TestCase):

    def setUp(self):
        ccdb_path = get_ccdb_home_path()

        self.sqlite_connection_str = "sqlite:///" + os.path.join(ccdb_path, "sql", "ccdb.sqlite")
        self.mysql_connection_str = "mysql://ccdb_user@127.0.0.1:3306/ccdb"
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





