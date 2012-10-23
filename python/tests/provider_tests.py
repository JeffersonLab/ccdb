__author__ = 'RomanovDA'

import unittest
import os
import ccdb.path_utils
from ccdb.model import Directory, TypeTable, TypeTableColumn, ConstantSet, Assignment, RunRange, Variation
from ccdb.model import gen_flatten_data, list_to_blob, blob_to_list, list_to_table
import sqlalchemy.orm.exc

from ccdb import AlchemyProvider

class AlchemyProviderTest(unittest.TestCase):

    def setUp(self):
        sqlite_path = ""
        if "CCDB_HOME" in os.environ: sqlite_path = os.environ["CCDB_HOME"]
        self.sqlite_connection_str = "sqlite:///" + os.path.join(sqlite_path, "mysql", "ccdb.sqlite")
        self.mysql_connection_str = "mysql://ccdb_user@127.0.0.1:3306/ccdb"
        self.provider = AlchemyProvider()

    def test_connection(self):
        self.provider.connect(self.sqlite_connection_str)
        self.provider.connect(self.mysql_connection_str)

    def test_directories(self):
        self.provider.connect(self.sqlite_connection_str)
        print "==> start SQLite directories tests"
        self.universal_test_directories()

        self.provider.connect(self.mysql_connection_str)
        print "==> start MySQL directories tests"
        self.universal_test_directories()

    def universal_test_directories(self):
        """
        test of directories work dependless of database
        """
        #simple get directory
        dir = self.provider.get_directory("/test")
        self.assertIsNotNone(dir)
        self.assertMultiLineEqual(dir.path, "/test")
        self.assertMultiLineEqual(dir.name, "test")

        #search directories
        dirs = self.provider.search_directories("t??t_va*", "/test")
        assert (len(dirs)!=0)

        dirs = self.provider.search_directories("*", "/test")
        assert (len(dirs)>=2)
        print dirs

        dirs = self.provider.search_directories("*", "")
        assert (len(dirs)>=2)
        print dirs

        #cleanup directories
        #Ok, lets check if directory for the next text exists...
        try:
            self.provider.delete_directory("/test/testdir/constants")
        except:
            pass

        try:
            self.provider.delete_directory("/test/testdir")
        except:
            pass

        #cleanup directories
        #Ok, lets check if directory for the next text exists...
        dir = self.provider.create_directory("testdir", "/test")
        self.assertIsNotNone(dir)

        #create subdirectory
        constants_subdir = self.provider.create_directory("constants","/test/testdir","My constants")
        self.assertIsNotNone(constants_subdir)
        self.assertEqual(constants_subdir.comment, "My constants")

        #cannot recreate subdirectory
        self.assertRaises(ValueError, self.provider.create_directory, "constants","/test/testdir","My constants")

        #create another subdirectory
        variables_subdir = self.provider.create_directory("variables","/test/testdir","My constants")

        #test delete
        self.provider.delete_directory("/test/testdir/constants")

        #test can't delete dir with subdirs
        self.assertRaises(ValueError, self.provider.delete_directory, "/test/testdir")

        #test delete by object
        self.provider.delete_directory(variables_subdir)

        #now, when dir doesn't have subdirs and subtables, it can be deleted
        self.provider.delete_directory("/test/testdir")

    def test_type_tables(self):
        self.provider.connect(self.sqlite_connection_str)
        print "==> start SQLite type tables tests"
        self.universal_type_tables()

        self.provider.connect(self.mysql_connection_str)
        print "==> start MySQL type tables tests"
        self.universal_type_tables()

    #noinspection PyBroadException
    def universal_type_tables(self):
        pass
        table = self.provider.get_type_table("/test/test_vars/test_table")
        assert table!=None;
        self.assertEqual(len(table.columns), 3)
        assert table.name == "test_table"
        assert table.path == "/test/test_vars/test_table"
        assert table.parent_dir
        assert table.parent_dir.name == "test_vars"
        assert table.columns[0].name == "x"
        print table

        #get all tables in directory
        tables = self.provider.get_type_tables("/test/test_vars")
        assert len(tables)>=2       #at least 2 tables are located in "/test/test_vars"
        print "  {0} tables in '/test/test_vars' ".format(len(tables))

        #count tables in a directory
        assert self.provider.count_type_tables("/test/test_vars") >= 2

        #SEARCH TYPE TABLES

        #basic search type table functional
        tables = self.provider.search_type_tables("t??t_tab*")
        self.assertNotEqual(len(tables), 0)

        #now lets get all tables from the directory.
        tables = self.provider.search_type_tables("*", "/test/test_vars")
        self.assertNotEqual(len(tables),0)

        #now lets get all tables from root directory.
        tables = self.provider.search_type_tables("t*", "/")
        self.assertEquals(len(tables),0)

        #CREATE AND DELETE

        try:
            #if such type table already extsts.. probably from last failed test...
            #we haven't test it yet, but we should try to delete it
            table = self.provider.get_type_table("/test/test_vars/new_table")
            self.provider.delete_type_table(table)
        except:
            pass

        table = self.provider.create_type_table(
                    name = "new_table",
                    dir_obj_or_path = "/test/test_vars",
                    rowsNumber = 5,
                    columns=[("c","double"), ("a","double"), ("b","int")],
                    comment = "This is temporary created table for test reasons")

        self.assertIsNotNone(table)

        table = self.provider.get_type_table("/test/test_vars/new_table")
        self.assertEqual(table.rows_count, 5)
        self.assertEqual(table._columns_count, 3)
        self.assertEqual(table.name, "new_table")
        self.assertEqual(table.columns[0].name, "c")
        self.assertEqual(table.columns[1].name, "a")
        self.assertEqual(table.columns[2].name, "b")
        self.assertEqual(table.comment, "This is temporary created table for test reasons")

        #delete
        self.provider.delete_type_table(table)
        self.assertRaises(sqlalchemy.orm.exc.NoResultFound, self.provider.get_type_table, "/test/test_vars/new_table")


    def test_run_ranges(self):
        self.provider.connect(self.sqlite_connection_str)
        print "==> start SQLite run ranges tests"
        self.universal_run_ranges_tests()

        self.provider.connect(self.mysql_connection_str)
        print "==> start MySQL run ranges tests"
        self.universal_run_ranges_tests()

    def universal_run_ranges_tests(self):

        # GET RUN-RANGE TEST
        #----------------------------------------------------

        #Get run range by name, test "all" run range
        rr = self.provider.get_named_run_range("all")
        self.assertIsNotNone(rr)

        #Get run range by min and max run values
        rr = self.provider.get_run_range(0, 2000)
        self.assertIsNotNone(rr)

        # NON EXISTENT RUN RANGE
        #----------------------------------------------------
        #Get run range that is not defined
        try:
            rr = self.provider.get_run_range(0, 2001)

            #oh... such run range exists? It shouldn't be... Maybe it is left because of the last tests...
            print "WARNING provider.get_run_range(0, 2001) found run range (should not be there)"
            print "trying to delete rrange and run the test one more time... "
            self.provider.delete_run_range(rr) #(!) <-- test of this function is further
            rr = self.provider.get_run_range(0, 2001)

        except sqlalchemy.orm.exc.NoResultFound:
            pass; #test passed


        # GET OR CREATE RUNRANGE
        #----------------------------------------------------

        #Get or create run-range is the main function to get RunRange without name
        # 0-2001 should be absent or deleted so this function will create run-range
        rr = self.provider.get_or_create_run_range(0, 2001)
        self.assertIsNotNone(rr)
        self.assertNotEquals(rr.id, 0)
        self.assertEquals(rr.min, 0)
        self.assertEquals(rr.max, 2001)

        # DELETE RUN-RANGE TEST
        #----------------------------------------------------
        self.provider.delete_run_range(rr)
        self.assertRaises(sqlalchemy.orm.exc.NoResultFound, self.provider.get_run_range, 0, 2001)

    def test_variations(self):
        self.provider.connect(self.sqlite_connection_str)
        print "==> start SQLite variations tests"
        self.universal_variations_tests()

        self.provider.connect(self.mysql_connection_str)
        print "==> start MySQL variations tests"
        self.universal_variations_tests()

    def universal_variations_tests(self):
        # GET VARIATION TEST
        #----------------------------------------------------

        #Get run range by name, test "all" run range
        v = self.provider.get_variation("default")
        self.assertIsNotNone(v)

        #Get variations by type table
        v = self.provider.get_run_range(0, 2000)
        table = self.provider.get_type_table("/test/test_vars/test_table")
        vs = self.provider.search_variations(table)
        self.assertIsNotNone(vs)
        self.assertNotEquals(len(vs), 0)

        #Get variations by name
        vs = self.provider.get_variations("def*")
        var_names = [var.name for var in vs]
        self.assertIn("default", var_names)

        # NON EXISTENT RUN RANGE
        #----------------------------------------------------
        #Get run range that is not defined
        try:
            v = self.provider.get_variation("abra_kozyabra")

            #oh... such run range exists? It shouldn't be... Maybe it is left because of the last tests...
            print "WARNING provider.get_variation('abra_kozyabra') found but should not be there"
            print "trying to delete variation and run the test one more time... "
            self.provider.delete_variation(v) #(!) <-- test of this function is further
            v = self.provider.get_variation("abra_kozyabra")

        except sqlalchemy.orm.exc.NoResultFound:
            pass; #test passed


        # create variation
        #----------------------------------------------------

        #Get or create run-range is the main function to get RunRange without name
        # 0-2001 should be absent or deleted so this function will create run-range
        v = self.provider.create_variation("abra_kozyabra")
        self.assertIsNotNone(v)
        self.assertNotEquals(v.id, 0)
        self.assertEquals(v.name, "abra_kozyabra")

        # DELETE RUN-RANGE TEST
        #----------------------------------------------------
        self.provider.delete_variation(v)
        self.assertRaises(sqlalchemy.orm.exc.NoResultFound, self.provider.get_variation, "abra_kozyabra")




    def test_assignments(self):
        self.provider.connect(self.sqlite_connection_str)
        print "==> start SQLite assignments tests"
        self.universal_assignments_tests()

        self.provider.connect(self.mysql_connection_str)
        print "==> start MySQL assignments tests"
        self.universal_assignments_tests()


    def universal_assignments_tests(self):

        assignment = self.provider.get_assignment(100, "/test/test_vars/test_table", "default")
        self.assertIsNotNone(assignment)

        #Check that everything is loaded
        tabledData = assignment.constant_set.data_table

        self.assertEquals(len(tabledData),2)
        self.assertEquals(len(tabledData[0]),3)
        self.assertEquals(tabledData[0][0], "2.2")
        self.assertEquals(tabledData[0][1], "2.3")
        self.assertEquals(tabledData[0][2], "2.4")
        self.assertEquals(tabledData[1][0], "2.5")
        self.assertEquals(tabledData[1][1], "2.6")
        self.assertEquals(tabledData[1][2], "2.7")

        #Ok! Lets get all assigments for current types table
        assignments = self.provider.get_assignments("/test/test_vars/test_table")
        self.assertNotEquals(len(assignments), 0)

        assignment = self.provider.create_assignment([[0,1,2],[3,4,5]],"/test/test_vars/test_table", 0, 1000, "default","Test assignment")
        assignment.print_deps()

        self.provider.delete_assignment(assignment)


    def test_gen_flatten_data(self):
        source = [[1,2],[3,"444"]]
        result = list(gen_flatten_data(source))
        assert result[0] == 1
        assert result[1] == 2
        assert result[2] == 3
        assert result[3] == "444"


    def test_list_to_blob(self):
        self.assertMultiLineEqual("1|2|33", list_to_blob([1,2,"33"]))
        self.assertMultiLineEqual("strings|with&delimiter;surprise", list_to_blob(["strings", "with|surprise"]))


    def test_blob_to_list(self):
        self.assertItemsEqual(["1","2","str"], blob_to_list("1|2|str"))
        self.assertItemsEqual(["strings", "with|surprise"], blob_to_list("strings|with&delimiter;surprise"))


    def test_list_to_table(self):
        self.assertRaises(ValueError, list_to_table, [1,2,3], 2)
        self.assertItemsEqual([[1,2,3],[4,5,6]], list_to_table([1,2,3,4,5,6], 3))


class PathUtilsTest(unittest.TestCase):
    """Test of the path_util package"""

    def validate_name_test(self):
        self.assertTrue(ccdb.path_utils.validate_name("this_is_variation2"))
        self.assertFalse(ccdb.path_utils.validate_name("this-is_variation2"))
        self.assertFalse(ccdb.path_utils.validate_name("this:isvariation2"))



















