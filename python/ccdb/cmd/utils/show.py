from ccdb.cmd import ConsoleUtilBase
from ccdb.cmd.Theme import Theme
from ccdb.cmd import is_verbose, is_debug_verbose

#ccdbcmd module interface
def create_util_instance():
    if is_debug_verbose(): print "      registring Show"
    return Show()


#*********************************************************************
#   Class Show - Shows type table data                               *
#                                                                    *
#*********************************************************************
class Show(ConsoleUtilBase):
    """ Shows type table data """
    
    # ccdb utility class descr part 
    #------------------------------
    command = "show"
    name = "Show"
    short_descr = "Shows type table data"
    
    def print_help(ChangeDir):
        print """ Shows type table data """ 
    # ---- end of print_help() ----


    def process(self, args):
        if(is_debug_verbose()):
            print "Show is gained a control over the process."
            print " ".join(args)