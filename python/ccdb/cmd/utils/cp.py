
import logging
import os

import ccdb
import ccdb.path_utils
from ccdb.cmd import ConsoleUtilBase, UtilityArgumentParser
from ccdb import AlchemyProvider
from ccdb import BraceMessage as LogFmt

#logger must be set to ccdb.cmd.utils.<utility command>
from ccdb.path_utils import ParseRequestResult, parse_request
from sqlalchemy.orm.exc import NoResultFound

log = logging.getLogger("ccdb.cmd.utils.cp")
#ccdbcmd module interface
def create_util_instance():
    log.debug("      registering Copy")
    return Copy()


#*********************************************************************
#   Class Copy - Copies an assignment to a new dataset               *
#                                                                    *
#*********************************************************************
class Copy(ConsoleUtilBase):
    """Copies an assignment to a new set of data"""
    
    command = "cp"
    name = "Copy"
    short_descr = "Copy assignment"
    uses_db = True

    def __init__(self):
        super(Copy, self).__init__()
        self.raw_entry = "/"         # object path with possible pattern, like /mole/*

    def __cleanup(self):
        """Call this function in the beginning of command processing to prepare variables for new command"""
        self.raw_entry = "/"

    def process(self, args):
        """This is an entry point for each time the command is called"""
        if log.isEnabledFor(logging.DEBUG):
            log.debug(LogFmt("{0}Copy is in charge{0}\\".format(os.linesep)))
            log.debug(LogFmt(" |- arguments : '" + "' '".join(args)+"'"))

        #prepare variables for the new command
        self.__cleanup()
        #get provider class which has functions for all CCDB database operation
        assert self.context
        provider = self.context.provider
        assert isinstance(provider, AlchemyProvider)
        parsed_args = self.process_arguments(args)

        if parsed_args.assignment.isdigit():
            assignment = provider.get_assignment_by_id(parsed_args.assignment)
        # if given the source assignment
        elif parsed_args.assignment:
            assignment = provider.get_assignment_by_request(parsed_args.assignment)
        else:# no ID or assignment given
            return 0
        if not parsed_args.variation:
            variation = assignment.variation
        else:
            variation = parsed_args.variation
        if parsed_args.run:
            run_range = parsed_args.run
        else:
            run_range = assignment.run_range
        if parsed_args.comment:
            comment = parsed_args.comment
        else:
            comment = assignment.comment
        provider.make_assignment(run_range, variation, comment, assignment)
        return 0

    def process_arguments(self, args):
        parser = UtilityArgumentParser()
        parser.add_argument("-v", "--variation", default=self.context.current_variation)
        parser.add_argument("-r", "--run",  type=str, default=self.context.current_run)
        parser.add_argument("-c", "--comment", default="")
        parser.add_argument("-a", "--assignment", default="")
        result = parser.parse_args(args)
        return result

    def validate(self):
        if not self.raw_file_path or not self.raw_table_path:
            return False
        return True

    def print_help(self):
        """Prints help for the command"""
        
        print ("""Copies assignment to a new data
        
        Flags:
        -v or --variation  Variation of new assignment
        -r or --run Run range of new assignment 
        -c or --comment Comment of the new assignment
        -a or --assignment Where the data is being copied can be assignment or ID
        
         cp -a <assignment> -v <variation>  -r <run_min>-<run_max> -c <comment> 

    """)
