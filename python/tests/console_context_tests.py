from StringIO import StringIO
import sys

__author__ = 'RomanovDA'

import unittest
import os
import logging

import ccdb.cmd.colorama
import ccdb.path_utils
import ccdb.cmd.themes

from ccdb.cmd.console_context import ConsoleContext

from ccdb.model import Directory, TypeTable, TypeTableColumn, ConstantSet, Assignment, RunRange, Variation
from ccdb.model import gen_flatten_data, list_to_blob, blob_to_list, list_to_table
import sqlalchemy.orm.exc

from ccdb import AlchemyProvider
logger = logging.getLogger("ccdb")


class ConsoleContextTests(unittest.TestCase):
    """
    Tests of ccdb.ConsoleContext and all utilities
    """

    def setUp(self):
        sqlite_path = ""
        if "CCDB_HOME" in os.environ: sqlite_path = os.environ["CCDB_HOME"]
        self.sqlite_connection_str = "sqlite:///" + os.path.join(sqlite_path, "mysql", "ccdb.sqlite")
        self.mysql_connection_str = "mysql://ccdb_user@127.0.0.1:3306/ccdb"

        #initialize but disable colorama
        ccdb.cmd.colorama.init(autoreset=True)
        ccdb.cmd.colorama.deinit()

        #create console context
        self.context = ConsoleContext()
        self.context.silent_exceptions = False
        self.context.theme = ccdb.cmd.themes.NoColorTheme
        self.context.connection_string = self.sqlite_connection_str
        self.context.user_name = "python_tests"
        self.context.register_utilities()

        #save stdout
        self.output = StringIO()
        self.saved_stdout = sys.stdout
        sys.stdout = self.output


    def test_add_rm_assignment(self):
        tests_dir = os.path.dirname(os.path.realpath(__file__))
        test_file = os.path.join(tests_dir, "test_table.txt")
        self.context.process_command_line("add /test/test_vars/test_table test_table.txt")
        print self.output.getvalue()



    def test_context(self):
        self.assertTrue(len(self.context.utils)>0)


    def test_cat(self):
        self.context.process_command_line("cat /test/test_vars/test_table")
        self.assertIn("2.3",  self.output.getvalue())

    def test_cd(self):
        self.context.process_command_line("cd test")

    def test_help(self):
        self.context.process_command_line("help")


    def test_howto(self):
        self.context.process_command_line("howto")


    def test_dump(self):
        self.context.process_command_line("dump /test/test_vars/test_table")

    def test_info(self):
        self.context.process_command_line("info /test/test_vars/test_table")


    def test_ls(self):
        self.context.process_command_line("ls")


    def test_mk_and_rm(self):
        pass
        #TODO make tests for mk* and rm commands here


    def test_pwd(self):
        self.context.process_command_line("pwd")
        self.assertIn("/",  self.output.getvalue())


    def test_rm(self):
        pass
        #TODO test rm


    def test_run(self):
        #default run is 0
        self.context.process_command_line("run")
        self.assertIn("0",  self.output.getvalue())

        #set another run number
        self.context.process_command_line("run 1")
        self.output.truncate(0)
        self.context.process_command_line("run")
        self.assertIn("1",  self.output.getvalue())


    def test_usage(self):
        self.context.process_command_line("usage")


    def test_vers(self):
        self.context.process_command_line("vers /test/test_vars/test_table")





