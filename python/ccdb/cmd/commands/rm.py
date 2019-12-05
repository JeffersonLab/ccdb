import logging
import os
from ccdb import AlchemyProvider, TypeTable, Directory, Variation
from ccdb.cmd import CliCommandBase
from sqlalchemy.orm.exc import NoResultFound

from ccdb.errors import ObjectIsNotFoundInDbError

log = logging.getLogger("ccdb.cmd.commands.rm")

# ********************************************************************
#   Class Info - Prints extended information of object by the path   *
# ********************************************************************
class Remove(CliCommandBase):
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
    def execute(self, args):
        log.debug("{0}Remove is gained a control{0}\\".format(os.linesep))
        log.debug(" |- arguments: " + " ".join(["'"+arg+"'" for arg in args]))

        assert self.context is not None
        provider = self.context.provider
        isinstance(provider, AlchemyProvider)
        
        # process arguments
        raw_entry, object_type, ask_confirm = self.process_arguments(args)
        log.debug(" |- object_type: '{0}'".format(object_type))
        log.debug(" |- ask confirm: '{0}'".format(ask_confirm))
        log.debug(" |- raw entry:   '{0}'".format(raw_entry))

        # correct ending /
        path = self.context.prepare_path(raw_entry)
                
        if not raw_entry:
            log.warning("No path is given. Use 'help info' or 'usage info' for getting help.")

        self.print_warning()
        
        # ask confirmation
        if ask_confirm:
            result = eval(input("To confirm delete type 'yes': "))
            if result != 'yes':
                return None

        # it is a type table
        if object_type == "type_table":
            type_table = provider.get_type_table(path)
            provider.delete_type_table(type_table)
            return type_table
        
        # it is a directory
        if object_type == "directory":
            directory = provider.get_directory(path)
            provider.delete_directory(directory)
            return directory
        
        # it is a variation
        if object_type == "variation":
            variation = provider.get_variation(raw_entry)
            provider.delete_variation(variation)
            return variation

        # it is assignment
        if object_type == "assignment":
            assignment = provider.get_assignment_by_id(int(raw_entry))
            provider.delete_assignment(assignment)
            return assignment

        # everything is fine!
        return 0
            
    def process_arguments(self, args):
        raw_entry = ""
        object_type = "type_table"
        ask_confirm = True
        # parse loop
        i = 0
        while i < len(args):
            token = args[i].strip()
            i += 1
            if token.startswith('-'):
                # it is some command, lets parse what is the command

                # variation
                if token == "-v" or token.startswith("--variation"):
                    if i < len(args):
                        raw_entry = args[i]
                        object_type = "variation"
                        i += 1
                        
                # directory
                if token == "-d" or token == "--directory":
                    raw_entry = args[i]
                    object_type = "directory"
                    i += 1

                if token == "-a" or token == "--assignment":
                    raw_entry = args[i]
                    object_type = "assignment"
                    i += 1

                if token == "-f" or token == "--force":
                    ask_confirm = False
                
            else:
                # it probably must be a type table path
                raw_entry = token
                object_type = "type_table"

        return raw_entry, object_type, ask_confirm
                
    def print_warning(self):
        """print warning"""
        
        print(""" 
                    (!) WARNING (!) 
          CCDB is no-delete storage by design!

It is assumed by CCDB design that object names or paths are used in user code. 
Deleting or renaming type table, directory or variation could break the user code 
which using this names.

Deleting a table and recreating with different signature could 
lead to even more severe hard-to-diagnose errors.
""")
        
    def print_help(self):
        """Prints help of the command"""
          
        print("""Removes type table, directory or variation
    rm <type table path>   - removes type table with given path
    rm -d <directory path> - removes directory with given path
    rm -v <variation name> - removes variation with given name
    rm -a <assignment id>  - Assignment db id from 'vers' command*

 Flags:

   -f or --force - removes object without question
    
    """)
