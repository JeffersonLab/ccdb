import os
import logging

import ccdb
from ccdb import TextFileDOM
from ccdb import AlchemyProvider
from ccdb.cmd import ConsoleUtilBase
from ccdb import BraceMessage as LogFmt

log = logging.getLogger("ccdb.cmd.utils.add")


# ccdbcmd module interface
def create_util_instance():
    """
    This function is a module interface

    :return: new AddData util
    :rtype: AddData
    """
    log.debug("      registering AddData")
    return AddData()


# *********************************************************************
#   Class AddData - Add data constants                                *
#                                                                     *
# *********************************************************************
class AddData(ConsoleUtilBase):
    """ Add data constants according given type table"""

    # ccdb utility class descr part 
    # ------------------------------
    command = "add"
    name = "AddData"
    short_descr = "Add data constants"
    uses_db = True

    def __init(self):
        self.reset()

    # ----------------------------------------
    #   process
    # ----------------------------------------
    def reset(self):
        """
        Resets for new command
        :return: None
        """

        # set arguments to default
        self.raw_table_path = ""
        self.table_path = ""
        self.raw_file_path = ""
        self.file_path = ""
        self.run_min = 0
        self.run_max = ccdb.INFINITE_RUN
        if self.context is None:
            self.variation = "default"
        else:
            self.variation = self.context.current_variation
        self.comment = ""
        self.is_namevalue_format = False
        self.no_comments = False
        self.c_comments = False  # file has '//'-style comments
        self.raw_entry = "/"  # object path with possible pattern, like /mole/*
        self.path = "/"  # parent path

    # ----------------------------------------
    #   process
    # ----------------------------------------
    def process(self, args):
        if log.isEnabledFor(logging.DEBUG):
            log.debug(LogFmt("{0}AddData is in charge{0}\\".format(os.linesep)))
            log.debug(LogFmt(" |- arguments : '" + "' '".join(args) + "'"))

        self.reset()

        provider = self.context.provider
        assert isinstance(provider, AlchemyProvider)

        # process arguments
        if not self.process_arguments(args):
            log.debug(LogFmt(" |- process arguments {0}{1}{2}", self.theme.Fail, "failed", self.theme.Reset))
            raise ValueError("Problem parsing arguments")

        # by "" user means default variation
        # self.variation = "default" if not bool(self.variation) else self.variation
        # TODO commented as self.variation is set in self.reset() need to be tested

        # validate what we've got
        if not self.validate():
            log.debug(LogFmt(" |- arguments validation {0}{1}{2}", self.theme.Fail, "failed", self.theme.Reset))
            raise ValueError("Arguments validation failed")

        # correct paths
        self.table_path = self.context.prepare_path(self.raw_table_path)
        self.file_path = self.raw_file_path

        # reading file
        try:
            if not self.is_namevalue_format:
                dom = ccdb.read_ccdb_text_file(self.file_path)
            else:
                dom = ccdb.read_namevalue_text_file(self.file_path, self.c_comments)
        except IOError as error:
            log.warning(LogFmt("Unable to read file '{0}'. The error message is: '{1}'", self.file_path, error))
            raise

        # check what we've got
        assert isinstance(dom, TextFileDOM)
        if not dom.data_is_consistent:
            message = "Inconsistency error. " + dom.inconsistent_reason
            log.warning(message)
            raise ValueError(message=message)

        if len(dom.comment_lines):
            self.comment += "\n".join(dom.comment_lines)

        # >oO debug record
        log.debug(" |- adding constants")
        log.debug(LogFmt(" |- columns: '{0}'  rows: '{1}'  comment lines:  '{2}'  metas: '{3}'",
                         len(dom.rows[0]), len(dom.rows), len(dom.comment_lines), len(dom.metas)))

        try:
            table = provider.get_type_table(self.table_path)
        except Exception as ex:
            if 'No table found by exact path' in ex.message:  # TODO replace with good exception type
                # it is safe to use len(dom.rows[0]) because dom.data_is_consistant checked that
                print(self._get_notable_instruction(self.table_path, len(dom.rows[0]), len(dom.rows)))

        # try to create
        assignment = provider.create_assignment(dom,
                                                self.table_path,
                                                self.run_min,
                                                self.run_max,
                                                self.variation,
                                                self.comment)
        log.info(assignment.request)
        return 0

        # ----------------------------------------

    #   process_arguments
    # ----------------------------------------
    def process_arguments(self, args):

        # parse loop
        i = 0

        while i < len(args):
            token = args[i].strip()
            i += 1
            if token.startswith('-'):
                # it is some command, lets parse what is the command

                # variation
                if token == "-v" or token.startswith("--variation"):
                    if i < len(args):
                        self.variation = args[i]
                        i += 1

                # runrange
                if token == "-r" or token == "--runrange":
                    result = self.context.parse_run_range(args[i])
                    i += 1
                    if not result:
                        log.warning("Run range should be in form of: min-max, or min- , or -max")
                        return False

                    # there is a result
                    (self.run_min, self.run_max, run_min_set, run_max_set) = result

                    # check how the bounds were set
                    if not run_min_set:
                        log.warning("Min run bound was set as 0 by default. ")
                    if not run_max_set:
                        log.warning("Max run bound was set as INFINITE_RUN by default. ")

                # file
                if token == "-f" or token == "--file":
                    self.raw_entry = args[i]
                    self.object_type = "directory"
                    i += 1

                # skip comments 'no-comments' value
                if token == "-n" or token == "--no-comments":
                    self.no_comments = True

                # name-value file mode
                if token == "--name-value":
                    self.is_namevalue_format = True

                # c style comments
                if token == "--c-comments":
                    self.c_comments = True

            else:
                if token.startswith("#"):
                    # everething next are comments
                    self.comment += " ".join(args[i - 1:])
                    self.comment.strip()
                    self.comment = self.comment[1:]
                    break  # break the loop since everything further are comments

                # it probably must be a type table path
                if self.raw_table_path == "":
                    self.raw_table_path = token
                elif self.raw_file_path == "":
                    self.raw_file_path = token

        return True

        # ----------------------------------------

    #   validate
    # ----------------------------------------
    def validate(self):
        if not self.raw_file_path or not self.raw_table_path:
            return False
        return True

        # ----------------------------------------

    #   print instruction if no table found
    # ----------------------------------------
    def _get_notable_instruction(self, path, cols, rows):
        """print instruction if no table found"""
        msg = """
There is no table with path '{0}' found in the database.
A table should be created prior adding the constants (see help mktbl)
The command to create the table for the data is:

mktbl {0} -c {1} -r {2} #<Description and comments here>
""".format(path, cols, rows)
        return msg

    # ----------------------------------------
    #   print_help
    # ----------------------------------------
    def print_help(self):
        """Prints help of the command"""

        print ("""Add data constants according given type table
    add <type table path>  -v <variation>  -r <run_min>-<run_max>  file_to_import

Required parameters:
    <type table path> - must be /absolute/path/ in command line mode
                        might be also relative/path in interactive mode 

    <variation> - variation name 
    
    <run_min>-<run_max> - run range. 
        if one inputs '<run_min>-' this means <run_min>-<infinit run>
        if one inputs '-<run_max>' this means <0>-<run_max> 
        if one omits runrange at all. The data will be put as
    
   file_to_import - file to import. It should be ccdb file format (see documentation or file format section) 
                    if file format is column of names and column of values add --name-value flag

Additional flags:
    
          --name-value  - indicates that the input file is in name-value format (column of names and column of values)
    -n or --no-comments - do not add all "#..." comments that is found in file to ccdb database
          --c-comments  - for files that contains '//' - C style comments. The add replaces simply // to #. 
    
    """)
