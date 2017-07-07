import logging
import sys
import os

from ccdb import TypeTable, Assignment
from ccdb import AlchemyProvider
from ccdb.cmd import ConsoleUtilBase
from ccdb.path_utils import ParseRequestResult, parse_request
from ccdb import BraceMessage as Lfm  # lfm is aka log format message. See BraceMessage desc about
from sqlalchemy.orm.exc import NoResultFound

log = logging.getLogger("ccdb.cmd.utils.cat")


# ccdb cmd module interface
def create_util_instance():
    log.debug(Lfm("      registering Cat"))
    return Cat()


# *********************************************************************
#   Class Cat - Show assignment data by ID                           *
# *********************************************************************
class Cat(ConsoleUtilBase):
    """Show assignment data by ID"""

    # ccdb utility class descr part
    # ------------------------------
    command = "cat"
    name = "Cat"
    short_descr = "Show assignment data by ID"
    uses_db = True

    # specific values
    show_borders = True
    show_header = True
    show_comments = False
    show_date = False

    def __init__(self):
        ConsoleUtilBase.__init__(self)
        self.raw_entry = "/"  # object path with possible pattern, like /mole/*
        self.path = "/"       # parent path
        self.raw_table_path = ""
        self.use_ass_id = False
        self.ass_id = 0
        self.print_horizontal = True
        self.user_request_print_horizontal = False
        self.user_request_print_vertical = False
        self.request = ParseRequestResult()

    # ----------------------------------------
    #   process
    # ----------------------------------------
    def process(self, args):
        """
        Process this command
        :param args:
        :return: 0 if command was successful, value!=0 means command was not successful
        :rtype: int
        """
        if log.isEnabledFor(logging.DEBUG):
            log.debug(Lfm("{0}Cat command is in charge {0}\\", os.linesep))
            log.debug(Lfm(" |- arguments : '" + "' '".join(args) + "'"))

        assert self.context is not None

        # reset arguments on each process
        self.raw_table_path = ""
        self.show_borders = True
        self.show_header = True
        self.show_comments = False
        self.show_date = False
        self.request = ParseRequestResult()
        self.ass_id = 0
        self.user_request_print_horizontal = False
        self.user_request_print_vertical = False

        if not len(args):
            print ("Please provide ID for assignment. Use 'help cat' to get more information")
            return 1

        if not self.process_arguments(args):
            return 1

        if self.use_ass_id:
            assignment = self.get_assignment_by_id(self.ass_id)
        else:
            assignment = self.get_assignment_by_request(self.request)

        if assignment:
            # now we have to know, how to print an assignment
            data = assignment.constant_set.data_table

            if len(data) and len(data[0]):
                if self.user_request_print_horizontal:
                    self.print_assignment_horizontal(assignment, self.show_header, self.show_borders,
                                                     self.show_comments)
                elif self.user_request_print_vertical:
                    self.print_assignment_vertical(assignment, self.show_header, self.show_borders, self.show_comments)
                else:
                    if len(data) == 1 and len(data[0]) > 3:
                        self.print_assignment_vertical(assignment, self.show_header, self.show_borders,
                                                       self.show_comments)
                    else:
                        self.print_assignment_horizontal(assignment, self.show_header, self.show_borders,
                                                         self.show_comments)
            else:
                log.warning("Assignment contains no data")
        else:
            print ("Cannot fill data for assignment with this ID")
            return 1

        return 0

    # ----------------------------------------
    #   gets assignment by database id
    # ----------------------------------------
    def get_assignment_by_id(self, assignment_id):
        """gets assignment by database id"""

        provider = self.context.provider
        assert isinstance(provider, AlchemyProvider)
        return self.context.provider.get_assignment_by_id(assignment_id)

    # ----------------------------------------
    #   gets assignment by parsed request
    # ----------------------------------------
    def get_assignment_by_request(self, request):
        """gets assignment by parsed request
        @param request: Parsed request
        @type request: ParseRequestResult
        """
        return self._get_assignment_by_request(request)

    # ----------------------------------------
    #   gets assignment by parsed request
    # ----------------------------------------
    def _get_assignment_by_request(self, request):

        provider = self.context.provider
        assert isinstance(provider, AlchemyProvider)
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

        log.debug(Lfm(" |- getting assignments for path : '{0}', run: '{1}', var: '{2}', time: '{3}'"
                      "", table_path, request.run, request.variation, time))
        try:
            assignment = provider.get_assignment(table_path, request.run, request.variation, time)
            log.debug(Lfm(" |- found assignment: {0}", assignment))
            return assignment

        except NoResultFound:
            # if we here there were no assignments selected
            log.warning(Lfm("There is no data for table {}, run {}, variation '{}'",
                            table_path, request.run, request.variation))
            if request.time_is_parsed:
                log.warning("    on ".format(request.time_str))

        return None

    # ----------------------------------------
    #   process_arguments
    # ----------------------------------------
    def process_arguments(self, args):
        # solo arguments
        if ("-b" in args) or ("--borders" in args):
            self.show_borders = True
        if ("-nb" in args) or ("--no-borders" in args):
            self.show_borders = False
        if ("-h" in args) or "--header":
            self.show_header = True
        if ("-nh" in args) or ("--no-header" in args):
            self.show_header = False
        if ("-c" in args) or ("--comments" in args):
            self.show_comments = True
        if ("-nc" in args) or ("--no-comments" in args):
            self.show_comments = False
        if ("-t" in args) or ("--time" in args):
            self.show_date = True
        if ("-nt" in args) or ("--no-time" in args):
            self.show_date = False
        if ("-ph" in args) or ("--horizontal" in args):
            self.user_request_print_horizontal = True
        if ("-pa" in args) or ("--vertical" in args):
            self.user_request_print_vertical = True

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
                        self.request.variation = args[i].strip()
                        self.request.variation_is_parsed = True
                        i += 1

                # runrange
                if token == "-r" or token == "--run":
                    try:
                        self.request.run = int(args[i].strip())
                        self.request.run_is_parsed = True
                        i += 1
                    except ValueError:
                        log.warning("Cannot read run from '{}' command", token)
                        return False

                # get assignment by id
                if token == "--id" and i < len(args):

                    token = args[i].strip()
                    i += 1
                    try:
                        self.ass_id = int(token)
                        self.use_ass_id = True
                        log.debug(Lfm(" |- parsed DB id : '{}' ", self.ass_id))
                    except ValueError:
                        log.warning("Cannot parse assignment DB id: '{}'", token)
                        return False

            else:  # !token.startswith('-')
                # it probably must be a request or just a table name
                log.debug(Lfm(" |- parsing request : '{0}'", token))
                self.request = parse_request(token)

        return True

    # ----------------------------------------
    #   validate
    # ----------------------------------------
    def validate(self):
        if not self.raw_table_path:
            return False
        return True

    # --------------------------------------------------------------------------------
    #   print_assignment_vertical
    # --------------------------------------------------------------------------------
    def print_assignment_horizontal(self, assignment, print_header=True, display_borders=True, comments=False):
        """
        print table with assignment data horizontally

        :param assignment : Assignment object ot print
        :type assignment: Assignment

        :param print_header: print header with column information or not
        :type print_header: bool

        :param comments: print comments

        :param display_borders: print '|' borders or not
        :type display_borders: bool

        """
        log.debug(Lfm(" |- print asgmnt horizontally: header {0}, borders {1}, comments {2}"
                      "", print_header, display_borders, comments))

        border = "|" if display_borders else " "

        assert isinstance(assignment, Assignment)
        table = assignment.constant_set.type_table
        assert isinstance(table, TypeTable)

        # PRINT COMMENTS
        if comments:
            print ("#" + str(assignment.comment).replace(os.linesep, os.linesep + "#"))

        column_names = [column.name for column in table.columns]
        column_types = [column.type for column in table.columns]
        data = assignment.constant_set.data_list

        columns_count = len(column_names)

        assert len(column_names) == len(column_types)
        assert (len(data) % columns_count) == 0

        min_width = 10
        column_width = [10 for _ in range(columns_count)]
        total_data_width = 0

        # determine column length
        for i in range(0, columns_count):
            if len(column_names[i]) > min_width:
                column_width[i] = len(column_names[i])
            else:
                column_width[i] = min_width

            total_data_width += column_width[i]

        # this is our cap, if we need it....
        cap = "+" + (total_data_width + 3 * columns_count - 1) * "-" + "+"

        # print header if needed
        if print_header:

            # cap?
            if display_borders:
                print (self.theme.AsgmtBorder + cap)

            # names line
            for i in range(0, columns_count):
                sys.stdout.write(self.theme.AsgmtBorder + border + self.theme.Reset)
                col_format = " %%-%is " % column_width[i]
                sys.stdout.write(self.theme.AsgmtHead + col_format % column_names[i] + self.theme.Reset)

            print (self.theme.AsgmtBorder + border + self.theme.Reset)  # last border

            # types line
            for i in range(0, columns_count):
                sys.stdout.write(self.theme.AsgmtBorder + border + self.theme.Reset)
                col_format = " %%-%is " % column_width[i]
                sys.stdout.write(self.theme.AsgmtType + col_format % column_types[i] + self.theme.Reset)
            print (self.theme.AsgmtBorder + border + self.theme.Reset)  # last border

        # cap?
        if display_borders:
            print (self.theme.AsgmtBorder + cap)

        # data line by line
        column_iter = 0
        for dataItem in data:
            # place data
            sys.stdout.write(self.theme.AsgmtBorder + border + self.theme.Reset)
            col_format = " %%-%is " % column_width[column_iter]
            sys.stdout.write(self.theme.AsgmtValue + col_format % dataItem + self.theme.Reset)
            column_iter += 1

            # new line?
            if column_iter == columns_count:
                column_iter = 0
                print (self.theme.AsgmtBorder + border + self.theme.Reset)

        # final cap?
        if display_borders:
            print (self.theme.AsgmtBorder + cap)

    # --------------------------------------------------------------------------------
    #   print_assignment_horizontal
    # --------------------------------------------------------------------------------
    def print_assignment_vertical(self, assignment, print_header=True, display_borders=True, comments=False):
        """
        print columns vertically and rows horizontally

        :param assignment : Assignment object ot print
        :type assignment: Assignment

        :param print_header: print header with column information or not
        :type print_header: bool

        :param display_borders: print '|' borders or not
        :type display_borders: bool

        :param comments: print comments
        """
        log.debug(Lfm(" |- print asgmnt vertically: header {0}, borders {1}, comments {2}",
                      print_header, display_borders, comments))

        assert isinstance(assignment, Assignment)

        border = " "
        if display_borders:
            border = "|"

        table = assignment.constant_set.type_table
        isinstance(table, TypeTable)

        # PRINT COMMENTS
        if comments:
            print ("#" + str(assignment.comment).replace(os.linesep, "#" + os.linesep))

        column_names = [column.name for column in table.columns]
        column_types = [column.type for column in table.columns]
        data = assignment.constant_set.data_table

        if not data:  # no rows
            return
        if not data[0]:  # no columns
            return
        assert len(column_names) == len(column_types)
        assert len(data[0]) == len(column_names)

        # present data as columns, each column has cells
        columns = []
        header_columns_added = 0
        if print_header:
            columns.append(column_names)
            columns.append(column_types)
            header_columns_added = 2

        for _ in data:
            columns.append([])

        # fill data to columns
        for rowI in range(0, len(data)):
            for colI in range(0, len(data[rowI])):
                columns[rowI + header_columns_added].append(data[rowI][colI])

        column_widths = [len(max(column, key=len)) for column in columns]
        total_width = 0
        for length in column_widths:
            total_width += length

        # totalDataLength = 0

        # #determine column length
        # for i in range(0, columnsNum):
        #    if len(columnNames[i]) > minLength:
        #        columnLengths[i] = len(columnNames[i])
        #    else:
        #        columnLengths[i] = minLength

        #    totalDataLength += columnLengths[i];

        # this is our cap, if we need it....
        cap = "+" + (total_width + 3 * len(columns) - 2) * "-" + "+"

        # print header if needed
        # names line
        #    for i in range(0, columnsNum):
        #        sys.stdout.write(self.theme.AsgmtBorder + border + self.theme.Reset)
        #        frmt = " %%-%is "%columnLengths[i]
        #        sys.stdout.write(self.theme.AsgmtHead + frmt%columnNames[i] + self.theme.Reset)
        #
        #    print self.theme.AsgmtBorder + border + self.theme.Reset #last border
        #    #types line
        #    for i in range(0, columnsNum):
        #        sys.stdout.write(self.theme.AsgmtBorder + border + self.theme.Reset)
        #        frmt = " %%-%is "%columnLengths[i]
        #        sys.stdout.write(self.theme.AsgmtType + frmt%columnTypes[i] + self.theme.Reset)
        #    print self.theme.AsgmtBorder + border + self.theme.Reset #last border

        # cap?
        if display_borders:
            print (self.theme.AsgmtBorder + cap + self.theme.Reset)

        # #data line by line
        # columnIter = 0

        for rowI in range(0, len(columns[0])):
            sys.stdout.write(self.theme.AsgmtBorder + border + self.theme.Reset)

            for colI in range(0, len(columns)):
                # place data
                data_item = columns[colI][rowI]
                frmt = " %%-%is " % column_widths[colI]
                if colI == 0 and print_header:
                    sys.stdout.write(self.theme.AsgmtHead + frmt % data_item + self.theme.Reset)
                elif colI == 1 and print_header:
                    sys.stdout.write(self.theme.AsgmtType + '(' + (frmt % data_item).strip() + ')' + self.theme.Reset)
                    sys.stdout.write(self.theme.AsgmtBorder + border + self.theme.Reset)
                else:
                    sys.stdout.write(self.theme.AsgmtValue + frmt % data_item + self.theme.Reset)

            sys.stdout.write(self.theme.AsgmtBorder + border + self.theme.Reset + os.linesep)

        # #final cap?
        if display_borders:
            print (self.theme.AsgmtBorder + cap + self.theme.Reset)

    # ----------------------------------------
    #   print_help
    # ----------------------------------------
    def print_help(self):
        """Prints help of the command"""

        print ("""Show data values for assignment.

Usage:
    cat <request or table path>
    cat --id <assignment_id>   #Where assignment_id provided by 'vers <table path>' command

Formatting flags:

    -c  or --comments     - Show comments on/off
    -nc or --no-comments

    -ph or --horizontal   - Print table horizontally
    -pa or --vertical     - Print table vertically
    (If no '--horizontal' or '--vertical' flag is given, the layout of table is determined automatically:
    vertical layout if table has only 1 row and more than 3 columns, horizontal otherwise)

    -b  or --borders      - Switch show borders on of off
    -nb or --no-borders

    -h  or --header       - Show header on/off
    -nh or --no-header

    -t  or --time         - Show time
    -nt or --no-time

Examples:
    > cat /test/test_vars/test_table               #print latest data for test_table
    > cat /test/test_vars/test_table::subtest      #print latest data in subtest variation
    > cat /test/test_vars/test_table:::2012-08     #print data latest for august 2012

See also 'dump' command which is 'cat' formatted to save data to files. 'help dump'

    """)
