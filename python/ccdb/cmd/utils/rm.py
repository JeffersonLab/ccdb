import logging
import os
from ccdb import AlchemyProvider
from ccdb.cmd import ConsoleUtilBase
from sqlalchemy.orm.exc import NoResultFound

log = logging.getLogger("ccdb.cmd.utils.rm")

#ccdbcmd module interface
def create_util_instance():
    log.debug("      registering Remove")
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

    raw_entry = "/"       #object path with possible pattern, like /mole/*
    path = "/"    #parent path
    
#----------------------------------------
#   process 
#----------------------------------------  
    def process(self, args):
        log.debug("{0}Remove is gained a control{0}\\".format(os.linesep))
        log.debug(" |- arguments: " + " ".join(["'"+arg+"'" for arg in args]))

        assert self.context is not None
        provider = self.context.provider
        isinstance(provider, AlchemyProvider)
        
        #process arguments
        self.raw_entry = ""
        self.object_type = "type_table" 
        self.ask_confirm = True
        self.process_arguments(args)
        log.debug(" |- object_type: '{0}'".format(self.object_type))
        log.debug(" |- ask confirm: '{0}'".format(self.ask_confirm))
        log.debug(" |- raw entry:   '{0}'".format(self.raw_entry))

        #correct ending /
        self.path = self.context.prepare_path(self.raw_entry)
                
        if not self.raw_entry:
            log.warning("No path is given. Use 'help info' or 'usage info' for getting help.")

        self.print_warning()
        
        #ask confirmation
        if self.ask_confirm:
            result = raw_input("To confirm delete type 'yes': ")
            if result != 'yes':
                return 0

        #it is a type table
        if self.object_type == "type_table":

            try:
                self.type_table = provider.get_type_table(self.path)
                provider.delete_type_table(self.type_table)
            except NoResultFound:
                log.warning("No type table with this path: '{0}'".format(self.path))
                raise
        
        #it is a directory
        if self.object_type == "directory":
            try:
                parent_dir = provider.get_directory(self.path)
                provider.delete_directory(parent_dir)
            except KeyError:
                log.warning("No directory with this path: '{0}'".format(self.path))
                raise
        
        #it is a variation
        if self.object_type == "variation":
            try:
                variation = provider.get_variation(self.raw_entry)
                provider.delete_variation(variation)
            except NoResultFound:
                log.warning("Unable to delete variation '{0}'".format(self.raw_entry))
                raise

        if self.object_type == "assignment":
            assignment = provider.get_assignment_by_id(int(self.raw_entry))
            provider.delete_assignment(assignment)
            #TODO use request instead of id

        #everything is fine!
        return 0
            
#----------------------------------------
#   process_arguments 
#----------------------------------------  
    def process_arguments(self, args):
        
        #parse loop
        i=0
        while i < len(args):
            token = args[i].strip()
            i+=1
            if token.startswith('-'):
                #it is some command, lets parse what is the command

                #variation
                if token == "-v" or token.startswith("--variation"):
                    if i<len(args):
                        self.raw_entry =  args[i]
                        self.object_type = "variation"
                        i+=1
                        
                #directory
                if token == "-d" or token == "--directory":
                    self.raw_entry = args[i]
                    self.object_type = "directory"
                    i+=1

                if token == "-a" or token == "--assignment":
                    self.raw_entry = args[i]
                    self.object_type = "assignment"
                    i+=1

                if token == "-f" or token == "--force":
                    self.ask_confirm = False
                
            else:
                #it probably must be a type table path
                self.raw_entry = token
                self.object_type = "type_table"
                
                


#----------------------------------------
#   print_warning
#----------------------------------------        
    def print_warning(self):
        """print warning"""
        
        print """ 
                    (!) WARNING (!) 
          CCDB is no-delete storage by design!

It is assumed by CCDB design that object names or paths are used in user code. 
Deleting or renaming type table, directory or variation could break the user code 
which using this names.

Deleting a table and recreating with different signature could 
lead to even more severe hard-to-diagnose errors.
"""
        


#----------------------------------------
#   print_help 
#----------------------------------------
    def print_help(self):
        """Prints help of the command"""
          
        print """Removes type table, directory or variation
    rm <type table path>   - removes type table with given path
    rm -d <directory path> - removes directory with given path
    rm -v <variation name> - removes variation with given name
    rm -a <assignment id>  - Assignment db id from 'vers' command*

 Flags:

   -f or --force - removes object without question
    
    """
