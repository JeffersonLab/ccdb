from ccdb.cmd import CliCommandBase
import logging

log = logging.getLogger("ccdb.cmd.commands.help")


# ********************************************************************
#   Class HelpUtil - Prints help for each util                       *
# ********************************************************************
class HelpUtil(CliCommandBase):
    """ Prints help for each util """
    
    # ccdb utility class descr part 
    # ------------------------------
    command = "help"
    name = "Help"
    short_descr = "Prints help for each util"
    help_util = True


    # ----------------------------------------
    #   print_help
    # ----------------------------------------
    def print_help(self):
        print(self.help_text)

        if self.context:
            print("Available commands:")
            print("   %-10s %-15s %s:" % ("(command)", "(name)", "(description)"))
            print("   " + "\n  ".join(
                ["%-10s %-15s %s" % (f"'{command}'", util.name, util.short_descr)
                    for command, util
                    in self.context.commands.items()
                    if not util.help_util]))
        print(self.flags_text)
        print(self.enveron_text)

    # ----------------------------------------
    #   process
    # ----------------------------------------
    def execute(self, args):
        if self.context:
            commands = list(self.context.commands.keys())
            if args:
                if args[0] in commands:
                    self.context.commands[args[0]].print_help()
                else:
                    msg = "Command {} is not found. Please run 'ccdb help' for the list of commands".format(args[0])
                    raise ModuleNotFoundError(msg)
            else:
                self.print_help()
        # The CLI treats a None result as failure (exit code 1), so report success
        return True
    
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

    -c <connection string>  or  --connection <connection string>
                         Set connection string to server

    --mysql-pwd          Ask for MySQL password before connecting to database
    
    --version            Print ccdb version (and quit)

    Debug helping flags:
    
    -s or --silent       Do not display any text. Will not work in interactive mode.
    --debug              Show verbose debug output          
    --errors-silent      (default) Print errors and return non 0 code but don't raise python exceptions (*)
    --errors-raise       Throws all python exceptions it caught and hard crashes (*)
    --raise              (deprecated) same as --errors-raise
    --no-color           No colored output
    
    * - By default CCDB throws all python exceptions in non interactive mode. But only print in console and continue 
    in interactive mode (I.e. works as --errors-raise in non interactive and --errors-silent in interactive (-i) mode)
    If --errors-silent is given in non interactive mode, process just prints exceptions and returns non 0 exit code 
    
          

                         """
    enveron_text = """     
Environment:
    CCDB_USER       : user name. Should be set to perform any update operation
    CCDB_CONNECTION : might be set, containing a connection string to be automatically loaded


Connection string examples:
    MySql  : mysql://ccdb_user@localhost/ccdb
    SQLite : sqlite:////full/path/to/ccdb.sqlite
             (create one with: ccdb -c sqlite:////full/path/to/ccdb.sqlite db init --init-i-am-sure)
             (notice 3 slashes)
    """
    
    





