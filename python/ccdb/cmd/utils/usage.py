from ccdb.cmd import ConsoleUtilBase
from ccdb.cmd.Theme import Theme
from ccdb.cmd import is_verbose, is_debug_verbose

def create_util_instance():
    if is_debug_verbose(): print "      registring Usage"
    return Usage()

class Usage(ConsoleUtilBase):
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