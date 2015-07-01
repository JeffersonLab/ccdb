from __future__ import print_function

from .console_context import ConsoleContext
from .themes import NoColorTheme

class ConsoleUtilBase(object):
    """base class for console utility"""

    #context = ConsoleContext()
    uses_db = False
    changes_db = False
    help_util = False
    command = ""

    @property
    def context(self):
        """:return: context object for current utility
           :rtype: ConsoleContext
        """
        return self._context

    @context.setter
    def context(self, value):
        assert isinstance(value, ConsoleContext)
        self._context = value

    def print_help(self):
        """Prints help of the command"""

        print("Help is not defined for command " + self.command)

    def print_usage(self):
        """Prints usage of the command"""
        print("@brief Usage is not defined for command " + self.command)

    def print_examples(self):
        """Prints examples of the command usage"""
        print("Examples are not defined for command " + self.command)

    def __init__(self):
        self._context = None
        self.theme = NoColorTheme()

    def read_multiline(self):
        user_input = []
        entry = raw_input("Enter comment text, put 'EOF' on its own line to quit: \n")

        while entry != "EOF":
            user_input.append(entry)
            entry = raw_input("")
        return user_input

