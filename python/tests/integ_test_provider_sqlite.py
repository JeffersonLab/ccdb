from ccdb.errors import DatabaseStructureError
import tests.provider_fixture
from tests import helper


class SQLiteAlchemyProviderTest(tests.provider_fixture.AlchemyProviderTest):

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

