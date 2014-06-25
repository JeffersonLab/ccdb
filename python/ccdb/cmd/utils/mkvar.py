from ccdb.cmd import ConsoleUtilBase, UtilityArgumentParser
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

        if not len(args):
            return

        #find #comment
        comment = ""
        for i in range(len(args)):
            arg = args[i]
            if arg.startswith("#"):
                comment = (" ".join(args[i:]))[1:]  # [1:] to remove #
                args = args[:i]
                break

        #utility argument parser is argparse which raises errors instead of exiting app
        parser = UtilityArgumentParser()
        parser.add_argument("name", default="")
        parser.add_argument("-p", "--parent", default="")
        result = parser.parse_args(args)

        parser.add_argument("--verbose", help="increase output verbosity",
                            action="store_true")

        #in case there is a space between comments and name

        if not validate_name(result.name):
            raise ValueError("Invalid variation name. Only [a-z A-Z 0-9 _] symbols are allowed for variation name")

        #try to create directory
        log.debug("  creating variation. Name: {0},  comment: {1}".format(result.name, comment))

        self.context.provider.create_variation(result.name, comment, result.parent)

        log.info("Variation " + result.name + self.theme.Success + " created" + self.theme.Reset)

    #----------------------------------------------
    #   print_help - prints help
    #----------------------------------------------
    def print_help(self):
        """prints help to user"""

        print """
MakeVariation or mkvar - create variation with specified name

usage:

    mkvar <name> #<comments>
    mkvar <name> -p <parent> #<comments>

    name           - is a variation name. [a-z A-Z 0-9 _] are allowed symbols
    comments       - are comments... don't forget space before #
    -p or --parent - name of parent variation. If no name provided, "default" variation is the parent
            """
