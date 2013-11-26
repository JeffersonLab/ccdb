import logging
import os

from ccdb.cmd import ConsoleUtilBase
from ccdb.path_utils import validate_name
from ccdb.brace_log_message import BraceMessage as Lfm


log = logging.getLogger("ccdb.cmd.utils.var")


#ccdbcmd module interface
def create_util_instance():
    log.debug("      registering CurrentVariation")
    return CurrentVariation()


#*********************************************************************
#   Class CurrentVariation - gets or sets current working variation  *
#                                                                    *
#*********************************************************************
class CurrentVariation(ConsoleUtilBase):
    """ gets or sets current working run """
    
    # ccdb utility class descr part 
    #------------------------------
    command = "var"
    name = "CurrentVariation"
    short_descr = "gets or sets current working variation"
    
    def print_help(self):
        print """Gets or sets current working variation
        var (no arguments)     displays current variation
        var <variation_name>   sets current variation

Current working variation is the variation that is used by default if no variation specified.
Example:
   >> var smith                  #set 'smith' variation as current working variation
   >> cat some_constants         #prints values for latest constants of smith variation
   >> cat some_constants::john   #prints values for latest constants of john variation

Current working variation can be set on ccdb start by '-v' flag.
 Example:
   \\> ccdb -v smith cat /test/some_constants   #set variation at ccdb start

If no variation specified at ccdb start, current working variation is 'default'
        """
    # ---- end of print_help() ----


    def process(self, args):
        if log.isEnabledFor(logging.DEBUG):
            log.debug(Lfm("{0}CurrentVariation is in charge{0}\\".format(os.linesep)))
            log.debug(Lfm(" |- arguments : '" + "' '".join(args)+"'"))
        
        assert self.context is not None

        if len(args):
            if not validate_name(args[0]):
                raise ValueError("Error. Variation name should consist of A-Z, a-z, 0-9, _")
            self.context.current_variation = args[0]
            log.info(Lfm("Working variation is set to '{}'", self.context.current_variation))
        else:
            #get working run
            print self.context.current_variation
        
        # all is fine
        return 0