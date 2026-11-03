import os
import logging
import shlex

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

        self.theme = NoColorTheme()
        return "cat " + " ".join(shlex.quote(arg) for arg in self.cat_flags(args) + list(args))

    # dump's defaults, each with every flag of its pair: a default goes to cat only when the user named neither
    # flag of the pair, so `dump -nc` prints no comment line instead of an argparse conflict (issue #99)
    DEFAULTS = (
        ("--no-borders", ("-b", "--borders", "-nb", "--no-borders")),
        ("--no-header", ("-h", "--header", "-nh", "--no-header")),
        ("--comments", ("-c", "--comments", "-nc", "--no-comments")),
        ("--horizontal", ("-ph", "--horizontal", "-pv", "--vertical")),
    )

    @classmethod
    def cat_flags(cls, args):
        """The flags dump adds to the user's arguments for cat"""
        named = set(args)
        return [default for default, pair in cls.DEFAULTS if not named.intersection(pair)]

    def print_help(self):
        """Prints help of the command"""
        print(""" Dumps data table to a file
Usage:
        dump <request> <file_name>

Example:
    > cat /test/test_vars/test_table > file.txt              # latest data for test_table
    > cat /test/test_vars/test_table::subtest > file.txt     # latest data in subtest variation
    > cat /test/test_vars/test_table:::2012-08 > file.txt    # data latest for august 2012

Dump is 'cat --no-borders --no-header --comments --horizontal'. It accepts the flags of 'cat' (see 'help cat'),
and a flag the user names replaces dump's default of the same pair:
    > dump -nc /test/test_vars/test_table > file.txt         # no comment line
        """)
