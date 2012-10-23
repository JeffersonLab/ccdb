from ccdb.cmd import ConsoleUtilBase
from ccdb.path_utils import validate_name
import logging

log = logging.getLogger("ccdb.cmd.utils.mkvar")

#ccdbcmd module interface
def create_util_instance():
    log.debug("      registering MakeVariation")
    return MakeVariation()


#*********************************************************************
#   Class MakeVariation - Create variation                           *
#                                                                    *
#*********************************************************************
class MakeVariation(ConsoleUtilBase):
    """ Create variation """
    
    # ccdb utility class descr part 
    #------------------------------
    command = "mkvar"
    name = "MakeVariation"
    short_descr = "Create variation"
    uses_db = True


    def process(self, args):
        log.debug("MakeVariation module gained control")
        log.debug("Arguments: \n " + "     ".join(args))
        
        if not len(args): return

        comment = ""
        raw_str = args[0] #hello dynamic language!

        #try to extract comment from /path/#comment
        if "#" in raw_str:
            var_name = raw_str[:raw_str.index("#")]
            comment = raw_str[raw_str.index("#") + 1:]
        else:
            var_name = raw_str

        #in case there is a space between comments and name

        if len(args)>=2 and str(args[1]).startswith("#"):
            comment = comment + args[1][1:]
            if len(args)>=3:
                comment = comment + " " + " ".join(args[2:])

        if not validate_name(var_name):
            log.warning("Invalid variation name. Only [a-z A-Z 0-9 _] symbols are allowed for variation name")
            return 1

        #try to create directory
        log.debug("  creating variation. Name: {0},  comment: {1}".format(var_name, comment))

        try:
            self.context.provider.create_variation(var_name, comment)
        except Exception as ex:
            log.warning("Failed to create directory. Exception message: {0}".format(ex))

        log.info("Variation " + var_name + self.theme.Success + " created" + self.theme.Reset)


    #----------------------------------------------
    #   print_help - prints help
    #----------------------------------------------
    def print_help(self):
        "prints help to user"

        print """
MakeVariation or mkvar - create variation with specified name

usage:

    mkvar <name> #<comments>

    name        - is a variation name. [a-z A-Z 0-9 _] are allowed symbols
    comments    - are comments...
            """
