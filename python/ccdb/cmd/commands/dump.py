import os
import logging

from ccdb.cmd import CliCommandBase
from ccdb import NoColorTheme

log = logging.getLogger("ccdb.cmd.commands.ls")


# ********************************************************************
#   Class List - Dumps datat table to a file                         *
# ********************************************************************
class Dump(CliCommandBase):
    """ Dumps datat table to a file """

    # ccdb utility class descr part 
    # ------------------------------
    command = "dump"
    name = "Dump"
    short_descr = "Dumps data table"
    uses_db = True
    is_alias = True

    def execute(self, args):
        log.debug("{0}Dump is gained a control {0}\\".format(os.linesep))
        log.debug(" |- arguments: " + " ".join(args))

        theme_backup = self.theme

        self.theme = NoColorTheme()
        # self.context.utils["cat"].theme = NoColorTheme()
        return "cat --no-borders --no-header --comments --time --horizontal " + " ".join(args)

    def print_help(self):
        """Prints help of the command"""
        print(""" Dumps data table to a file
Usage:
        dump <request> <file_name>

Example:
    > cat /test/test_vars/test_table > file.txt              # latest data for test_table
    > cat /test/test_vars/test_table::subtest > file.txt     # latest data in subtest variation
    > cat /test/test_vars/test_table:::2012-08 > file.txt    # data latest for august 2012

Dump accepts the same flags as 'cat' command. See 'help cat' for flags
        """)
