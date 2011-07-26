from ccdb.cmd import ConsoleUtilBase
from ccdb.cmd.Theme import Theme
from ccdb.cmd import is_verbose, is_debug_verbose

#ccdbcmd module interface
def create_util_instance():
    if is_debug_verbose(): print "      registring Examples"
    return Examples()


#*********************************************************************
#   Class Examples - Prints example of usage for each util           *
#                                                                    *
#*********************************************************************
class Examples(ConsoleUtilBase):
    """ Prints example of usage for each util """
    
    # ccdb utility class descr part 
    #------------------------------
    command = "examples"
    name = "Examples"
    short_descr = "Prints example of usage for each util"
    help_util = True
    
    def print_help(ChangeDir):
       print """ Prints example of usage for each util """ 
    # ---- end of print_help() ----


    def process(self, args):
        if(is_debug_verbose()):
            print "Examples is gained a control over the process."
            print " ".join(args)