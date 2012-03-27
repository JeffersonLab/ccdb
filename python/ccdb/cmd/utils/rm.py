import posixpath
import logging
import time

from ccdb.ccdb_pyllapi import Directory, ConstantsTypeTable, ConstantsTypeColumn, Variation
from ccdb import MySQLProvider
from ccdb.cmd import ConsoleUtilBase
from ccdb.cmd import Theme
from ccdb.cmd import is_verbose, is_debug_verbose

log = logging.getLogger("ccdb.cmd.utils.rm")

#ccdbcmd module interface
def create_util_instance():
    log.debug("      registring Remove")
    return Remove()


#*********************************************************************
#   Class Info - Prints extended information of object by the path   *
#                                                                    *
#*********************************************************************
class Remove(ConsoleUtilBase):
    """ Removes directory or type table """
    
    # ccdb utility class descr part 
    #------------------------------
    command = "rm"
    name = "Remove"
    short_descr = "Removes directory or type table"
    uses_db = True

    #variables for each process

    rawentry = "/"       #object path with possible pattern, like /mole/*
    path = "/"    #parent path
    
#----------------------------------------
#   process 
#----------------------------------------  
    def process(self, args):
        log.debug("Remove is gained a control over the process.")
        log.debug("   " + " ".join(args))

        assert self.context != None
        provider = self.context.provider
        isinstance(provider, MySQLProvider)
        
        #process arguments
        self.rawentry = ""
        self.object_type = "type_table" 
        self.ask_confirm = True
        self.process_arguments(args)
        
        #correct ending /
        self.path = self.context.prepare_path(self.rawentry)
                
        if not self.rawentry:
            log.warning("No path is given. Use 'help info' or 'usage info' for getting help.")

        self.print_warning()
        
        #ask confirmation
        if self.ask_confirm:
            result = raw_input("To confirm delete type 'yes': ")
            if result != 'yes': return 0
            

        #it is a type table
        if self.object_type == "type_table":
            
            self.type_table = provider.get_type_table(self.path, True)
            if self.type_table:
                if not provider.delete_type_table(self.type_table):
                    log.warning("Unable to delete type table")
            else:
                log.warning("No type table with this path")
                return 1
        
        #it is a directory
        if self.object_type == "directory":
            parent_dir = provider.get_directory(self.path)
            if(parent_dir):
                if not provider.delete_directory(self.type_table):
                    log.warning("Unable to delete directory")
            else:
                log.warning("No directory with this path")
                return 1
        
        #it is a variation
        if self.object_type == "variation":
            variation = provider.get_variation(self.rawentry)
            if not variation:
                log.warning("No variation with this name")
                return 1

            if not provider.delete_variation(variation):
                log.warning("Unable to delete variation")
                return 1
        
        #everything is fine!
        return 0
            
#----------------------------------------
#   process_arguments 
#----------------------------------------  
    def process_arguments(self, args):
        
        #parse loop
        i=0
        token = ""
        while i < len(args):
            token = args[i].strip()
            i+=1
            if token.startswith('-'):
                #it is some command, lets parse what is the command

                #variation
                if token == "-v" or token.startswith("--variation"):
                    if i<len(args):
                        self.rawentry =  args[i]
                        self.object_type = "variation"
                        i+=1
                        
                #directory
                if token == "-d" or token == "--directory":
                    self.rawentry = args[i]
                    self.object_type = "directory"
                    i+=1

                if token == "-f" or token == "--force":
                    self.ask_confirm = False
                
            else:
                #it probably must be a type table path
                self.rawentry = token
                self.object_type = "type_table"
                
                


#----------------------------------------
#   print_warning
#----------------------------------------        
    def print_warning(self):
        "print warning"
        
        print """ 
                    (!) WARNING (!) 
          CCDB is no-delete storage by design!

It is assumed by CCDB design that object names or paths are used in user code. 
Deleting or renaming type table, directory or variation could break the user code 
wich using this names. 

Deleting a table and recreating with different signature could 
lead to even more severe hard-to-diagnose errors.
"""
        


#----------------------------------------
#   print_help 
#----------------------------------------
    def print_help(self):
        "Prints help of the command"
          
        print """Removes type table, directory or variation
    rm <type table path>   - removes type table with given path
    rm -d <directory path> - removes directory with given path
    rm -v <variation name> - removes variation with given name

 Flags:

   -f or --force - removes object without question
    
    """
