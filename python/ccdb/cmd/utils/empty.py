import logging

from ccdb.cmd import ConsoleUtilBase
from ccdb import AlchemyProvider

#######################################################################
#                                                                     #
#      T H I S    I S   E M P T Y   U T I L I T Y   E X A M P L E     #
#                                                                     #
#######################################################################


#logger must be set to ccdb.cmd.utils.<utility command>
log = logging.getLogger("ccdb.cmd.utils.empty")   

#ccdbcmd module interface
def create_util_instance():
    log.debug("      registering Empty")
    return Empty()


#*********************************************************************
#   Class Empty - empty utility example with description             *
#                                                                    *
#*********************************************************************
class Empty(ConsoleUtilBase):
    """empty utility example"""
    
    # ccdb utility class descr part 
    #------------------------------
    command = "empty"
    name = "Empty"
    short_descr = "empty utility example"
    uses_db = True


    def __init(self):
        # variables for each process
        #------------------------------
        self.raw_entry = "/"      #object path with possible pattern, like /mole/*
        self.path = "/"           #parent path


    
#----------------------------------------
#   process 
#----------------------------------------  
    def process(self, args):
        log.debug("VersionsUtility is gained a control over the process.")
        log.debug("   " + " ".join(args))

        assert self.context is not None
        provider = self.context.provider
        isinstance(provider, AlchemyProvider)

        #process arguments
        self.variation = ""
        self.run = -1

        if not len(args):
            print "Please provide ID for assignment. Use help cat to get more information"
            return 1

        if not self.process_arguments(args):
            return 1



        return 0

#----------------------------------------
#   process_arguments 
#----------------------------------------  
    def process_arguments(self, args):
        #solo arguments 
        pass

    
    
#----------------------------------------
#   validate 
#----------------------------------------  
    def validate(self):
        if not self.raw_table_path: return False
        return True

    
#----------------------------------------
#   print_help 
#----------------------------------------
    def print_help(self):
        "Prints help of the command"
        
        print """This is empty utility. It is a template and a sample for writing new utilities

    """
