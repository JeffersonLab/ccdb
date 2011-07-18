from ccdb.cmd import ConsoleUtilBase
from ccdb.cmd.Theme import Theme
from ccdb.cmd import is_verbose, is_debug_verbose

def create_util_instance():
    if is_debug_verbose(): print "      registring HowTo"
    return HowTo()

class HowTo(ConsoleUtilBase):
    command = "howto"
    name = "HowTo"
    short_descr = "Prints howtos"
    help_util = True
    
    def print_help(ChangeDir):
       print """ """ 
    # ---- end of print_help() ----


    def process(self, args):
        if(is_debug_verbose()):
            print "HowTo is gained a control over the process."
            print " ".join(args)