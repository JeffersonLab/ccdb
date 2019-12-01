from ccdb.cmd import CliCommandBase
import logging

log = logging.getLogger("ccdb.cmd.commands.usage")

#ccdbcmd module interface
def create_util_instance():
    log.debug("      registering Usage")
    return Usage()


#*********************************************************************
#   Class Usage - Prints usage for each util                         *
#                                                                    *
#*********************************************************************
class Usage(CliCommandBase):
    """ Prints usage for each util """
    
    # ccdb utility class descr part 
    #------------------------------
    command = "usage"
    name = "Usage"
    short_descr = "Prints usage for each util"
    help_util = True
    
    def print_help(self):
        print(""" Prints the usage of the command """) 
    # ---- end of print_help() ----


    def execute(self, args):
        log.debug("  Usage is gained a control over the process")
        log.debug(" ".join(args))