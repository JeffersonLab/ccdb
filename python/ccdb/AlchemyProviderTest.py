__author__ = 'RomanovDA'

import unittest
import os
import os.path
import sys
from Model import Directory, TypeTable, TypeTableColumn, ConstantSet, Assignment, RunRange, Variation

from AlchemyProvider import AlchemyProvider

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
        assert(dir != None)
        assert(dir.path == "/test")
        assert(dir.name == "test")

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
        assert dir != None

        #create subdirectory
        constants_subdir = self.provider.create_directory("constants","/test/testdir","My constants")
        assert constants_subdir!=None
        assert constants_subdir.comment == "My constants"

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
        assert len(tables) > 0

        #now lets get all tables from the directory.
        tables = self.provider.search_type_tables("*", "/test/test_vars")
        assert len(tables) >0

















