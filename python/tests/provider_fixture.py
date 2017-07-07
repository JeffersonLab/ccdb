import unittest
import os
from ccdb import get_ccdb_home_path
from ccdb.model import gen_flatten_data, list_to_blob, blob_to_list, list_to_table, TypeTableColumn
from ccdb.model import LogRecord, User
from ccdb.errors import DatabaseStructureError, TypeTableNotFound, DirectoryNotFound, \
    UserNotFoundError, VariationNotFound, RunRangeNotFound

from ccdb import AlchemyProvider
from tests import helper


class AlchemyProviderTest(unittest.TestCase):
    ccdb_path = get_ccdb_home_path()
    _connection_str = helper.sqlite_test_connection_str
    _provider = AlchemyProvider()

    @property
    def provider(self):
        return self._provider

    @property
    def connection_str(self):
        return self._connection_str

    @connection_str.setter
    def connection_str(self, connection_str):
        self._connection_str = connection_str

    def setUp(self):
        self._provider = AlchemyProvider()
        self.provider.logging_enabled = False
        self.provider.authentication.current_user_name = "test_user"

    def test_connection(self):
        """ Tests that provider connects successfully"""
        self.provider.connect(self.connection_str)

    def test_connect_to_old_schema(self):
        """ Test connection to schema with wrong version """
        ccdb_path = get_ccdb_home_path()
        old_schema_cs = "sqlite:///" + os.path.join(ccdb_path, "python", "tests", "old_schema.ccdb.sqlite")
        self.assertRaises(DatabaseStructureError, self.provider.connect, old_schema_cs)

    def test_directories(self):
        """ Test of directories"""
        self.provider.connect(self.connection_str)   # this test requires the connection

        # simple get directory
        dir_obj = self.provider.get_directory("/test")
        self.assertIsNotNone(dir_obj)
        self.assertMultiLineEqual(dir_obj.path, "/test")
        self.assertMultiLineEqual(dir_obj.name, "test")

        # search directories
        dirs = self.provider.search_directories("t??t_va*", "/test")
        assert (len(dirs) != 0)

        dirs = self.provider.search_directories("*", "/test")
        assert (len(dirs) >= 2)

        dirs = self.provider.search_directories("*", "")
        assert (len(dirs) >= 2)

        # cleanup directories
        # Ok, lets check if directory for the next text exists...
        try:
            self.provider.delete_directory("/test/testdir/constants")
        except DirectoryNotFound:
            pass

        try:
            self.provider.delete_directory("/test/testdir")
        except DirectoryNotFound:
            pass

        # cleanup directories
        # Ok, lets check if directory for the next text exists...
        dir_obj = self.provider.create_directory("testdir", "/test")
        self.assertIsNotNone(dir_obj)

        self.provider.logging_enabled = True    # enable logging to test log too

        # create subdirectory
        constants_subdir = self.provider.create_directory("constants", "/test/testdir", "My constants")
        self.assertIsNotNone(constants_subdir)
        self.assertEqual(constants_subdir.comment, "My constants")

        # check log
        log = self.provider.get_log_records(limit=1)[0]
        assert (isinstance(log, LogRecord))
        self.assertEqual(log.action, "create")
        self.assertEqual(log.affected_ids, "|directories" + str(constants_subdir.id) + "|")
        self.assertEqual(log.comment, "My constants")
        self.assertIn("Created directory", log.description)
        self.provider.logging_enabled = False

        # cannot recreate subdirectory
        self.assertRaises(ValueError, self.provider.create_directory, "constants", "/test/testdir", "My constants")

        # create another subdirectory
        variables_subdir = self.provider.create_directory("variables", "/test/testdir", "My constants")

        # test delete
        self.provider.delete_directory("/test/testdir/constants")

        # test can't delete dir with sub dirs
        self.assertRaises(ValueError, self.provider.delete_directory, "/test/testdir")

        # test delete by object
        self.provider.delete_directory(variables_subdir)

        # now, when dir doesn't have sub dirs and sub tables, it can be deleted
        self.provider.delete_directory("/test/testdir")

    # noinspection PyBroadException
    def test_type_tables(self):
        """
        Test type table operation
        @return: None
        """
        self.provider.connect(self.connection_str)   # this test requires the connection

        table = self.provider.get_type_table("/test/test_vars/test_table")
        assert table is not None
        self.assertEqual(len(table.columns), 3)
        assert table.name == "test_table"
        assert table.path == "/test/test_vars/test_table"
        assert table.parent_dir
        assert table.parent_dir.name == "test_vars"
        assert table.columns[0].name == "x"

        # get all tables in directory
        tables = self.provider.get_type_tables("/test/test_vars")
        assert len(tables) >= 2       # at least 2 tables are located in "/test/test_vars"

        # count tables in a directory
        assert self.provider.count_type_tables("/test/test_vars") >= 2

        # SEARCH TYPE TABLES

        # basic search type table functional
        tables = self.provider.search_type_tables("t??t_tab*")
        self.assertNotEqual(len(tables), 0)
        self.assertIn("/", tables[0].path)

        # now lets get all tables from the directory.
        tables = self.provider.search_type_tables("*", "/test/test_vars")
        self.assertNotEqual(len(tables), 0)
        for table in tables:
            self.assertEqual(table.path, "/test/test_vars" + "/" + table.name)

        # now lets get all tables from root directory.
        tables = self.provider.search_type_tables("t*", "/")
        self.assertEquals(len(tables), 0)

        # CREATE AND DELETE

        try:
            # if such type table already exists.. probably from last failed test...
            # we haven't test it yet, but we should try to delete it
            table = self.provider.get_type_table("/test/test_vars/new_table")
            self.provider.delete_type_table(table)
        except:
            pass

        table = self.provider.create_type_table(
            name="new_table",
            dir_obj_or_path="/test/test_vars",
            rows_num=5,
            columns=[('c', 'double'), ('a', 'double'), ('b', 'int')],
            comment="This is temporary created table for test reasons")

        self.assertIsNotNone(table)

        table = self.provider.get_type_table("/test/test_vars/new_table")
        self.assertEqual(table.rows_count, 5)
        self.assertEqual(table.columns_count, 3)
        self.assertEqual(table.name, 'new_table')
        self.assertEqual(table.columns[0].name, 'c')
        self.assertEqual(table.columns[0].type, 'double')
        self.assertEqual(table.columns[1].name, 'a')
        self.assertEqual(table.columns[1].type, 'double')
        self.assertEqual(table.columns[2].name, 'b')
        self.assertEqual(table.columns[2].type, 'int')
        self.assertEqual(table.comment, "This is temporary created table for test reasons")

        # delete
        self.provider.delete_type_table(table)
        self.assertRaises(TypeTableNotFound, self.provider.get_type_table, "/test/test_vars/new_table")

    def test_run_ranges(self):
        """Test run ranges """

        self.provider.connect(self.connection_str)   # this test requires the connection

        # Get run range by name, test "all" run range
        rr = self.provider.get_named_run_range("all")
        self.assertIsNotNone(rr)

        # Get run range by min and max run values
        rr = self.provider.get_run_range(0, 2000)
        self.assertIsNotNone(rr)

        # NON EXISTENT RUN RANGE
        # ----------------------------------------------------
        # Get run range that is not defined
        try:
            rr = self.provider.get_run_range(0, 2001)

            # oh... such run range exists? It shouldn't be... Maybe it is left because of the last tests...
            print ("WARNING provider.get_run_range(0, 2001) found run range (should not be there)")
            print ("trying to delete run range and run the test one more time... ")
            self.provider.delete_run_range(rr)      # (!) <-- test of this function is further
            rr = self.provider.get_run_range(0, 2001)
            self.assertIsNotNone(rr)

        except RunRangeNotFound:
            pass      # test passed

        # GET OR CREATE RUNRANGE
        # ----------------------------------------------------

        # Get or create run-range is the main function to get RunRange without name
        # 0-2001 should be absent or deleted so this function will create run-range
        rr = self.provider.get_or_create_run_range(0, 2001)
        self.assertIsNotNone(rr)
        self.assertNotEquals(rr.id, 0)
        self.assertEquals(rr.min, 0)
        self.assertEquals(rr.max, 2001)

        # DELETE RUN-RANGE TEST
        # ----------------------------------------------------
        self.provider.delete_run_range(rr)
        self.assertRaises(RunRangeNotFound, self.provider.get_run_range, 0, 2001)

    def test_variations(self):
        """Test variations"""
        self.provider.connect(self.connection_str)   # this test requires the connection

        # Get variation by name, test "all" run range
        v = self.provider.get_variation("default")
        self.assertIsNotNone(v)

        # Get variations by type table
        table = self.provider.get_type_table("/test/test_vars/test_table")
        vs = self.provider.search_variations(table)
        self.assertIsNotNone(vs)
        self.assertNotEquals(len(vs), 0)

        # Get variations by name
        vs = self.provider.get_variations("def*")
        var_names = [var.name for var in vs]
        self.assertIn("default", var_names)

        # NON EXISTENT VARIATION
        # ----------------------------------------------------
        # Get run range that is not defined
        try:
            v = self.provider.get_variation("abra_kozyabra")

            # oh... such run range exists? It shouldn't be... Maybe it is left because of the last tests...
            print ("WARNING provider.get_variation('abra_kozyabra') found but should not be there")
            print ("trying to delete variation and run the test one more time... ")
            self.provider.delete_variation(v)    # (!) <-- test of this function is further
            v = self.provider.get_variation("abra_kozyabra")
            self.assertIsNotNone(v)

        except VariationNotFound:
            pass     # test passed

        # create variation
        # ----------------------------------------------------

        # Get or create run-range is the main function to get RunRange without name
        # 0-2001 should be absent or deleted so this function will create run-range
        v = self.provider.create_variation("abra_kozyabra")
        self.assertIsNotNone(v)
        self.assertNotEquals(v.id, 0)
        self.assertEquals(v.parent_id, 1)
        self.assertEquals(v.name, "abra_kozyabra")

        # DELETE RUN-RANGE TEST
        # ----------------------------------------------------
        self.provider.delete_variation(v)
        self.assertRaises(VariationNotFound, self.provider.get_variation, "abra_kozyabra")

        # Now create with comment and parent
        v = self.provider.create_variation("abra_kozyabra", "Abra!!!", "test")
        self.assertEquals(v.parent.name, "test")
        self.assertEquals(v.comment, "Abra!!!")

        # cleanup
        self.provider.delete_variation(v)

    def test_variation_backup(self):
        """Test Backup of """
        self.provider.connect(self.connection_str)   # this test requires the connection

        a = self.provider.get_assignment("/test/test_vars/test_table", 100, "test")
        self.assertEqual(a.constant_set.data_list[0], "2.2")

        # No such calibration exist in test variation run 100, but constants should fallback to variation default

    def test_assignments(self):
        """Test Assignments"""
        self.provider.connect(self.connection_str)   # this test requires the connection

        assignment = self.provider.get_assignment("/test/test_vars/test_table", 100, "default")
        self.assertIsNotNone(assignment)

        # Check that everything is loaded
        tabled_data = assignment.constant_set.data_table
        self.assertEquals(len(tabled_data), 2)
        self.assertEquals(len(tabled_data[0]), 3)
        self.assertEquals(tabled_data[0][0], "2.2")
        self.assertEquals(tabled_data[0][1], "2.3")
        self.assertEquals(tabled_data[0][2], "2.4")
        self.assertEquals(tabled_data[1][0], "2.5")
        self.assertEquals(tabled_data[1][1], "2.6")
        self.assertEquals(tabled_data[1][2], "2.7")

        # Ok! Lets get all assignments for current types table
        assignments = self.provider.get_assignments("/test/test_vars/test_table")
        self.assertNotEquals(len(assignments), 0)

        # Ok! Lets get all assignments for current types table and variation
        assignments = self.provider.get_assignments("/test/test_vars/test_table", variation="default")
        self.assertNotEquals(len(assignments), 0)

        assignment = self.provider.create_assignment([[0, 1, 2], [3, 4, 5]], "/test/test_vars/test_table", 0, 1000,
                                                     "default", "Test assignment")
        self.assertEqual(assignment.constant_set.type_table.path, "/test/test_vars/test_table")
        self.assertEqual(assignment.variation.name, "default")
        self.assertEqual(assignment.run_range.min, 0)
        self.assertEqual(assignment.run_range.max, 1000)
        self.assertEqual(assignment.comment, "Test assignment")
        tabled_data = assignment.constant_set.data_table
        self.assertEquals(len(tabled_data), 2)
        self.assertEquals(len(tabled_data[0]), 3)
        self.assertEquals(tabled_data[0][0], "0")
        self.assertEquals(tabled_data[0][1], "1")
        self.assertEquals(tabled_data[0][2], "2")
        self.assertEquals(tabled_data[1][0], "3")
        self.assertEquals(tabled_data[1][1], "4")
        self.assertEquals(tabled_data[1][2], "5")

        self.provider.delete_assignment(assignment)

    def test_users(self):
        """Test users"""
        self.provider.connect(self.connection_str)   # this test requires the connection

        user = self.provider.get_user("anonymous")
        self.assertIsNotNone(user)
        self.assertEqual(user.name, "anonymous")

        user = self.provider.get_user("test_user")
        isinstance(user, User)
        self.assertIsNotNone(user)
        self.assertEqual(user.password, "test")
        self.assertEqual(user.roles, ["runrange_crate", "runrange_delete"])
        # self.assertEqual(user.)

        # test that with wrong user we can't create anything
        self.provider.authentication.current_user_name = "non_exist_user_ever"
        self.assertRaises(UserNotFoundError, self.provider.create_directory, "some_strange_dir", "/")
        self.assertEqual(0, len(self.provider.search_directories("some_strange_dir")))
        self.assertRaises(UserNotFoundError, self.provider.update_directory, self.provider.get_directory("/test"))
        self.assertRaises(UserNotFoundError, self.provider.delete_directory, self.provider.get_directory("/test"))
        self.assertIsNotNone(self.provider.get_directory("/test"))

    @staticmethod
    def test_gen_flatten_data():
        source = [[1, 2], [3, "444"]]
        result = list(gen_flatten_data(source))
        assert result[0] == 1
        assert result[1] == 2
        assert result[2] == 3
        assert result[3] == "444"

    def test_list_to_blob(self):
        self.assertMultiLineEqual("1|2|33", list_to_blob([1, 2, "33"]))
        self.assertMultiLineEqual("strings|with&delimiter;surprise", list_to_blob(["strings", "with|surprise"]))

    def test_blob_to_list(self):
        self.assertItemsEqual(["1", "2", "str"], blob_to_list("1|2|str"))
        self.assertItemsEqual(["strings", "with|surprise"], blob_to_list("strings|with&delimiter;surprise"))

    def test_list_to_table(self):
        self.assertRaises(ValueError, list_to_table, [1, 2, 3], 2)
        self.assertItemsEqual([[1, 2, 3], [4, 5, 6]], list_to_table([1, 2, 3, 4, 5, 6], 3))

    def test_get_users(self):
        self.provider.connect(self.connection_str)   # this test requires the connection
        users = self.provider.get_users()
        self.assertGreater(len(users), 0)

    def test_validate_data(self):
        column = TypeTableColumn()

        # int type
        column.type = 'int'
        self.assertEqual(self.provider.validate_data_value('1', column), 1)
        self.assertRaises(ValueError, self.provider.validate_data_value, 'hren', column)

        # lets check bool type
        column.type = 'bool'
        self.assertEqual(self.provider.validate_data_value('TrUe', column), True)
        self.assertEqual(self.provider.validate_data_value('FalSe', column), False)
        self.assertEqual(self.provider.validate_data_value('1', column), True)
        self.assertEqual(self.provider.validate_data_value('0', column), False)
        self.assertRaises(ValueError, self.provider.validate_data_value, 'hren', column)

        # uint!
        column.type = 'uint'
        self.assertEqual(self.provider.validate_data_value('1', column), 1)
        self.assertRaises(ValueError, self.provider.validate_data_value, '-1', column)
