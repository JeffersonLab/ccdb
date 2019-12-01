from abc import abstractmethod

from .themes import NoColorTheme


class CliCommandBase(object):
    """base class for a single CCDB CLI command"""

    #context = ConsoleContext()
    uses_db = False
    changes_db = False
    help_util = False
    command = ""
    _context = None

    @property
    def context(self):
        """:return: context object for current utility
           :rtype: ConsoleContext
        """
        return self._context

    @context.setter
    def context(self, value):
        self._context = value

    @abstractmethod
    def execute(self, args):
        """Processes the command
        :parameter args: [] - a List of arguments
        """
        pass


    def print_help(self):
        """Prints help of the command"""

        print(("Help is not defined for command " + self.command))

    def print_usage(self):
        """Prints usage of the command"""
        print(("@brief Usage is not defined for command " + self.command))

    def print_examples(self):
        """Prints examples of the command usage"""
        print(("Examples are not defined for command " + self.command))

    def __init__(self):
        self._context = None
        self.theme = NoColorTheme()

    def read_multiline(self):
        user_input = []
        entry = eval(input("Enter comment text, put 'EOF' on its own line to quit: \n"))

        while entry != "EOF":
            user_input.append(entry)
            entry = eval(input(""))
        return user_input

