import logging
import os


from ccdb import AlchemyProvider
import ccdb
from ccdb.cmd import ConsoleUtilBase, UtilityArgumentParser
from ccdb.brace_log_message import BraceMessage as LogFmt


log = logging.getLogger("ccdb.cmd.utils.vers")


# ccdbcmd module interface
def create_util_instance():
    log.debug("      registering Versions")
    return Versions()


#*********************************************************************
#   Class Versions - Show versions of data for specified type table  *
#                                                                    *
#*********************************************************************
class Versions(ConsoleUtilBase):
    """" Show versions of data. Assignments in terms of CCDB """
    
    # ccdb utility class descr part 
    # ------------------------------
    command = "vers"
    name = "Versions"
    short_descr = "Show versions of data for specified type table"
    uses_db = True

    # - - - - - - - - - - - - - - - - - - - - -
    def process(self, args):
        """Main function that do the job"""

        if log.isEnabledFor(logging.DEBUG):
            log.debug(LogFmt("{0}Versions is in charge{0}\\".format(os.linesep)))
            log.debug(LogFmt(" |- arguments : '" + "' '".join(args)+"'"))

        # preparations
        assert self.context is not None
        provider = self.context.provider
        isinstance(provider, AlchemyProvider)
        
        # process arguments
        (raw_table_path, variation, run) = self._process_arguments(args)

        if not raw_table_path:
            log.info("Table name (path) is required. See 'help vers'")
            return 0    # OK return

        # correct path
        table_path = self.context.prepare_path(raw_table_path)

        # get and print assignments
        assignments = provider.get_assignments(table_path, run, variation)
        self.print_assignments(assignments, variation, run)
        return 0
            
    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    @staticmethod
    def _process_arguments(args):
        parser = UtilityArgumentParser()
        parser.add_argument("raw_path", nargs='?', default="")
        parser.add_argument("-v", "--variation", default="")
        parser.add_argument("-r", "--run", type=int, default=-1)
        
        # parse
        result = parser.parse_args(args)

        return result.raw_path, result.variation, result.run

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    def print_assignments(self, assignments, variation, run):

        # if user specifies run, show it!
        if run != -1:
            print("For run: {}".format(run))

        # if user specified variation, show it!
        if variation:
            print("For variation: {}".format(variation))

        # table header... and table =)
        print self.theme.Directories + "(ID)   (Created)              (Modified)              (variation)     (run range)      (comments)"
        for asgmnt in assignments:
            assert isinstance(asgmnt, ccdb.Assignment)
            max_str = repr(asgmnt.run_range.max)
            if asgmnt.run_range.max == ccdb.INFINITE_RUN:
                max_str="inf"
            print " %-5i "%asgmnt.id +\
                  " %-20s"%asgmnt.created.strftime("%Y-%m-%d %H-%M-%S   ") +\
                  " %-20s"%asgmnt.modified.strftime("%Y-%m-%d %H-%M-%S   ") + " " +\
                  " %-14s "%asgmnt.variation.name +\
                  " %-15s "%(repr(asgmnt.run_range.min) + "-" + max_str) +\
                  asgmnt.comment[0:20].replace("\n", " ")

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    def print_help(self):
        """Prints help of the command"""
          
        print """Show versions of data for specified type table

Flags:
    -v or --variation  - filters output by variation
    -r or --run        - filters output by run

Remark: Current working variation which is set by 'var' command or '-v' ccdb flag
is not propagated to 'vers' command.

Example:
    >> vers /test/test_vars/test_table   #get all data versions
    >> cd /test/test_vars                #navigate to directory
    >> vers -v default test_table        #shows only data versions in default variation
    """