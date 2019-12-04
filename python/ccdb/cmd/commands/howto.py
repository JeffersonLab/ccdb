from ccdb.cmd import CliCommandBase
from ccdb.brace_log_message import BraceMessage as Lfm
import logging

log = logging.getLogger("ccdb.cmd.commands.howto")


# *********************************************************************
#   Class HowTo - Prints howtos                                       *
# *********************************************************************
class HowTo(CliCommandBase):
    """ Prints howtos """
    
    # ccdb utility class descr part 
    # ------------------------------
    command = "howto"
    name = "HowTo"
    short_descr = "Prints howtos"
    help_util = True
    howtos = []


    # ---- end of print_help() ----
    def execute(self, args):
        log.debug("HowTo is gained a control over the process")
        log.debug(Lfm("Arguments: '{0}'  ".join(args)))

        print ("No examples yet")

    def print_help(self):
        print ("""
        Prints cases for using the ccdb console tools
        """)

    def print_howto_list(self):
        print ("""
1. Add constants to existing table
2. Add constants to a new table

        """)


