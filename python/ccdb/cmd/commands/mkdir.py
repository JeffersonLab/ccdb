from ccdb.cmd import ConsoleUtilBase
import posixpath
import logging
import os
from ccdb import BraceMessage as LogFmt

log = logging.getLogger("ccdb.cmd.utils.mkdir")


#ccdbcmd module interface
def create_util_instance():
    """
    This function is a module interface

    :return: new MakeDirectory utility
    :rtype: MakeDirectory
    """
    log.debug("      registering MakeDirectory")
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
        if log.isEnabledFor(logging.DEBUG):
            log.debug(LogFmt("{0}MakeDirectory is in charge{0}\\".format(os.linesep)))
            log.debug(LogFmt(" |- arguments : '" + "' '".join(args)+"'"))

        
        if not len(args):
            return

        comment = ""
        raw_str = args[0]

        #in case there is a space between comments and name
        if len(args) >= 2 and args[1].startswith("#"):
            comment = args[1][1:]
            if len(args) >= 3:
                comment = comment + " " + " ".join(args[2:])
        
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
        log.debug(" |- creating directory. Name: {0}, parent path: {1},  comment: {2}".format(name,parent_path,comment))

        try:
            self.context.provider.create_directory(name, parent_path, comment)
            log.info("Directory " + name + self.theme.Success + " created" + self.theme.Reset)
        except Exception as ex:
            log.warning(self.theme.Fail+"Failed"+self.theme.Reset+" to create directory. Exception message: {0}".format(ex))
            raise


        
