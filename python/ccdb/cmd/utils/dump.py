import os
import logging

from ccdb.cmd import ConsoleUtilBase
from ccdb import NoColorTheme

log = logging.getLogger("ccdb.cmd.utils.ls")


# ccdbcmd module interface
def create_util_instance():
    log.debug("      registering Dump")
    return Dump()


# *********************************************************************
#   Class List - Dumps datat table to a file                         *
#                                                                    *
# *********************************************************************
class Dump(ConsoleUtilBase):
    """ Dumps datat table to a file """

    # ccdb utility class descr part 
    # ------------------------------
    command = "dump"
    name = "Dump"
    short_descr = "Dumps data table"
    uses_db = True

    # variables for each process

    def process(self, args):
        log.debug("{0}Dump is gained a control {0}\\".format(os.linesep))
        log.debug(" |- arguments: " + " ".join(args))

        theme_backup = self.context.theme

        self.context.theme = NoColorTheme()
        # self.context.utils["cat"].theme = NoColorTheme()
        try:
            command = "cat --no-borders --no-header --comments --time --horizontal " + " ".join(args)
            self.context.process_command_line(command)
        finally:
            self.context.theme = theme_backup
            # self.context.utils["cat"].theme = theme_backup

    def print_directory_tree(self, directory, print_full_path, level):
        """prints a full tree of directories
            This is recursive function"""

        # print this directory
        if not print_full_path:
            # noinspection PyUnusedLocal
            print ("".join(["   " for i in range(0, level)]) + directory.name)
        else:
            print (directory.full_path)

        # print subdirectories recursively
        sub_dirs = directory.subdirs
        if len(sub_dirs) > 0:
            for subDir in sub_dirs:
                self.print_directory_tree(subDir, print_full_path, level + 1)

    def print_help(self):
        """Prints help of the command"""
        print (""" Dumps data table to a file
Usage:
        dump <request> <file_name>

Example:
    > cat /test/test_vars/test_table > file.txt              # latest data for test_table
    > cat /test/test_vars/test_table::subtest > file.txt     # latest data in subtest variation
    > cat /test/test_vars/test_table:::2012-08 > file.txt    # data latest for august 2012

Dump accepts the same flags as 'cat' command. See 'help cat' for flags
        """)
