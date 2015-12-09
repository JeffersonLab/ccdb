from ccdb.cmd import ConsoleUtilBase
import logging

log = logging.getLogger("ccdb.cmd.utils.help")

# ccdb cmd module interface
def create_util_instance():
    log.debug("      registering HelpUtil")
    return HelpUtil()


#*********************************************************************
#   Class HelpUtil - Prints help for each util                       *
#                                                                    *
#*********************************************************************
class HelpUtil(ConsoleUtilBase):
    """ Prints help for each util """
    
    # ccdb utility class descr part 
    #------------------------------
    command = "help"
    name = "Help"
    short_descr = "Prints help for each util"
    help_util = True

    #----------------------------------------
    #   print_help
    #----------------------------------------
    def print_help(self):
        print self.help_text

        if self.context:
            print ("Available commands:")
            print ("   %-10s %-15s %s:"%("(command)", "(name)", "(description)"))
            print ("   " + "\n  ".join(
                ["%-10s %-15s %s" % (command, util.name, util.short_descr) 
                for command, util 
                in self.context.utils.items()
                if not util.help_util]))
        print self.flags_text
        print self.enveron_text


    #----------------------------------------
    #   process
    #----------------------------------------
    def process(self, args):
        if self.context:
            commands = self.context.utils.keys()
            if len(args)>0:
                if args[0] in commands:
                    self.context.utils[args[0]].print_help()
                else:
                    print ("Command %s not found. Available commands are: "%args[0])
            else:
                self.print_help()
    
    help_text = """
Calibration Constants Data Base (CCDB) command line tools.
Print "ccdb -i" to start in interactive mode
Usage:
    ccdb <general arguments> command <command arguments>

    print help <command> to see help for the command
    print usage <command> to see usage for the command

    """
    flags_text = """

Flags:
    -i or --interactive  Starts program in interactive mode. TRY IT(!)

    -s or --silent       Do not display any text. Will not work in interactive mode.
          --debug        Show verbose debug output
          --raise        Process throws all exceptions it caught
          --no-color     No colored output
    -c <connection string>  or  --connection <connection string>
                         Set connection string to server

    --mysql-pwd          Ask for MySQL password before connecting to database
                         """
    enveron_text = """     
Environment:
    CCDB_USER       : user name. Should be set to perform any update operation
    CCDB_CONNECTION : might be set, containing a connection string to be automatically loaded


Connection string examples:
    MySql  : mysql://ccdb_user@localhost/ccdb
    SQLite : sqlite:///$CCDB_HOME/sql/ccdb.sqlite
             (notice 3 slashes)
    """
    
    





