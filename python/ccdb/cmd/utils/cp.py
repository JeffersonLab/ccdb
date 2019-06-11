
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
from wheezy.template.ext.determined import parse_args

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

       # log.debug(self.get_assignment_by_request(self.process_arguments(args)))

        #process arguments
        parsed_args = self.process_arguments(args)

        if parsed_args.assignment:
            assignment = self.get_assignment_by_request(parsed_args.assignment)
        log.debug(assignment)
        log.debug(assignment.request)
        log.debug(assignment.comment)

        if not self.validate(parsed_args):
            return 1   # the return is like application ret. 1 means problems


        # try avoid print() and use log to print data
        log.debug(self.context.current_variation + self.context.current_run)
        log.debug(parsed_args.variation + parsed_args.run)
        log.debug(self.context.current_path)
        # the return is like application ret. 0 means OK
        return 0

    def process_arguments(self, args):
        #solo arguments
        #utility argument parser is argparse which raises errors instead of exiting app
        parser = UtilityArgumentParser()
        parser.add_argument("-v", "--variation", default=self.context.current_variation)
        parser.add_argument("-r", "--run",  type=str, default=self.context.current_run)
        parser.add_argument("-c", "--comment", default="")
        parser.add_argument("-a", "--assignment", default="")# not sure if there should be id and assignment
        parser.add_argument("--id", type=int, default=0)
        result = parser.parse_args(args)

        return result

    def get_assignment_by_request(self, request):
        if isinstance(request, str):# request is a string parse it and make a request
            request = parse_request(request)

        provider = self.context.provider
        assert isinstance(request, ParseRequestResult)
        if not request.variation_is_parsed:
            request.variation = self.context.current_variation

        if not request.run_is_parsed:
            request.run = self.context.current_run

        # correct path
        table_path = self.context.prepare_path(request.path)
        time = request.time if request.time_is_parsed else None

        # check such table really exists (otherwise exception will be thrown)
        # noinspection PyBroadException
        try:
            provider.get_type_table(table_path)
        except:
            log.error("Cant load: " + table_path)

        log.debug(LogFmt(" |- getting assignments for path : '{0}', run: '{1}', var: '{2}', time: '{3}'"
                      "", table_path, request.run, request.variation, time))
        try:
            assignment = provider.get_assignment(table_path, request.run, request.variation, time)
            log.debug(LogFmt(" |- found assignment: {0}", assignment))
            return assignment

        except NoResultFound:
            # if we here there were no assignments selected
            log.warning(LogFmt("There is no data for table {}, run {}, variation '{}'",
                            table_path, request.run, request.variation))
            if request.time_is_parsed:
                log.warning("    on ".format(request.time_str))

        return None
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
        --id ID of data
        -a or --assignment The assignment to be copied to the data
        
         cp -v <variation>  -r <run_min>-<run_max> -c <comment> --id <DB ID>

    """)
