import sys
import posixpath
import logging

from ccdb.ccdb_pyllapi import Directory, ConstantsTypeTable
from ccdb import MySQLProvider
from ccdb.cmd import ConsoleUtilBase
from ccdb.cmd import Theme
from ccdb.cmd import is_verbose, is_debug_verbose

log = logging.getLogger("ccdb.cmd.utils.ls")

def create_util_instance():
    log.debug("      registring Dump")
    return Dump()

class Dump(ConsoleUtilBase):
    command = "dump"
    name = "Dump"
    short_descr = "Dumps datat table to a file"
    uses_db = True

    #variables for each process

    rawentry = "/"       #object path with possible pattern, like /mole/*
    parent_path = "/"    #parent path
    parent_dir = None    # @type parent_dir DDirectory
    pattern = ""         #pattern on the end of parent path like file?*

    def process(self, args):
        log.debug("Dump is gained a control over the process.")
        log.debug("Arguments: " + " ".join(args))
        
        assert self.context != None
        provider = self.context.provider;
        assert isinstance(provider, MySQLProvider)
        
        print "Dump is not implemented now"
        
       


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
        print "Dumps datat table to a file"

