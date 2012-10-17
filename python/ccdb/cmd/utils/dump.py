import sys
import posixpath
import logging

from ccdb import AlchemyProvider
from ccdb.cmd import ConsoleUtilBase

log = logging.getLogger("ccdb.cmd.utils.ls")

#ccdbcmd module interface
def create_util_instance():
    log.debug("      registering Dump")
    return Dump()


#*********************************************************************
#   Class List - Dumps datat table to a file                         *
#                                                                    *
#*********************************************************************
class Dump(ConsoleUtilBase):
    """ Dumps datat table to a file """
    
    # ccdb utility class descr part 
    #------------------------------
    command = "dump"
    name = "Dump"
    short_descr = "Dumps data table"
    uses_db = True

    #variables for each process

    def process(self, args):
        log.debug("Dump is gained a control over the process.")
        log.debug("Arguments: " + " ".join(args))

        self.context.process("cat --no-borders --no-header --comments --time" + " ".join(args))


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

