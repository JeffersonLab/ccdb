import logging
import os

from ccdb.cmd import CliCommandBase, UtilityArgumentParser
from ccdb import AlchemyProvider
from ccdb import BraceMessage as LogFmt


log = logging.getLogger("ccdb.cmd.commands.cp")


# *********************************************************************
#      Class Copy - Copies an assignment to a new dataset             *
#                                                                     *
# *********************************************************************
class Copy(CliCommandBase):
    """Copies an assignment to a new set of data"""
    
    command = "cp"
    name = "Copy"
    short_descr = "Copy assignment"
    uses_db = True

    def execute(self, args):
        """This is an entry point for each time the command is called"""
        if log.isEnabledFor(logging.DEBUG):
            log.debug(LogFmt("{0}Copy is in charge{0}\\".format(os.linesep)))
            log.debug(LogFmt(" |- arguments : '" + "' '".join(args)+"'"))

        # get provider class which has functions for all CCDB database operation
        provider = self.context.provider

        assert isinstance(provider, AlchemyProvider)
        parsed_args = self.process_arguments(args)
        if not parsed_args.variation:
            variation = None
        else:
            variation = parsed_args.variation
        if parsed_args.run:
            run_range_str = parsed_args.run
            run_min, run_max, run_set, run_max_set = self.context.parse_run_range(run_range_str)
            run_range = provider.get_or_create_run_range(run_min, run_max)
        else:
            run_range = None
        if parsed_args.comment:
            comment = parsed_args.comment
        else:
            comment = ""
        if parsed_args.assignment.isdigit():
            assignment = provider.get_assignment_by_id(parsed_args.assignment)
            # if given the source assignment
        else:
            assignment = provider.get_assignment_by_request(parsed_args.assignment)
        result_assignment = provider.copy_assignment(assignment, run_range, variation, comment)
        return result_assignment

    def process_arguments(self, args):
        parser = UtilityArgumentParser()
        parser.add_argument("-v", "--variation", default=self.context.current_variation)
        parser.add_argument("-r", "--run",  type=str, default=self.context.current_run)
        parser.add_argument("-c", "--comment", default="")
        parser.add_argument("assignment")
        result = parser.parse_args(args)
        return result

    def print_help(self):
        """Prints help for the command"""
        
        print("""Copies assignment - adds a new assignment with the same data but another run range, variation, time
        
        Flags:
        -v or --variation  Variation of new assignment
        -r or --run Run range of new assignment 
        -c or --comment Comment of the new assignment
        -a or --assignment Where the data is being copied can be assignment or database ID
        
         cp -a <assignment> -v <variation>  -r <run_min>-<run_max> -c <comment>""")
