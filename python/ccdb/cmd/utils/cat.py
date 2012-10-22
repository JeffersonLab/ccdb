import posixpath
import logging
import time
import sys
import os

import ccdb
from ccdb import Directory, TypeTable, TypeTableColumn, Variation, Assignment
from ccdb import AlchemyProvider
from ccdb.cmd import ConsoleUtilBase
from ccdb.cmd import Theme
from ccdb.path_utils import ParseRequestResult, parse_request

log = logging.getLogger("ccdb.cmd.utils.cat")


#ccdbcmd module interface
def create_util_instance():
    log.debug("      registering Cat")
    return Cat()


#*********************************************************************
#   Class Cat - Show assignment data by ID                           *
#*********************************************************************
class Cat(ConsoleUtilBase):
    """Show assignment data by ID"""

    # ccdb utility class descr part 
    #------------------------------
    command = "cat"
    name = "Cat"
    short_descr = "Show assignment data by ID"
    uses_db = True

    #specific values
    show_borders = True
    show_header = True
    show_comments = False
    show_date = False


    def __init__(self):
        # variables for each command process
        #------------------------------------
        self.raw_entry = "/"      #object path with possible pattern, like /mole/*
        self.path = "/"          #parent path
        self.raw_table_path = ""
        self.use_ass_id = False
        self.ass_id = 0
        self.print_horisontal = True
        self.user_request_print_horisontal = False
        self.user_request_print_vertical = False
        self.request = ParseRequestResult()


    #----------------------------------------
    #   process
    #----------------------------------------
    def process(self, args):
        """
        Process this command
        :param args:
        :return: 0 if command was successful, value!=0 means command was not successfull
        :rtype: int
        """
        log.debug("Cat is gained a control over the process.")
        log.debug("   " + " ".join(args))

        assert self.context is not None

        #reset arguments on each process        
        self.raw_table_path = ""
        self.show_borders = True
        self.show_header = True
        self.show_comments = False
        self.show_date = False
        self.request = ParseRequestResult()
        self.ass_id = 0
        self.user_request_print_horisontal = False
        self.user_request_print_vertical = False

        if not len(args):
            print "Please provide ID for assignment. Use 'help cat' to get more information"
            return 1

        if not self.process_arguments(args):
            return 1

            #if self.run == -1: 
            #    self.run = self.context.current_run

            #if not self.validate():
            #    return 1

            #correct path
            #self.table_path = self.context.prepare_path(self.raw_table_path)

            #check xuch table really exists
            #table = provider.get_type_table(self.table_path, False)
            #if not table:
            #    logging.warning("Type table %s not found in the DB"% self.table_path)
            #    return 1

            #assignment = provider.get_assignment(self.table_path, self.run)
        assignment = None
        if self.use_ass_id:
            assignment = self.get_assignment_by_id(self.ass_id)
        else:
            assignment = self.get_assignment_by_request(self.request)

        if assignment:
            #now we have to know, how to print an assignment
            data = assignment.constant_set.data_table

            if len(data)!=0 and len(data[0])!=0:
                if self.user_request_print_horisontal:
                    self.print_assignment_horizontal(assignment, self.show_header, self.show_borders)
                elif self.user_request_print_vertical:
                    self.print_assignment_vertical(assignment, self.show_header, self.show_borders)
                else:
                    if len(data) == 1 and len(data[0])>3:
                        self.print_assignment_vertical(assignment, self.show_header, self.show_borders)
                    else:
                        self.print_assignment_horizontal(assignment, self.show_header, self.show_borders)
            else:
                log.warning("Assignment contains no data")
        else:
            print "Cannot fill data for assignment with this ID"
            return 1

        return 0

#----------------------------------------
#   gets assignment by database id
#----------------------------------------
    def get_assignment_by_id(self, id):
        """gets assignment by database id"""

        provider = self.context.provider
        assert isinstance(provider, AlchemyProvider)
        return self.context.provider.get_assignment_by_id(id)

#----------------------------------------
#   gets assignment by parsed request
#----------------------------------------  
    def get_assignment_by_request(self, request):
        """gets assignment by parsed request"""
        
        provider = self.context.provider
        isinstance(provider, AlchemyProvider)
        isinstance(request, ParseRequestResult)

        if not request.WasParsedVariation:
            request.Variation = "default"

        
        if not request.WasParsedRunNumber:
            request.RunNumber = self.context.current_run

        #correct path
        self.table_path = self.context.prepare_path(self.request.Path)
        
        #check such table really exists
        table = provider.get_type_table(self.table_path)
        if not table:
            log.warning("    Type table %s not found in the DB"% self.table_path)
            return None
                
        assignments = provider.get_assignments(self.table_path, self.request.RunNumber, self.request.Variation, self.request.Time)
        if assignments and len(assignments)>0:
            return assignments[0]
        
        #if we here there were no assignments selected
        log.warning("    There is no data for table {}, run {}, variation '{}'".format(self.table_path, self.request.RunNumber, self.request.Variation))
        if request.WasParsedTime:
            log.warning("    on ".format(self.request.TimeString))
        return None
    
