import unittest
import os
import logging
import sys
import shlex

import ccdb.cmd.colorama
from ccdb.errors import DirectoryNotFound, TypeTableNotFound
import ccdb.path_utils
import ccdb.cmd.themes
from ccdb.cmd.console_context import ConsoleContext
import helper

logger = logging.getLogger("ccdb")


class AddThenDumpFileTests(unittest.TestCase):
    """
    Tests of ccdb.ConsoleContext and all utilities
    """

    def setUp(self):
        # We need only sqlite tests. We test that we work with all databases in the provider fixture
        self.sqlite_connection_str = helper.sqlite_test_connection_str

        # initialize but disable colorama
        #ccdb.cmd.colorama.init(autoreset=True)
        #ccdb.cmd.colorama.deinit()

        # create console context
        self.context = ConsoleContext()
        self.context.silent_exceptions = False
        self.context.theme = ccdb.cmd.themes.NoColorTheme()
        self.context.connection_string = self.sqlite_connection_str
        self.context.user_name = "python_tests"
        self.context.register_utilities()
        self.context.provider.authentication.current_user_name = "test_user"

        # logger
        ch = logging.StreamHandler()
        ch.stream = sys.stdout
        logger.addHandler(ch)
        logger.setLevel(logging.INFO)


        # create table
        try:
            self.context.process_command_line("mktbl /test/channel_mc_efficiency -r 5 -c 1")
        except Exception as e:
            if "Such table already exists" in e.message:
                sys.stderr.write("mktbl /test/channel_mc_efficiency already exists")
            else:
                raise

    def tearDown(self):
        with helper.captured_output() as (out, err):
            self.context.process_command_line("vers /test/channel_mc_efficiency")
        text = str(out.getvalue())
        line = text.split("\n")[1]
        assignment_id = int(shlex.split(line)[0])
        self.context.process_command_line("rm -f -a {0}".format(assignment_id))
        self.context.process_command_line("rm -f -t /test/channel_mc_efficiency")

    def test_same_content(self):
        pass

        """When adding, then dumping a file its content should match"""
        self.test_data_path = os.path.join(helper.ccdb_test_path, 'channel_mc_efficiency.list')


        self.context.process_command_line("add /test/channel_mc_efficiency " + self.test_data_path)

        with helper.captured_output() as (out, err):
            self.context.process_command_line("dump /test/channel_mc_efficiency")

        # This can go inside or outside the `with` block
        dumped_str = str(out.getvalue().strip())

        dumped_lines = [line.strip() for line in dumped_str.split('\n')]

        # read the original file
        with open(self.test_data_path, 'r') as content_file:
            original_lines = [line.strip() for line in content_file]
            #original_str = content_file.read()


        self.assertEqual(dumped_lines, original_lines)


