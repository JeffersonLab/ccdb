import os

from ccdb import get_ccdb_home_path
from ccdb.errors import DatabaseStructureError
import provider_fixture
import helper


class SQLiteAlchemyProviderTest(provider_fixture.AlchemyProviderTest):

    def setUp(self):
        super(SQLiteAlchemyProviderTest, self).setUp()
        self.connection_str = helper.sqlite_test_connection_str
        helper.copy_test_sqlite_db()

    def tearDown(self):
        super(SQLiteAlchemyProviderTest, self).tearDown()
        helper.clean_test_sqlite_db()

    def test_sqlite_wrong_file(self):
        """ Test connection to wrong sqlite file """
        self.assertRaises(DatabaseStructureError, self.provider.connect, "sqlite:///some.crap.file")

    def test_connect_dbv4(self):
        """Tests that one can't connect to schemva V4"""
        ccdb_path = get_ccdb_home_path()
        old_schema_cs = "sqlite:///" + os.path.join(ccdb_path, "python", "tests", "old_schema.dbV4.sqlite")
        self.assertRaises(DatabaseStructureError, self.provider.connect, old_schema_cs)

