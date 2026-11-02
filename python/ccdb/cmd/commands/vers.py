import logging
import os


from ccdb import AlchemyProvider
import ccdb
from ccdb.cmd import CliCommandBase, UtilityArgumentParser
from ccdb.path_utils import parse_request
from ccdb.brace_log_message import BraceMessage as LogFmt


log = logging.getLogger("ccdb.cmd.commands.vers")


# ********************************************************************
#   Class Versions - Show versions of data for specified type table  *
# ********************************************************************
class Versions(CliCommandBase):
    """" Show versions of data. Assignments in terms of CCDB """
    
    # ccdb utility class descr part 
    # ------------------------------
    command = "vers"
    name = "Versions"
    short_descr = "Show versions of data for specified type table"
    uses_db = True

    def __init__(self, context):
        self.context = context

    # - - - - - - - - - - - - - - - - - - - - -
    def execute(self, args):
        """Main function that do the job"""

        if log.isEnabledFor(logging.DEBUG):
            log.debug(LogFmt("{0}Versions is in charge{0}\\".format(os.linesep)))
            log.debug(LogFmt(" |- arguments : '" + "' '".join(args)+"'"))

        # preparations
        assert self.context is not None
        provider = self.context.provider
        isinstance(provider, AlchemyProvider)
        
        # process arguments
        (raw_table_path, variation, run, extended) = self._process_arguments(args)

        if not raw_table_path:
            log.info("Table name (path) is required. See 'help vers'")
            return True

        # a request with a tag lists the versions the tag sees: created at or before its time, in its variation and
        # in the parents of it, where the request resolves as cat does
        tag = None
        if '@' in raw_table_path:
            request = parse_request(raw_table_path)
            if variation:
                raise ValueError("A request with a tag can have neither a variation nor a time; remove -v/--variation")
            raw_table_path = request.path
            tag = provider.get_tag(request.tag)
            if request.run_is_parsed:
                run = request.run

        # correct path
        table_path = self.context.prepare_path(raw_table_path)

        # get and print assignments. The listing shows no data, so the data text of the sets is not loaded
        table = provider.get_type_table(table_path)
        assignments = provider.get_assignments(table, run, variation, defer_vault=True, tag=tag)
        if tag is not None:
            tree = [v.name for v in provider.get_variation_tree_up(provider.get_tag_variation(tag))]
            variation = "{0} (tag '{1}' at {2} UTC)".format(" -> ".join(tree), tag.name,
                                                             tag.snapshot_time.strftime("%Y-%m-%d %H:%M:%S"))
        sharer_counts = provider.get_constant_set_sharer_counts(table) if extended else None
        self.print_assignments(assignments, variation, run, sharer_counts)
        return True
            
    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    @staticmethod
    def _process_arguments(args):
        parser = UtilityArgumentParser()
        parser.add_argument("raw_path", nargs='?', default="")
        parser.add_argument("-v", "--variation", default="")
        parser.add_argument("-r", "--run", type=int, default=-1)
        parser.add_argument("-l", "--extended", action="store_true")

        # parse
        result = parser.parse_args(args)

        return result.raw_path, result.variation, result.run, result.extended

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    def print_assignments(self, assignments, variation, run, sharer_counts=None):
        """
        Prints the assignments as a table

        :param sharer_counts: {constant set id: number of assignments using it}; when given (vers -l),
                              two columns show the data hash prefix and that number
        """

        # if user specifies run, show it!
        if run != -1:
            print("For run: {}".format(run))

        # if user specified variation, show it!
        if variation:
            print("For variation: {}".format(variation))

        # table header... and table =)
        extended = sharer_counts is not None
        data_header = "(data)        (shared)  " if extended else ""
        print(self.theme.Directories + "(ID)     (created)              (user)           (variation)     (run range)      "
              + data_header + "(comments)" + self.theme.Reset)
        for asgmnt in assignments:
            assert isinstance(asgmnt, ccdb.model.Assignment)
            assert isinstance(asgmnt.author, ccdb.model.User)

            max_str = repr(asgmnt.run_range.max)
            if asgmnt.run_range.max == ccdb.INFINITE_RUN:
                max_str="inf"
            # vers -l: the first 12 hex digits of the data hash, and how many assignments share that data
            data_columns = ""
            if extended:
                constant_set = asgmnt.constant_set
                data_columns = "%-13s " % constant_set.sha256[:12] + "%-9s " % sharer_counts.get(constant_set.id, 0)

            print(" %-6i "%asgmnt.id +\
                  " %-20s"%asgmnt.created.strftime("%Y-%m-%d %H-%M-%S   ") +\
                  " %-15s" % asgmnt.author.name + " " +\
                  " %-14s "%asgmnt.variation.name +\
                  " %-15s "%(repr(asgmnt.run_range.min) + "-" + max_str) +\
                  data_columns +\
                  asgmnt.comment[0:20].replace("\n", " "))

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    def print_help(self):
        """Prints help of the command"""
          
        print("""Show versions of data for specified type table

Flags:
    -v or --variation  - filters output by variation
    -r or --run        - filters output by run
    -l or --extended   - also shows the first 12 hex digits of the data hash (data)
                         and the number of assignments that share this data (shared)

Remark: Current working variation which is set by 'var' command or '-v' ccdb flag
is not propagated to 'vers' command.

Example:
    >> vers /test/test_vars/test_table   #get all data versions
    >> cd /test/test_vars                #navigate to directory
    >> vers -v default test_table        #shows only data versions in default variation
    >> vers test_table@mytag             #versions that tag 'mytag' sees, up to its time: its variation
                                         #and its parents up to default, as 'cat test_table@mytag' resolves
    >> vers -l test_table                #shows which versions share the same data
    """)