from ccdb.cmd import ConsoleUtilBase
import logging

log = logging.getLogger("ccdb.cmd.utils.usage")

#ccdbcmd module interface
def create_util_instance():
    log.debug("      registering Usage")
    return Usage()


#*********************************************************************
#   Class Usage - Prints usage for each util                         *
#                                                                    *
#*********************************************************************
class Usage(ConsoleUtilBase):
    """ Prints usage for each util """
    
    # ccdb utility class descr part 
    #------------------------------
    command = "usage"
    name = "Usage"
    short_descr = "Prints usage for each util"
    help_util = True
    
    def print_help(self):
        print """ Prints the usage of the command """ 
    # ---- end of print_help() ----


    def process(self, args):
        log.debug("  Usage is gained a control over the process")
        log.debug(" ".join(args))