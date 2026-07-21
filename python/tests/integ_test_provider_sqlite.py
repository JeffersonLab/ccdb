import os

from ccdb import get_ccdb_home_path
from ccdb.errors import DatabaseStructureError
from ccdb import testing as helper

# Have to import it this way as tests may be considered a package or not depending on context
try:
    from . import provider_fixture
except:
    import provider_fixture


# noinspection PyPep8Naming
class SQLiteAlchemyProviderTest(provider_fixture.AlchemyProviderTest):

    def setUp(self):
        super().setUp()
        self.connection_str = helper.sqlite_test_connection_str
        helper.recreate_test_sqlite_db()

    def tearDown(self):
        super().tearDown()
        helper.clean_test_sqlite_db()

    def test_sqlite_wrong_file(self):
        """ Test connection to wrong sqlite file """
        self.assertRaises(DatabaseStructureError, self.provider.connect, "sqlite:///some.crap.file")

    def test_connect_dbv4(self):
        """Tests that one can't connect to schemva V4"""
        ccdb_path = get_ccdb_home_path()
        old_schema_cs = "sqlite:///" + os.path.join(ccdb_path, "python", "tests", "old_schema.dbV4.sqlite")
        self.assertRaises(DatabaseStructureError, self.provider.connect, old_schema_cs)

