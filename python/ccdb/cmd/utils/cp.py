import posixpath
import logging
import os

from ccdb.errors import DirectoryNotFound
from ccdb.model import Directory, TypeTable
from ccdb.provider import AlchemyProvider
from ccdb.cmd import ConsoleUtilBase, UtilityArgumentParser
from ccdb import BraceMessage as LogFmt

log = logging.getLogger("ccdb.cmd.utils.cp")

# ccdbcmd module interface
def create_util_instance():
    log.debug("   copying data")

    return Copy()

#*********************************************************************
#   Class Info - Copies data to a different assignment               *
#                                                                    *
#*********************************************************************
class Copy(ConsoleUtilBase):
    """Copies data to a different assignment"""

    # ccdb utility class descr part
    # ------------------------------
    command = "cp"
    name = "Copy"
    short_descr = "Copies data from one assignment to another assignment"
    uses_db = True


    def process(self, args):
        """This is an entry point for each time the command is called"""

        if log.isEnabledFor(logging.DEBUG):
            log.debug(LogFmt("{0}Copy is in charge{0}\\".format(os.linesep)))
            log.debug(LogFmt(" |- arguments : '" + "' '".join(args)+"'"))

        # get provider class which has functions for all CCDB database operation
        assert self.context
        provider = self.context.provider
        assert isinstance(provider, AlchemyProvider)

        # process arguments
        parsed_args = self.process_arguments(args)

        if not self.validate(parsed_args):
            return 1   # the return is like application ret. 1 means problems

        path = self.context.prepare_path(parsed_args.raw_path)   # add current path to user input

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
        parser.add_argument("-v", "--variation", default=self.context.current_variation)
        parser.add_argument("-r", "--run", default=self.context.current_run, type=int)

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

        print("""This is empty utility. It is a template and a sample for writing new utilities

    """)


