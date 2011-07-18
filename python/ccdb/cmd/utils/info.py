import posixpath
import logging
import time

from ccdb.ccdb_pyllapi import Directory, ConstantsTypeTable, ConstantsTypeColumn, Variation
from ccdb import MySQLProvider
from ccdb.cmd import ConsoleUtilBase
from ccdb.cmd import Theme
from ccdb.cmd import is_verbose, is_debug_verbose

log = logging.getLogger("ccdb.cmd.utils.info")


#----------------------------------------
#   plugin interface realization 
#----------------------------------------
def create_util_instance():
    log.debug("      registring Info")
    return Info()

#*********************************************************************
#   Class Info - Prints extended information of object by the path   *
#                                                                    *
#*********************************************************************
class Info(ConsoleUtilBase):
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
	isinstance(provider, MySQLProvider)
	
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
	    
	    self.type_table = provider.get_type_table(self.path, True)
	    if self.type_table:
		self.print_type_table(self.type_table)
	    else:
		log.warning("No type table with this path")
		return 1
	
	#it is a directory
	if self.object_type == "directory":
	    parent_dir = provider.get_directory(self.path)
	    if(parent_dir):
		self.print_directory(parent_dir)
	    else:
		log.warning("No directory with this path")
		return 1
	
	#it is a variation
	if self.object_type == "variation":
	    variation = provider.get_variation(self.rawentry)
	    if(variation):
		self.print_variation(variation)
	    else:
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
        isinstance(directory, Directory)
        print " Name      :  " + Theme.Success +  directory.name
        print " Full path :  " + directory.full_path
	try:
            print " Created   :  " + time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime(directory.created_time))
        except:
            pass
        try:
	    print " Modified  :  " + time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime(directory.modified_time))
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
	isinstance(table, ConstantsTypeTable)
	print "+------------------------------------------+"
	print "| Type table information                   |"
	print "+------------------------------------------+"
	print " Name       :  " + Theme.Success +  table.name
	print " Full path  :  " + table.full_path
	print " Rows       :  " + Theme.Accent + repr(table.nrows)
	print " Columns    :  " + Theme.Accent + repr(table.ncolumns)
	print " Created    :  " + time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime(table.created_time))
	print " Modified   :  " + time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime(table.modified_time))
	
	print "+------------------------------------------+"
	print "| Columns info                             |"
	print "+------------------------------------------+"
	#columns info 
	print
	print "Columns info "
	print " (type)    : (name)"
	for column in table.columns:
	    isinstance(column, ConstantsTypeColumn)
	    print " " + Theme.Type + "%-10s"%column.column_type + Theme.Reset + ": "+ column.name
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
	print " Created    :  " + time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime(variation.created_time))
	print " Modified   :  " + time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime(variation.modified_time))
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
