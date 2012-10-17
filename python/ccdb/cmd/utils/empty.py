import posixpath
import logging
import time
import sys

import ccdb

from ccdb.cmd import ConsoleUtilBase
from ccdb.cmd import Theme
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
        self.show_borders = True
        self.show_header = True
        self.show_comments = False
        self.show_date = False
    
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
        self.raw_table_path = ""
        self.variation = ""
        self.run = -1
        self.show_borders = True
        self.show_header = True
        self.show_comments = False
        self.show_date = False
    
        self.ass_id = 0
    
        if not len(args):
            print "Please provide ID for assignment. Use help cat to get more information"
            return 1

        if not self.process_arguments(args):
            return 1
            
            #if self.run == -1: 
            #    self.run = self.context.current_run
                
            #if not self.validate():
            #    return 1
            
            #correct path
            #self.table_path = self.context.prepare_path(self.raw_table_path)
            
            #check xuch table really exists
            #table = provider.get_type_table(self.table_path, False)
            #if not table:
            #    logging.warning("Type table %s not found in the DB"% self.table_path)
            #    return 1
            
            #assignment = provider.get_assignment(self.table_path, self.run)


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
