from ccdb.cmd import ConsoleUtilBase
from ccdb.cmd.Theme import Theme
from ccdb.cmd import is_verbose, is_debug_verbose

def create_util_instance():
    if is_debug_verbose(): print "      registring PrintWorkDir"
    return PrintWorkDir()

class PrintWorkDir(ConsoleUtilBase):
    command = "pwd"
    name = "PrintWorkDir"
    short_descr = "Prints working directory"
    
    def print_help(ChangeDir):
        print """ Prints working directory """ 
    # ---- end of print_help() ----


    def process(self, args):
        if(is_debug_verbose()):
            print "PrintWorkDir is gained a control over the process."
            print " ".join(args)
        
        assert self.context != None

        print self.context.current_path