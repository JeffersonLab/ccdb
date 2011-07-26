from ccdb.cmd import ConsoleUtilBase
from ccdb.cmd.Theme import Theme
from ccdb.cmd import is_verbose, is_debug_verbose

#ccdbcmd module interface
def create_util_instance():
    if is_debug_verbose(): print "      registring Usage"
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
    
    def print_help(ChangeDir):
        print """ Prints the usage of the command """ 
    # ---- end of print_help() ----


    def process(self, args):
        if(is_debug_verbose()):
            print "Usage is gained a control over the process."
            print " ".join(args)