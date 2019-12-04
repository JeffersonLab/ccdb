from ccdb.cmd import CliCommandBase

import logging
log = logging.getLogger("ccdb.cmd.commands.pwd")


# ********************************************************************
#   Class PrintWorkDir - Prints working directory                    *
# ********************************************************************
class PrintWorkDir(CliCommandBase):
    """ Prints working directory """
    
    # ccdb utility class descr part 
    #------------------------------
    command = "pwd"
    name = "PrintWorkDir"
    short_descr = "Prints working directory"
    
    def print_help(self):
        print(""" Prints working directory """) 

    def execute(self, args):
        log.debug("  PrintWorkDir is gained a control over the process.")
        log.debug("    ".join(args))
        assert self.context is not None
        print(self.context.current_path)