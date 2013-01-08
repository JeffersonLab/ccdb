import unittest
import os
import logging
import sys
import shlex
from StringIO import StringIO

import ccdb.cmd.colorama
import ccdb.path_utils
import ccdb.cmd.themes
from ccdb import get_ccdb_home_path
from ccdb.cmd.console_context import ConsoleContext

logger = logging.getLogger("ccdb")


class ConsoleContextTests(unittest.TestCase):
    """
    Tests of ccdb.ConsoleContext and all utilities
    """

    def setUp(self):
        ccdb_path = get_ccdb_home_path()

        self.sqlite_connection_str = "sqlite:///" + os.path.join(ccdb_path, "sql", "ccdb.sqlite")
        self.mysql_connection_str = "mysql://ccdb_user@127.0.0.1:3306/ccdb"

        #initialize but disable colorama
        ccdb.cmd.colorama.init(autoreset=True)
        ccdb.cmd.colorama.deinit()

        #create console context
        self.context = ConsoleContext()
        self.context.silent_exceptions = False
        self.context.theme = ccdb.cmd.themes.NoColorTheme()
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
        self.context.process_command_line("add /test/test_vars/test_table "+test_file)
        self.output.truncate(0)
        self.context.process_command_line("vers /test/test_vars/test_table")
        text = str(self.output.getvalue())
        line = text.split("\n")[1]
        id = int(shlex.split(line)[0])
        self.context.process_command_line("rm -f -a {0}".format(id))


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
        self.context.theme = ccdb.cmd.themes.ColoredTheme()
        self.context.process_command_line("dump /test/test_vars/test_table")
        text = self.output.getvalue()
        self.assertNotIn("[",text,"Check that dump disabled color output")

        #cleanup
        self.context.theme = ccdb.cmd.themes.NoColorTheme()
        self.output.truncate(0)


    def test_info(self):
        self.context.process_command_line("info /test/test_vars/test_table")


    def test_ls(self):
        self.context.process_command_line("ls")


    def test_mk_rm_dir(self):
        self.context.process_command_line("mkdir /test/auto_testing_dir")
        #TODO check test table internals are wright
        self.context.process_command_line("rm --force -d /test/auto_testing_dir")


    def test_mk_rm_table(self):
        self.context.process_command_line("mktbl /test/auto_testing_table -r 2 x y z #This is comment for my table")
        #TODO check test table internals are wright
        self.context.process_command_line("rm --force /test/auto_testing_table")

    def test_mk_rm_variation(self):
        self.context.process_command_line("mkvar auto_testing_variation")
        #TODO check test table internals are wright
        self.context.process_command_line("rm --force -v auto_testing_variation")


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





