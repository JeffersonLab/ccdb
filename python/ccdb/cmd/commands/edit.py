
import logging
import os

import ccdb
import ccdb.path_utils
from ccdb.cmd import CliCommandBase, UtilityArgumentParser
from ccdb import AlchemyProvider
from ccdb import BraceMessage as LogFmt


# logger must be set to ccdb.cmd.utils.<utility command>
log = logging.getLogger("ccdb.cmd.commands.edit")


# ccdbcmd module interface
def create_util_instance():

    log.debug("      registering Edit")
    return Edit()


# *********************************************************************
#   Class Edit- Change a value in a table            *
#                                                                    *
# *********************************************************************
class Edit(CliCommandBase):
    """Edit a value in a table"""

    # ccdb utility class descr part
    # ------------------------------
    command = "edit"
    name = "Edit"
    short_descr = "Edit a value in the table"
    uses_db = True

    def __init__(self):
        super(Edit, self).__init__()
        self.raw_entry = "/"  # object path with possible pattern, like /mole/*

    # ----------------------------------------
    #   cleanup
    # ----------------------------------------
    def __cleanup(self):
        """Call this function in the beginning of command processing to prepare variables for new command"""
        self.raw_entry = "/"

    #
    #   process
    # ----------------------------------------
    def execute(self, args):
        """This is an entry point for each time the command is called"""

        if log.isEnabledFor(logging.DEBUG):
            log.debug(LogFmt("{0}Edit is in charge{0}\\".format(os.linesep)))
            log.debug(LogFmt(" |- arguments : '" + "' '".join(args) + "'"))

        # prepare variables for the new command
        self.__cleanup()

        # get provider class which has functions for all CCDB database operation
        assert self.context
        provider = self.context.provider
        assert isinstance(provider, AlchemyProvider)

        # process arguments
        parsed_args = self.process_arguments(args)

        if not self.validate(parsed_args):
            return 1  # the return is like application ret. 1 means problems

        path = self.context.prepare_path(parsed_args.raw_path)  # add current path to user input

        # try avoid print() and use log to print data
        log.info(LogFmt("{0}raw_path{1} : {2}", self.theme.Accent, self.theme.Reset, parsed_args.raw_path))
        log.info(LogFmt("{0}path{1}     : {2}", self.theme.Accent, self.theme.Reset, path))
        log.info(LogFmt("{0}variation{1}: {2}", self.theme.Accent, self.theme.Reset, parsed_args.variation))
        log.info(LogFmt("{0}run{1}      : {2}", self.theme.Accent, self.theme.Reset, parsed_args.run))

        # the return is like application ret. 0 means OK
        return 0

    # ----------------------------------------
    #   process_arguments
    # ----------------------------------------
    def process_arguments(self, args):
        # solo arguments

        # utility argument parser is argparse which raises errors instead of exiting app
        parser = UtilityArgumentParser()
        parser.add_argument("raw_path")
        parser.add_argument("-c", "--column", default="")
        parser.add_argument("-r", "--row", default="")
        parser.add_argument("-v", "--value")
        return parser.parse_args(args)

    # ----------------------------------------
    #   validate
    # ----------------------------------------
    def validate(self, parsed_args):
        if not ccdb.path_utils.validate_name(parsed_args.raw_path):
            log.error("The wrong path is given")
            return False

        return True

    # ----------------------------------------
    #   print_help
    # ----------------------------------------
    def print_help(self):
        """Prints help for the command"""

        print("""
        -c or --column Columns of the wrong data
        -r or --row Row of the wrong data
        -v or --value Correct value to replace wrong data

    """)
