import posixpath
import logging
import time

import ccdb
from ccdb.ccdb_pyllapi import Directory, ConstantsTypeTable, ConstantsTypeColumn, Variation
from ccdb import MySQLProvider, TextFileDOM
from ccdb.cmd import ConsoleUtilBase
from ccdb.cmd import Theme
from ccdb.cmd import is_verbose, is_debug_verbose

log = logging.getLogger("ccdb.cmd.utils.add")

def create_util_instance():
    log.debug("      registring AddData")
    return AddData()

class AddData(ConsoleUtilBase):
    command = "add"
    name = "AddData"
    short_descr = "Add data constants according given type table"
    uses_db = True

    #variables for each process

    rawentry = "/"   #object path with possible pattern, like /mole/*
    path = "/"       #parent path
    
#----------------------------------------
#   process 
#----------------------------------------  
    def process(self, args):
        log.debug("AddData is gained a control over the process.")
        log.debug("   " + " ".join(args))

        assert self.context != None
        provider = self.context.provider
	isinstance(provider, MySQLProvider)
	
	#process arguments
	self.raw_table_path = ""
	self.table_path = ""
	self.raw_file_path = ""
	self.file_path = ""
	self.run_min = 0
	self.run_max = ccdb.INFINITE_RUN
	self.variation = ""
	self.comment = ""
        if not self.process_arguments(args):
	    return 1
	
	if self.variation == "":
	    self.variation = "default"
	    
	if not self.validate():
	    return 1
	
	#correct path
        self.table_path = self.context.prepare_path(self.raw_table_path)
	self.file_path = self.raw_file_path
	
	#reading file
	dom = None
	try:
	    dom = ccdb.read_ccdb_text_file(self.file_path)
	except IOError as error:
	    log.warning("Unable to read file %s. The error message is: \n %s"%(self.file_path, error.message))
	    return 1	
	assert isinstance(dom, TextFileDOM)	
	if not dom.data_is_consistant:
	    log.warning("Number of columns in rows are inconsisnsant in file")
	    return 1
	
	if len(dom.comment_lines):
	    self.comment += "\n" + "\n".join(dom.comment_lines)
	    
	#try to create
	result = provider.create_assignment(dom, self.table_path, self.run_min, self.run_max, self.variation, self.comment)
	
	if not result: 
	    log.warn("Constants adding " +Theme.Fail+" error "+Theme.Reset)
	    return provider.get_last_error()
	
	log.info("Constants added " +Theme.Success+"successfully"+Theme.Reset)
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
			self.variation = args[i]
			i+=1
						
		#runrange
		if token == "-r" or token == "--runrange":
		    result = self.context.parse_run_range(args[i])
		    i+=1
		    if not result:
			log.warning("Run range should be in form of: min-max, or min- , or -max")
			return False
		    
		    #there is a result
		    (self.run_min,  self.run_max, run_min_set, run_max_set) = result
		    
		    #check how the bounds were set
		    if not run_min_set:
			log.warning("Min run bound was set as 0 by default")
		    if not run_max_set:
			log.warning("Max run bound was set as INFINITE_RUN by default")
		    
		
		#runrange
		if token == "-f" or token == "--file":
		    self.rawentry = args[i]
		    self.object_type = "directory"
		    i+=1
		
            else:
		if token.startswith("#"):
		    #everething next are comments
		    self.comment += " ".join( args[i-1:])
		    self.comment.strip()
		    self.comment = self.comment[1:]
		    break #break the loop since everething next are comment
		
		#it probably must be a type table path
		if self.raw_table_path == "":
		    self.raw_table_path = token
		elif self.raw_file_path == "":
		    self.raw_file_path = token
	
	return True
    
    
#----------------------------------------
#   validate 
#----------------------------------------  
    def validate(self):
	if not self.raw_file_path : return False
	if not self.raw_table_path: return False
	return True

    
#----------------------------------------
#   print_help 
#----------------------------------------
    def print_help(self):
	"Prints help of the command"
	  
        print """Add data constants according given type table
	add <type table path>  -v <variation>  -r <run_min>-<run_max>  file_to_import
    
    """
