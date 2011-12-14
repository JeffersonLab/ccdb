import posixpath
import logging
import time
import sys

import ccdb
from ccdb.ccdb_pyllapi import Directory, ConstantsTypeTable, ConstantsTypeColumn, Variation, Assignment
from ccdb import MySQLProvider
from ccdb.cmd import ConsoleUtilBase
from ccdb.cmd import Theme
from ccdb.cmd import is_verbose, is_debug_verbose
from ccdb.PathUtils import ParseRequestResult, parse_request

log = logging.getLogger("ccdb.cmd.utils.cat")


#ccdbcmd module interface
def create_util_instance():
    log.debug("      registring Cat")
    return Cat()


#*********************************************************************
#   Class Cat - Show assignment data by ID                           *
#                                                                    *
#*********************************************************************
class Cat(ConsoleUtilBase):
    """Show assignment data by ID"""

    # ccdb utility class descr part 
    #------------------------------
    command = "cat"
    name = "Cat"
    short_descr = "Show assignment data by ID"
    uses_db = True

    # variables for each command process
    #------------------------------------
    rawentry = "/"      #object path with possible pattern, like /mole/*
    path = "/"          #parent path
    raw_table_path = ""
    use_ass_id = False
    ass_id = 0

    show_borders = True
    show_header = True
    show_comments = False
    show_date = False
    request = ParseRequestResult()

#----------------------------------------
#   process 
#----------------------------------------  
    def process(self, args):
        log.debug("Cat is gained a control over the process.")
        log.debug("   " + " ".join(args))

        assert self.context != None
                
        #reset arguments on each process        
        self.raw_table_path = ""
        self.show_borders = True
        self.show_header = True
        self.show_comments = False
        self.show_date = False
        self.request = ParseRequestResult()
        self.ass_id = 0

        if not len(args):
            print "Please provide ID for assignment. Use help cat to get more information"
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
            self.print_assignment_vertical(assignment, self.show_header, self.show_borders)
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
        assert isinstance(provider, MySQLProvider)

        assignment = Assignment()
        assignment.db_id = id
        if not provider.fill_assignment(assignment): return None
        return assignment

#----------------------------------------
#   gets assignment by parsed request
#----------------------------------------  
    def get_assignment_by_request(self, request):
        """gets assignment by parsed request"""
        
        provider = self.context.provider
        isinstance(provider, MySQLProvider)
        isinstance(request, ParseRequestResult)

        if not request.WasParsedVariation:
            request.Variation = "default"

        if not request.WasParsedRunNumber:
            request.RunNumber = self.context.current_run

        #correct path
        self.table_path = self.context.prepare_path(self.request.Path)
        
        #check such table really exists
        table = provider.get_type_table(self.table_path, False)
        if not table:
            log.warning("    Type table %s not found in the DB"% self.table_path)
            return None
        
        print " {} {} {} {} ".format(self.table_path, self.request.RunNumber, self.request.Variation, self.request.Time)
        assignments = provider.get_assignments(self.table_path, self.request.RunNumber, self.request.Variation, self.request.Time)
        if assignments and len(assignments)>0:
            return assignments[0]
        log.warning("    Error getting assignment for the table %s"% self.table_path)
    
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

        print """Show data values for assigment. use assigment ID from the vers
	-b  or --borders      - Switch show borders on of off
	-nb or --no-borders

	-h  or --header        - Show header on/off
	-nh or --no-header

	-c  or --comments     - Show comments on/off
	-nc or --no-comments

	-t  or --time         - Show time
	-nt or --no-time


    """

#----------------------------------------
#   print_assignment_vertical 
#---------------------------------------- 	
    def print_assignment_vertical(self, assignment, printHeader=True, displayBorders=True):
        assert isinstance(assignment, Assignment)

        border = " "
        if displayBorders: border = "|"

        table = assignment.type_table
        assert isinstance(table, ConstantsTypeTable)

        columnNames = table.get_column_names()
        columnTypes = table.get_column_types()
        data = assignment.data_list

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