#----------------------------------------
#   process_arguments 
#----------------------------------------  
    def process_arguments(self, args):
        #solo arguments 
        if ("-b" in args)  or ("--borders" in args):
            self.show_borders = True
        if ("-nb" in args) or ("--no-borders" in args):
            self.show_borders = False
        if ("-h" in args) or ("--header"):
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
            self.user_request_print_horisontal = True
        if ("-pa" in args) or ("--vertical" in args):
            self.user_request_print_vertical = True

        #parse loop
        i=0
        token = ""
        while i < len(args):
            token = args[i].strip()
            i+=1
            if token.startswith('-'):
                #it is some command, lets parse what is the command

                #variation
                if token == "-v" or token.startswith("--variation"):
                    if i<len(args):
                        self.request.Variation = args[i].strip()
                        self.request.WasParsedPath = True
                        i+=1

                #runrange
                if token == "-r" or token == "--run":
                    try:
                         self.request.RunNumber = int(args[i].strip())
                         self.request.WasParsedRunNumber = True
                         i+=1
                    except ValueError:
                        log.warning("    Cannot read run from {} command".format(token))
                        return False
                    
                
                #get assignment by id
                if token == "--id" and i < len(args):
                    
                    token = args[i].strip()
                    i+=1
                    try:
                        self.ass_id = int(token)
                        self.use_ass_id = True
                        log.debug("    The assigment DB ID is... " + repr(self.ass_id));
                    except ValueError:
                        print "Cannot parse argument: {}".format(token)
                        return False

            else:    #!token.startswith('-')
                #it probably must be a request or just a table name
                if ':' in token:                             #it is a request
                    self.request = parse_request(token)
                else:                                        #it is a table path
                    self.request.Path = token
                    self.request.WasParsedPath = True
               

        return True


#----------------------------------------
#   validate 
#----------------------------------------  
    def validate(self):
        if not self.raw_table_path: return False
        return True


