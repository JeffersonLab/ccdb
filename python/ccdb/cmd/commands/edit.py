
import logging
import os

import ccdb
import ccdb.path_utils
from ccdb.cmd import CliCommandBase, UtilityArgumentParser
from ccdb import AlchemyProvider
from ccdb import BraceMessage as LogFmt


# logger must be set to ccdb.cmd.utils.<utility command>
log = logging.getLogger("ccdb.cmd.commands.edit")


# ********************************************************************
#   Class Edit- Change a value in a table                            *
# ********************************************************************
class Edit(CliCommandBase):
    """Edit a value in a table"""

    # ccdb utility class descr part
    # ------------------------------
    command = "edit"
    name = "Edit"
    short_descr = "Edit the comment of a version"
    uses_db = True

    def __init__(self, context):
        super().__init__(context)
        self.raw_entry = "/"  # object path with possible pattern, like /mole/*

    # ----------------------------------------
    #   cleanup
    # ----------------------------------------
    def __cleanup(self):
        """Call this function in the beginning of command processing to prepare variables for new command"""
        self.raw_entry = "/"

    #
    #   process
    # ----------------------------------------
    def execute(self, args):
        """This is an entry point for each time the command is called"""

        if log.isEnabledFor(logging.DEBUG):
            log.debug(LogFmt("{0}Edit is in charge{0}\\".format(os.linesep)))
            log.debug(LogFmt(" |- arguments : '" + "' '".join(args) + "'"))

        # prepare variables for the new command
        self.__cleanup()

        # get provider class which has functions for all CCDB database operation
        assert self.context
        provider = self.context.provider
        assert isinstance(provider, AlchemyProvider)

        # process arguments
        parsed_args = self.process_arguments(args)

        # the comment of a version (issue #56)
        if parsed_args.comment is not None:
            if not parsed_args.assignment:
                raise ValueError("--comment needs the version: edit -a <assignment id or request> --comment \"text\"")
            assignment = self._get_assignment(parsed_args.assignment)
            previous = assignment.comment or ""
            provider.set_assignment_comment(assignment, parsed_args.comment)
            log.info(LogFmt("Comment of assignment {0} ('{1}') changed", assignment.id, assignment.request))
            log.info(LogFmt("  was: {0}", previous))
            log.info(LogFmt("  now: {0}", assignment.comment))
            return True

        if not parsed_args.raw_path:
            raise ValueError("edit needs a table path, or -a <assignment> --comment \"text\"")

        if not self.validate(parsed_args):
            return False  # False means the command failed

        path = self.context.prepare_path(parsed_args.raw_path)  # add current path to user input

        # try avoid print() and use log to print data
        log.info(LogFmt("{0}raw_path{1} : {2}", self.theme.Accent, self.theme.Reset, parsed_args.raw_path))
        log.info(LogFmt("{0}path{1}     : {2}", self.theme.Accent, self.theme.Reset, path))
        log.info(LogFmt("{0}variation{1}: {2}", self.theme.Accent, self.theme.Reset, parsed_args.variation))
        log.info(LogFmt("{0}run{1}      : {2}", self.theme.Accent, self.theme.Reset, parsed_args.run))

        # Truthy return means the command succeeded
        return True

    # ----------------------------------------
    #   process_arguments
    # ----------------------------------------
    def process_arguments(self, args):
        # solo arguments

        # utility argument parser is argparse which raises errors instead of exiting app
        parser = UtilityArgumentParser()
        parser.add_argument("raw_path", nargs="?", default="")
        parser.add_argument("-c", "--column", default="")
        parser.add_argument("-r", "--row", default="")
        parser.add_argument("-v", "--value")
        parser.add_argument("-a", "--assignment", default="")
        parser.add_argument("--comment")
        return parser.parse_args(args)

    def _get_assignment(self, text):
        """An assignment by its database id or by a request string"""
        provider = self.context.provider
        if text.isdigit():
            return provider.get_assignment_by_id(int(text))
        return provider.get_assignment_by_request(text)

    # ----------------------------------------
    #   validate
    # ----------------------------------------
    def validate(self, parsed_args):
        if not ccdb.path_utils.validate_name(parsed_args.raw_path):
            log.error("The wrong path is given")
            return False

        return True

    # ----------------------------------------
    #   print_help
    # ----------------------------------------
    def print_help(self):
        """Prints help for the command"""

        print("""Edits the comment of a version (an assignment)
    edit -a <assignment id or request> --comment "new comment"

    The data, run range, variation and time of the version stay. The log record of the change keeps the previous
    comment. The id is the first column of 'vers'; a request such as /test/test_vars/test_table:100 works too.

Example:
    > edit -a 4213 --comment "Undo the BCAL cable swap for future runs"
    > edit -a /test/test_vars/test_table:100 --comment ""      # clears the comment

Editing values (not implemented yet):
        -c or --column Columns of the wrong data
        -r or --row Row of the wrong data
        -v or --value Correct value to replace wrong data

    """)
