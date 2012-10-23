import posixpath
import logging
import time

import ccdb
from ccdb import Directory, TypeTable, TypeTableColumn, Variation
from ccdb import AlchemyProvider
import sqlalchemy.exc
from ccdb.cmd import ConsoleUtilBase
from sqlalchemy.orm.exc import NoResultFound

log = logging.getLogger("ccdb.cmd.utils.info")

#ccdbcmd module interface
def create_util_instance():
    log.debug("      registering Info")
    return Info()


#*********************************************************************
#   Class Info - Prints extended information of object by the path   *
#                                                                    *
#*********************************************************************
class Info(ConsoleUtilBase):
    """ Prints extended information of object by the path """
    
    # ccdb utility class descr part 
    #------------------------------
    command = "info"
    name = "Info"
    short_descr = "Prints extended information of object by the path"
    uses_db = True

    #variables for each process

    rawentry = "/"       #object path with possible pattern, like /mole/*
    path = "/"    #parent path
    
    
#----------------------------------------
#   process 
#----------------------------------------  
    def process(self, args):
        log.debug("InfoUtil is gained a control over the process.")
        log.debug("   " + " ".join(args))

        assert self.context != None
        provider = self.context.provider
        isinstance(provider, AlchemyProvider)
        
        #process arguments
        self.rawentry = ""
        self.object_type = "type_table" 
        self.process_arguments(args)
        
        #correct ending /
        self.path = self.context.prepare_path(self.rawentry)
        
        
        if not self.rawentry:
            log.warning("No path is given. Use 'help info' or 'usage info' for getting help.")

        #it is a type table
        if self.object_type == "type_table":
            try:
                self.type_table = provider.get_type_table(self.path)
                self.print_type_table(self.type_table)
            except NoResultFound:
                log.warning("No type table with this path")
                return 1
        
        #it is a directory
        if self.object_type == "directory":
            try:
                parent_dir = provider.get_directory(self.path)
                self.print_directory(parent_dir)
            except KeyError: #TODO change KeyError to NoResultFound or something
                log.warning("No directory with this path")
                return 1
        
        #it is a variation
        if self.object_type == "variation":
            try:
                variation = provider.get_variation(self.rawentry)
                self.print_variation(variation)
            except NoResultFound:
                log.warning("No variation with this name")
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
                
            else:
                #it probably must be a type table path
                self.rawentry = token
                self.object_type = "type_table"
                
                
#----------------------------------------
#   print_directory 
#----------------------------------------   
    def print_directory(self, directory):
        assert isinstance(directory, Directory)
        print " Name      :  " + self.theme.Success +  directory.name
        print " Full path :  " + directory.path
        try:
            print " Created   :  " + directory.created.strftime("%Y-%m-%d %H-%M-%S")
        except:
            pass
        try:
            print " Modified  :  " + directory.modified.strftime("%Y-%m-%d %H-%M-%S")
        except:
            pass
        #comment
        print " Comment: "
        print directory.comment
        print
        
        
#----------------------------------------
#   print_type_table 
#----------------------------------------        
    def print_type_table(self, table):
        #basic values: name rows columns path
        assert isinstance(table, TypeTable)
        print "+------------------------------------------+"
        print "| Type table information                   |"
        print "+------------------------------------------+"
        print " Name       :  " + self.theme.Success +  table.name
        print " Full path  :  " + table.path
        print " Rows       :  " + self.theme.Accent + repr(int(table.rows_count))
        print " Columns    :  " + self.theme.Accent + repr(int(table._columns_count))
        print " Created    :  " + table.created.strftime("%Y-%m-%d %H-%M-%S")
        print " Modified   :  " + table.modified.strftime("%Y-%m-%d %H-%M-%S")
        print " DB Id      :  " + repr(int(table.id))
        print "+------------------------------------------+"
        print "| Columns info                             |"
        print "+------------------------------------------+"
        #columns info 
        print
        print "Columns info "
        print " N.   (type)    : (name)"
        for column in table.columns:
            print " " + repr(int(column.order)).ljust(4)+" " + self.theme.Type + "%-10s"%column.type + self.theme.Reset + ": "+ column.name
           
        print 
        print "+------------------------------------------+"
        #comment
        print "Comment: "
        print table.comment
        print

#----------------------------------------
#   print_variation 
#----------------------------------------        
    def print_variation(self, variation):
        #basic values: name rows columns path
        assert isinstance(variation, Variation)
        print " Name       :  " + variation.name
        print " Created    :  " + variation.created.strftime("%Y-%m-%d %H-%M-%S")
        print " Modified   :  " + variation.modified.strftime("%Y-%m-%d %H-%M-%S")
        print " DB Id      :  " + repr(int(variation.id))
        print " Comment:  "
        print
        print variation.comment
        print

#----------------------------------------
#   print_help 
#----------------------------------------
    def print_help(self):
        "Prints help of the command"
          
        print """Prints extended info about the object
    info <type table path>   - info about type table with given path
    info -d <directory path> - info about directory with given path
    info -v <variation name> - info about variation with given name
    
    """