#----------------------------------------
#   print_help 
#----------------------------------------
    def print_help(self):
        "Prints help of the command"

        print """Show data values for assigment.
	-b  or --borders      - Switch show borders on of off
	-nb or --no-borders

	-h  or --header       - Show header on/off
	-nh or --no-header

	-c  or --comments     - Show comments on/off
	-nc or --no-comments

	-t  or --time         - Show time
	-nt or --no-time

        -ph or --horizontal   - Print table horizontally
        -pa or --vertical     - Print table vertically
        If no '--horizontal' or '--vertical' is given - the layout of table will be determined automatically: vertical layout if table has only 1 row and more than 3 columns otherwise horizontal

        --id show table by database ID. One can obtain ID by 'vers <table path>' command

    """


    #--------------------------------------------------------------------------------
    #   print_assignment_vertical
    #--------------------------------------------------------------------------------
    def print_assignment_horizontal(self, assignment, printHeader=True, displayBorders=True):
        """
        print table with assignment data horizontally

        :param assignment : Assignment object ot print
        :type assignment: Assignment

        :param printHeader: print header with column information or not
        :type printHeader: bool

        :param displayBorders: print '|' borders or not
        :type displayBorders: bool
        """
        assert isinstance(assignment, Assignment)

        border = " "
        if displayBorders: border = "|"

        table = assignment.constant_set.type_table
        assert isinstance(table, TypeTable)

        columnNames = [column.name  for column in table.columns]
        columnTypes = [column.type  for column in table.columns]
        data = assignment.constant_set.data_list

        columnsNum = len(columnNames)

        assert len(columnNames) == len(columnTypes)
        assert (len(data) % columnsNum) == 0

        minLength = 10
        columnLengths = [10 for i in range(columnsNum)]
        totalDataLength = 0

        #determine column length
        for i in range(0, columnsNum):
            if len(columnNames[i]) > minLength:
                columnLengths[i] = len(columnNames[i])
            else:
                columnLengths[i] = minLength

            totalDataLength += columnLengths[i];

        #this is our cap, if we need it.... 
        cap = "+" + (totalDataLength + 3 * columnsNum - 1)*"-" + "+"

            #print header if needed
        if printHeader:

            #cap?
            if displayBorders:
                print Theme.AsgmtBorder + cap

            #names line
            for i in range(0, columnsNum):
                sys.stdout.write(Theme.AsgmtBorder + border + Theme.Reset)
                frmt = " %%-%is "%columnLengths[i]
                sys.stdout.write(Theme.AsgmtHead + frmt%columnNames[i] + Theme.Reset)

            print Theme.AsgmtBorder + border + Theme.Reset #last border

            #types line
            for i in range(0, columnsNum):
                sys.stdout.write(Theme.AsgmtBorder + border + Theme.Reset)
                frmt = " %%-%is "%columnLengths[i]
                sys.stdout.write(Theme.AsgmtType + frmt%columnTypes[i] + Theme.Reset)
            print Theme.AsgmtBorder + border + Theme.Reset #last border
        else:
            if self.show_comments:
                pass


        #cap?
        if displayBorders:
            print Theme.AsgmtBorder + cap

        #data line by line
        columnIter = 0
        for dataItem in data:
            #place data
            sys.stdout.write(Theme.AsgmtBorder + border + Theme.Reset)
            frmt = " %%-%is "%columnLengths[columnIter]
            sys.stdout.write(Theme.AsgmtValue + frmt%dataItem + Theme.Reset)
            columnIter+=1

            #new line?
            if columnIter == columnsNum:
                columnIter = 0
                print Theme.AsgmtBorder + border + Theme.Reset

        #final cap?
        if displayBorders:
            print Theme.AsgmtBorder + cap



    #--------------------------------------------------------------------------------
    #   print_assignment_horizontal
    #--------------------------------------------------------------------------------
    def print_assignment_vertical(self, assignment, printHeader=True, displayBorders=True):
        """
        print columns vertically and rows horizontally

        :param assignment : Assignment object ot print
        :type assignment: Assignment

        :param printHeader: print header with column information or not
        :type printHeader: bool

        :param displayBorders: print '|' borders or not
        :type displayBorders: bool
        """

        assert isinstance(assignment, Assignment)
        
        border = " "
        if displayBorders: border = "|"

        table = assignment.constant_set.type_table
        isinstance(table, TypeTable)

        columnNames = [column.name  for column in table.columns]
        columnTypes = [column.type  for column in table.columns]
        data = assignment.constant_set.data_table
        
        if len(data)==0 :return
        if len(data[0])==0:return
        assert len(columnNames) == len(columnTypes)
        assert len(data[0]) == len(columnNames)

        #present data as columns, each column has cells
        columns = []
        headerColumnsAdded = 0
        if printHeader:
            columns.append(columnNames)
            columns.append(columnTypes)
            headerColumnsAdded = 2
        
        for row in data:
            columns.append([])
        
        #fill data to columns
        for rowI in range(0,len(data)):
            for colI in range (0,len(data[rowI])):
                columns[rowI + headerColumnsAdded].append(data[rowI][colI])

               
        #    
        #    

        
        columnLengths = [len(max(column, key=len)) for column in columns]
        totalLength =0
        for length in columnLengths: totalLength+=length

        
        
        #totalDataLength = 0

        ##determine column length
        #for i in range(0, columnsNum):
        #    if len(columnNames[i]) > minLength:
        #        columnLengths[i] = len(columnNames[i])
        #    else:
        #        columnLengths[i] = minLength

        #    totalDataLength += columnLengths[i];

        #this is our cap, if we need it.... 
        cap = "+" + (totalLength + 3 * len(columns) - 2)*"-" + "+"

        #print header if needed
        

            #names line
        #    for i in range(0, columnsNum):
        #        sys.stdout.write(Theme.AsgmtBorder + border + Theme.Reset)
        #        frmt = " %%-%is "%columnLengths[i]
        #        sys.stdout.write(Theme.AsgmtHead + frmt%columnNames[i] + Theme.Reset)
#
 #           print Theme.AsgmtBorder + border + Theme.Reset #last border

        #    #types line
        #    for i in range(0, columnsNum):
        #        sys.stdout.write(Theme.AsgmtBorder + border + Theme.Reset)
        #        frmt = " %%-%is "%columnLengths[i]
        #        sys.stdout.write(Theme.AsgmtType + frmt%columnTypes[i] + Theme.Reset)
        #    print Theme.AsgmtBorder + border + Theme.Reset #last border

        ##cap?
        if displayBorders:
            print Theme.AsgmtBorder + cap + Theme.Reset

        ##data line by line
        #columnIter = 0
        rowI=0; colI=0;

        for rowI in range(0, len(columns[0])):
            sys.stdout.write(Theme.AsgmtBorder + border + Theme.Reset)

            for colI in range(0, len(columns)):
                #place data
                dataItem = columns[colI][rowI]
                frmt = " %%-%is "%columnLengths[colI]
                if colI==0 and printHeader:
                    sys.stdout.write(Theme.AsgmtHead + frmt%dataItem + Theme.Reset)
                elif colI==1 and printHeader:
                    sys.stdout.write(Theme.AsgmtType + '('+(frmt%dataItem).strip()+')' + Theme.Reset)
                    sys.stdout.write(Theme.AsgmtBorder + border + Theme.Reset)
                else:
                    sys.stdout.write(Theme.AsgmtValue + frmt%dataItem + Theme.Reset)


            sys.stdout.write(Theme.AsgmtBorder + border + Theme.Reset + os.linesep)
        

        #    #new line?
        #    if columnIter == columnsNum:
        #        columnIter = 0
        #        print Theme.AsgmtBorder + border + Theme.Reset


        ##final cap?
        if displayBorders:
            print Theme.AsgmtBorder + cap + Theme.Reset