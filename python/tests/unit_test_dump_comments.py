import unittest
import os
import logging
import sys
import shlex

import ccdb.path_utils
import ccdb.cmd.themes
from ccdb.cmd.cli_manager import CliManager, CCDB_EXCEPTIONS_THROW
from ccdb import testing as helper

logger = logging.getLogger("ccdb")


class AddThenDumpFileTests(unittest.TestCase):
    """
    Tests of ccdb.ConsoleContext and all utilities
    """

    def setUp(self):

        # Create a fresh test DB
        helper.recreate_test_sqlite_db()

        # We need only sqlite tests. We test that we work with all databases in the provider fixture
        self.sqlite_connection_str = helper.sqlite_test_connection_str

        # create console context
        self.context = CliManager()
        self.context.exception_handling = CCDB_EXCEPTIONS_THROW
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
            if "Such table already exists" in str(e):
                sys.stderr.write("mktbl /test/channel_mc_efficiency already exists")
            else:
                raise

    def tearDown(self):
        self.context.process_command_line("vers /test/channel_mc_efficiency")
        with helper.captured_output() as (out, err):
            self.context.process_command_line("vers /test/channel_mc_efficiency")
        text = str(out.getvalue())
        line = text.split("\n")[1]
        assignment_id = int(shlex.split(line)[0])
        try:
            self.context.process_command_line("rm -f -a {0}".format(assignment_id))
            self.context.process_command_line("rm -f -t /test/channel_mc_efficiency")
        except Exception as ex:
            print("Error removing '/test/channel_mc_efficiency'. It might be OK(!). " + str(ex) + os.linesep)
            self.context.process_command_line("vers /test/channel_mc_efficiency")

        helper.clean_test_sqlite_db()

    def test_same_content(self):
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

        self.assertEqual(dumped_lines, original_lines)


