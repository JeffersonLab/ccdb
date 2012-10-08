from ccdb.cmd import ConsoleUtilBase
from ccdb.cmd.Theme import Theme
from ccdb.cmd import is_verbose, is_debug_verbose
from ccdb import Directory, AlchemyProvider, TypeTable
import posixpath
import logging

import posixpath

log = logging.getLogger("ccdb.cmd.utils.mkdir")

#ccdbcmd module interface
def create_util_instance():
    if is_debug_verbose(): print "      registring MakeDirectory"
    return MakeDirectory()


#*********************************************************************
#   Class MakeDirectory - Create directory                           *
#                                                                    *
#*********************************************************************
class MakeDirectory(ConsoleUtilBase):
    """ Create directory """
    
    # ccdb utility class descr part 
    #------------------------------
    command = "mkdir"
    name = "MakeDirectory"
    short_descr = "Create directory"
    uses_db = True

    def process(self, args):
        if is_debug_verbose():
            log.debug("MakeDirectory module gained control")
            log.debug("Arguments: " + " ".join(args))
            print
            print args
        
        if not len(args): return 
                
        path = ""
        comment = "" 
        raw_str=""
        raw_str = args[0] #hello dynamic language!
        
        #in case there is a space between comments and name
        if len(args)>=2 and args[1].starts_with("#"):
            comment = args[1]
        
        #try to extract comment from /path/#comment 
        if "#" in raw_str:
            path = raw_str[:raw_str.index("#")]
            comment = raw_str[raw_str.index("#") + 1:]
        else:
            path = raw_str
            
        #prepare path
        path = self.context.prepare_path(path)
        
        #where is name and parent_path?
        (parent_path, name) = posixpath.split(path)
        
        #try to create directory
        if is_debug_verbose():
            print "   creating directory. Name: ", name, " parent path: ", parent_path, " comment: ", comment

        try:
            self.context.provider.create_directory(name, parent_path, comment)
        except Exception as ex:
            log.warning("Failed to create directory. Exception message: {0}".format(ex))
        else: print "Directory " + name + Theme.Success + " created" + Theme.Reset
        
