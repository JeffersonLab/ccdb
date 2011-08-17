from ccdb.cmd import ConsoleContext
import ccdb.cmd

class ConsoleUtilBase:
    "base class for console utility"
    
    context = ConsoleContext()
    uses_db = False
    changes_db = False
    help_util = False

    def print_help(self):
        "Prints help of the command"
        print "Help is not defined for command " + self.command

    def print_usage(self):
        "Prints usage of the command"
        print "Usage is not defined for command " + self.command

    def print_examples(self):
        "Prints examples of the command usage"
        print "Examples are not defined for command " + self.command

    def __init(self):
        self.description = ""
        self.command = ""
        #self.context = ConsoleContext()
                        
        #context = None
        
    def read_multiline(self):
        user_input = []
        entry = raw_input("Enter comment text, 'EOF' on its own line to quit: \n")
        
        while entry != "EOF":
            user_input.append(entry)
            entry = raw_input("")
        return user_input

