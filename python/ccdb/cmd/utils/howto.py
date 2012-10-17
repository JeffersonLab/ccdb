from ccdb.cmd import ConsoleUtilBase

import logging

log = logging.getLogger("ccdb.cmd.utils.howto")

#ccdbcmd module interface
def create_util_instance():
    log.debug("      registering HowTo")
    return HowTo()


#*********************************************************************
#   Class HowTo - Prints howtos                                      *
#                                                                    *
#*********************************************************************
class HowTo(ConsoleUtilBase):
    """ Prints howtos """
    
    # ccdb utility class descr part 
    #------------------------------
    command = "howto"
    name = "HowTo"
    short_descr = "Prints howtos"
    help_util = True

    # ---- end of print_help() ----


    def process(self, args):
        log.debug("HowTo is gained a control over the process")
        log.debug("  ".join(args))

        print "No examples yet"

    def print_help(ChangeDir):
        print """
        Prints cases for using the ccdb console tools
        """