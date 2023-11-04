import posixpath
from abc import abstractmethod

from .cli_context import CliContext
from .themes import NoColorTheme


class CliCommandBase(object):
    """base class for a single CCDB CLI command"""

    #context = ConsoleContext()
    uses_db = False
    changes_db = False
    help_util = False
    is_alias = False
    command = ""
    _context = None

    def __init__(self, context):
        assert isinstance(context, CliContext)
        self.context = context

    @property
    def theme(self):
        return self.context.theme

    @theme.setter
    def theme(self, value):
        self.context.theme = value

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

    def read_multiline(self):
        user_input = []
        entry = input("Enter comment text, put 'EOF' on its own line to quit: \n")

        while entry != "EOF":
            user_input.append(entry)
            entry = input("")
        return user_input

