import sys
import posixpath
import logging

from ccdb.ccdb_pyllapi import Directory, ConstantsTypeTable
from ccdb import MySQLProvider
from ccdb.cmd import ConsoleUtilBase
from ccdb.cmd import Theme
from ccdb.cmd import is_verbose, is_debug_verbose

log = logging.getLogger("ccdb.cmd.utils.ls")

#ccdbcmd module interface
def create_util_instance():
    log.debug("      registring ListUtil")
    return List()

#*********************************************************************
#   Class List - List objects in a given directory                   *
#                                                                    *
#*********************************************************************
class List(ConsoleUtilBase):
    """ List objects in a given directory """
    
    # ccdb utility class descr part 
    #------------------------------
    command = "ls"
    name = "List"
    short_descr = "List objects in a given directory"
    uses_db = True

    #variables for each process

    rawentry = "/"       #object path with possible pattern, like /mole/*
    parent_path = "/"    #parent path
    parent_dir = None    # @type parent_dir DDirectory
    pattern = ""         #pattern on the end of parent path like file?*

    def process(self, args):
        log.debug("ListUtil is gained a control over the process.")
        log.debug("Arguments: " + " ".join(args))
        
        assert self.context != None
        provider = self.context.provider;
        assert isinstance(provider, MySQLProvider)
        
        # @type provider DMySQLDataProvider
        provider = self.context.provider

        #PARSE ARGUMENTS
        #-------------------------------
        if "--dump-tree" in args:
            self.parent_dir = provider.get_root_directory()
            self.print_directory_tree(self.parent_dir, False, 0)
            return

        if "--dump" in args:
            self.parent_dir = provider.get_root_directory()
            self.print_directory_tree(self.parent_dir, True, 0)
            return


        if len(args) > 0:
            self.rawentry = args[0]
        else:
            self.rawentry = self.context.current_path

        #PREPARE DIRS
        #---------------------------

        #correct ending /
        if self.rawentry.endswith("/"):
            self.rawentry = self.rawentry[:-1]

        #local or absolute path?
        if not self.rawentry.startswith("/"):
            self.rawentry = posixpath.join(self.context.current_path , self.rawentry)

        #normalize
        self.rawentry = posixpath.normpath(self.rawentry)
        
        #SEARCH LOGIC
        #---------------------------

        #brute assumption that user has entered a simple dir path
        self.parent_dir = provider.get_directory(self.rawentry)
        self.parent_path = self.rawentry
        self.pattern = ""
        self.parent_dir

        if not self.parent_dir:
            #we have not find the directory by brute rawentry.
            #but maybe it is just /path/plus*some*pattern
            (head, tale) = posixpath.split(self.rawentry)
            self.parent_path = head
            self.pattern = tale
            
            if(is_debug_verbose()):
                print "new path: "
                print "   ", self.parent_path
                if len(self.pattern): print "pattern: ", self.pattern
            #try to find such dir once more
            self.parent_dir = provider.get_directory(self.parent_path)

        #found a directory
        if self.parent_dir:
            assert isinstance(self.parent_dir, Directory)
            assert isinstance(self.context.provider, MySQLProvider)

            if(is_debug_verbose()):
                print "full path: \n   ", self.parent_dir.full_path
                if len(self.pattern): print "pattern: ", self.pattern
            
            #part 1 directories for this path
            subdirs = []
            if self.pattern == "":
                subdirs = self.parent_dir.subdirs
            else:
                subdirs = self.context.provider.search_directories(self.pattern, self.parent_path)
           
            for subdir in subdirs:
                print Theme.Directories + subdir.name + "    "
            
            #part 2 is tables for this path
            tables = []
            if self.pattern == "":
                tables = self.context.provider.get_type_tables(self.parent_dir)
            else:
                tables = self.context.provider.search_type_tables(self.pattern, self.parent_path)
                        
            for table in tables:
                print table.name
            print
        else:
            print "Can't find the directory"


    def print_directory_tree(self, directory, printFullPath, level):
        """prints a full tree of directories
            This is recursive function"""

        #print this directory
        if not printFullPath:
            print "".join(["   " for i in range(0, level)]) + directory.name
        else:
            print directory.full_path

        #print subdirectories recursively
        subDirs = directory.subdirs
        if len(subDirs)>0:
            for subDir in subDirs:
                self.print_directory_tree(subDir, printFullPath, level+1)

    def print_help(self):
        "Prints help of the command"
        print "Displays directories and tables for current directory"

