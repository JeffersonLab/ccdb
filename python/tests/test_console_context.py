import unittest
import os
import logging
import sys
import shlex

# python 3 support
try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

import ccdb.cmd.colorama
from ccdb.errors import DirectoryNotFound, TypeTableNotFound
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

        # initialize but disable colorama
        ccdb.cmd.colorama.init(autoreset=True)
        ccdb.cmd.colorama.deinit()

        # create console context
        self.context = ConsoleContext()
        self.context.silent_exceptions = False
        self.context.theme = ccdb.cmd.themes.NoColorTheme()
        self.context.connection_string = self.sqlite_connection_str
        self.context.user_name = "python_tests"
        self.context.register_utilities()

        # save stdout
        self.output = StringIO()
        self.saved_stdout = sys.stdout
        sys.stdout = self.output
        self.err_output = StringIO()
        self.saved_stderr = sys.stderr
        sys.stderr = self.err_output

        # logger
        ch = logging.StreamHandler()
        ch.stream = self.output
        logger.addHandler(ch)
        logger.setLevel(logging.INFO)

    def tearDown(self):
        # restore stdout
        sys.stdout = self.saved_stdout
        sys.stderr = self.saved_stderr

    def test_context(self):
        """Test utils are loaded"""
        self.assertTrue(len(self.context.utils)>0)


    def test_cat(self):
        """cat. General help"""
        self.context.process_command_line("cat /test/test_vars/test_table")
        self.assertIn("2.3", self.output.getvalue())

    def test_variation_backup(self):
        """Test Backup of """

        self.context.process_command_line("cat /test/test_vars/test_table:100:test")
        self.assertIn("2.2", self.output.getvalue())


    def test_cd(self):
        """cd. General test"""
        self.context.process_command_line("cd test")


    def test_help(self):
        """help. Help command test"""
        self.context.process_command_line("help")
        self.assertIn("ls", self.output.getvalue())


    def test_howto(self):
        """howto. General test"""
        self.context.process_command_line("howto")


    def test_dump(self):
        """dump. General and output tests"""
        self.context.theme = ccdb.cmd.themes.ColoredTheme()
        self.context.process_command_line("dump /test/test_vars/test_table")
        text = self.output.getvalue()
        self.assertNotIn("[",text,"Check that dump disabled color output")

        #cleanup
        self.context.theme = ccdb.cmd.themes.NoColorTheme()
        self.output.truncate(0)


    def test_info(self):
        """info. General test"""
        self.context.process_command_line("info /test/test_vars/test_table")
        out_str = self.output.getvalue()
        self.assertIn("test_table", out_str)
        self.assertIn("Test type", out_str)
        self.assertIn("z", out_str)


    def test_ls(self):
        """ls. General test"""
        self.context.process_command_line("ls")
        self.assertIn("test", self.output.getvalue())

    def test_ls_table(self):
        """ls. General test"""
        self.context.process_command_line("ls /test/test_vars/test_table")
        self.assertIn("test", self.output.getvalue())


    def test_mk_rm_dir(self):
        """mkdir, rm. Create directory and delete it"""
        self.context.process_command_line("mkdir /test/auto_testing_dir #Comment for the dir\n something at new line")
        # TODO check test table internals are right
        self.context.process_command_line("rm --force -d /test/auto_testing_dir")

    def test_mktbl_from_file(self):
        """mkdir infer table structure from file"""
        tests_dir = os.path.dirname(os.path.realpath(__file__))
        test_file = os.path.join(tests_dir, "test_table.txt")
        self.context.process_command_line("mktbl -f " + test_file)
        out_str = self.output.getvalue()
        self.assertIn("mktbl <name> -r 2 X Y Z #<comments>", out_str)

        # now lets check more complex example, where we set table name and comment
        self.output.truncate(0)
        self.context.process_command_line("mktbl /test/haha -f " + test_file + " #harasho")
        out_str = str(self.output.getvalue())
        self.assertIn("mktbl /test/haha -r 2 X Y Z #harasho", out_str)

    def test_mk_rm_table(self):
        """mktbl, rm. Create table and delete it"""
        self.context.process_command_line("mktbl /test/auto_testing_table -r 2 x y z #This is comment for my table")
        #TODO check test table internals are right
        self.context.process_command_line("rm --force /test/auto_testing_table")

    def test_mk_rm_variation(self):
        """mkvar, rm. Create variation and delete it"""
        self.context.process_command_line("mkvar auto_testing_variation -p test #hahaha")
        self.context.process(["mkvar", "auto_testing_variation2", "-p", "test"], 0)    # Regression test for GitHub #3
        # TODO check test table internals are right
        self.context.process_command_line("rm --force -v auto_testing_variation")
        self.context.process_command_line("rm --force -v auto_testing_variation2")

    def test_add_rm_assignment(self):
        """add, rm. Add constants and remove them"""
        tests_dir = os.path.dirname(os.path.realpath(__file__))
        test_file = os.path.join(tests_dir, "test_table.txt")
        print(test_file)
        self.context.process_command_line("add /test/test_vars/test_table " + test_file)
        self.output.truncate(0)
        self.context.process_command_line("vers /test/test_vars/test_table")
        text = str(self.output.getvalue())
        line = text.split("\n")[1]
        id = int(shlex.split(line)[0])
        self.context.process_command_line("rm -f -a {0}".format(id))


    def test_pwd(self):
        """pwd. General test"""
        self.context.process_command_line("pwd")
        self.assertIn("/", self.output.getvalue())


    def test_rm(self):
        """rm. General test... But rm is tested in other tests"""
        pass


    def test_run(self):
        """run. Test if 0 is default run"""
        self.context.process_command_line("run")
        self.assertIn("0", self.output.getvalue())


    def test_run_change(self):
        """run. Test run is changed"""
        self.context.process_command_line("run 1")
        self.output.truncate(0)
        self.context.process_command_line("run")
        self.assertIn("1", self.output.getvalue())


    def test_var(self):
        """var. Test if 'default' variation is default"""
        #default run is 0
        self.context.process_command_line("var")
        self.assertIn("default", self.output.getvalue())


    def test_var_change(self):
        """var. Test variation change"""
        self.context.process_command_line("var test_var")
        self.output.truncate(0)
        self.context.process_command_line("var")
        self.assertIn("test_var", self.output.getvalue())


    def test_vers(self):
        """vers. General usage test"""
        self.context.process_command_line("vers /test/test_vars/test_table")
        result = self.output.getvalue()

        # REGRESSION test: for v. 1.02, doesn't show data if context default run is not in run-range
        self.assertIn("500-3000", result, "Because test_table has data for 500-3000 run-range")


    def test_vers_variation_run(self):
        """vers. Test if vers limits variation and run range if -v and -r flags are given"""
        self.context.process_command_line("vers /test/test_vars/test_table -v default -r 0")
        result = self.output.getvalue()

        self.assertNotIn("subtest", result)
        self.assertNotIn("500-3000", result)    # There is test data for 500-3000 run-range


    def test_vers_bad_params(self):
        """vers. Test vers bad parameters"""

        #wrong directory
        self.assertRaises(DirectoryNotFound, self.context.process_command_line, "vers /some/wrong/dir/table")
        self.assertRaises(TypeTableNotFound, self.context.process_command_line, "vers /test/test_vars/wrong_table")

    def test_skip_sqlite_logging(self):
        """
        check that for sqlite connection user name is skipped
        """

        self.context.process_command_line("ls") # run command that requires connection make it to connect
        self.assertEqual('anonymous', self.context.user_name)

    def test_log(self):
        """
        log. general test
        """
        self.context.process_command_line("log")

    def test_logging_errors_to_stderr(self):
        """ Tests if errors are redirected to stderr"""

        # create stderr handler
        stderr_handler = logging.StreamHandler()
        stderr_handler.stream = sys.stderr
        stderr_handler.setLevel(logging.ERROR)
        logger.addHandler(stderr_handler)

        # do something wrong... Muuuuu ha ha ha
        self.context.silent_exceptions = True
        self.context.process_command_line("rm -f -t something_that_never_exist")
        self.assertIn("No type table found by exact path", self.err_output.getvalue())

