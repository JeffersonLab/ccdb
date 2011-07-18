from ccdb.cmd import ConsoleUtilBase
from ccdb.cmd.Theme import Theme
from ccdb.cmd import is_verbose, is_debug_verbose

def create_util_instance():
    if is_debug_verbose(): print "      registring HelpUtil"
    return HelpUtil()

class HelpUtil(ConsoleUtilBase):
    command = "help"
    name = "Help"
    short_descr = "Prints help for each util"
    help_util = True
    
    def print_help(self):
        print self.help_text

        if self.context:
            print "Available commands:"
            print "  %-10s %-15s %s:"%("(command)", "(name)", "(description)")
            print "  " + "\n  ".join(
                ["%-10s %-15s %s" % (command, util.name, util.short_descr) 
                for command, util 
                in self.context.utils.items() 
                if not util.help_util])
        print self.flags_text
        print self.enveron_text


    # ---- end of print_help() ----


    def process(self, args):
        if self.context:
            commands = self.context.utils.keys()
            if len(args)>0:
                if args[0] in commands:
                    self.context.utils[args[0]].print_help()
                else:
                    print "Command %s not found. Available commands are: "%args[0]
            else:
                self.print_help()
    
    help_text = """
Callibration Constants Data Base (CCDB) console tools.
Print "ccdbcmd -I" to start in interactive mode
Usage:
    ccdb <general arguments> command <command arguments>

    print help <command> to see help for the command
    print usage <command> to see usage for the command
    print example <command> to see examples for command
    print howto add constants to get instruction
    print howto - to het all available howtos"""
    flags_text = """

Flags:
    -d or --debug        Show verbose debug output
    -s or --silent       Do not display any text. Will not work in interactive mode. 
    -I or --interactive  Starts programm in interactive mode.
          --no-color     No colored output
    -c <connection string>  or  --connection <connection string>
                         Set connection string to server"""
    enveron_text = """     
Environment:
    CCDB_USER       : should be set to perform any update operation 
    CCDB_CONNECTION : might be set, containing a connection string to be automatically loaded"""
    
    





