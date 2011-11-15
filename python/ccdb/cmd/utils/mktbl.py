import posixpath
import re
import logging

import ccdb
from ccdb.cmd import is_verbose, is_debug_verbose, Theme, ConsoleUtilBase
from ccdb.cmd.Theme import bool_color, print_bool


log = logging.getLogger("ccdb.cmd.utils.mktbl")

#ccdbcmd module interface
def create_util_instance():
    log.debug("      registring MakeTable")
    return MakeTable()


#*********************************************************************
#   Class MakeTable - Create constants type table                    *
#                                                                    *
#*********************************************************************
class MakeTable(ConsoleUtilBase):
    """ Create constants type table """
    
    # ccdb utility class descr part 
    #------------------------------
    command = "mktbl"
    name = "MakeTable"
    short_descr = "Create constants type table"
    uses_db = True
    
#----------------------------------------
#   __init__ 
#---------------------------------------- 
    def __init__(self):
        self.columns = {}
        self.unparsed_columns = []
        self.rows = 1
        self.rows_set = False
        self.interactive = False
        self.interactive_set = False
        self.comment = ""
        self.comment_set = False
        self.table_name = ""
        self.table_parent_path = ""
        self.table_path = ""
        self.table_path_set = False
        self.no_columns_quantity=False
    
#--------------------------------------------------------------------------------
#   reset_on_process - sets values to be ready for new process function
#--------------------------------------------------------------------------------     
    def reset_on_process(self):
        self.columns = {}
        self.unparsed_columns = []
        self.rows = 1
        self.rows_set = False
        self.interactive = False
        self.interactive_set = False
        self.comment = ""
        self.comment_set = False
        self.table_name = ""
        self.table_parent_path = ""
        self.table_path = ""
        self.table_path_set = False
        self.no_columns_quantity=False
        #set interactive mode as context by default
        self.interactive = self.context.is_interactive
        

#----------------------------------------
#   process - processes commands
#----------------------------------------   
    def process(self, args):
        
        #>oO debug      
        log.debug("Cat is gained a control over the process.")
        log.debug("   " + " ".join(args))
        
        #reset all needed variables
        self.reset_on_process()
        
        #process arguments
        self.process_arguments(args)
        
        
        if self.interactive:
            self.interactive_mode()
        
        #lets parse columns
        self.columns = self.parse_columns(self.unparsed_columns)
        
        #set name
        self.table_path = self.context.prepare_path(self.table_path)
        (self.table_parent_path, self.table_name) = posixpath.split(self.table_path)
        
        #>oO debug
        if is_debug_verbose(): self.print_settings_summary()
        
        if is_verbose() and not self.interactive:
            self.print_validation()
        
        #create table
        self.do_create_type()
        

#----------------------------------------
#   process - processes commands
#----------------------------------------              
    def interactive_mode(self):
        if not self.table_path_set:
            self.table_name = raw_input("Enter table name :")
            self.table_parent_path = raw_input("Enter table parent path: ")
            self.table_path = posixpath.join(self.table_parent_path, self.table_name)
        if not self.comment_set:
            self.comment = raw_input("Enter comment :")


#----------------------------------------
#   process - processes commands
#----------------------------------------         
    def do_create_type(self):
        if is_debug_verbose():
            print "writing to database..." 
            
        result = self.context.provider.create_type_table(self.table_name, self.table_parent_path, self.rows, self.columns, self.comment)
        
        if result:
            print "saving table to database... " + Theme.Success + " completed"
        else:
            print "saving table to database... " + Theme.Fail + " failed"
            
        #table = ccdb.ccdb_pyllapi.ConstantsTypeTable()
        #table.SetName(self.table_name)
        #table.SetComment(self.comment)
        #for pycolumn in self.columns:
        #    column = ccdb.ccdb_pyllapi.ConstantsTypeColumn()
        #    column.SetName(pycolumn["name"])
        #    column.SetType(pycolumn["type"])
        #    table.AddColumn(column)


#----------------------------------------------
#   process_arguments - process input arguments
#----------------------------------------------
    def process_arguments(self, args):
        """@brief process input arguments
        
           @remarks Logic:
           *  All tokens that have '-' in the beginning are commands
           *  If token starts with '#' this and all next tokens are comments
           *  If token not starts with '-' or '#' it could be a table name or column name
               > So the first such token considered to be table name
               > All other such tokens are treated as columns
        
        """
        
        #parse loop
        i=0
        token = ""
        while i < len(args):
            token = args[i].strip()
            i+=1
            if token.startswith('-'): #it is some command

                #rows number
                if token == "-r" or token.startswith("--rows"):
                    if i<len(args):
                        try:
                            self.rows =  int(args[i])
                            self.rows_set = True
                        except ValueError:
                            log.warning("Cannot parse number of rows")                      
                            self.rows =  1
                            self.rows_set = False
                            
                        i+=1

                #no columns quantity 
                if token == "-nq" or token.startswith("--no-quantity"):
                    self.no_columns_quantity=True
                    continue

                #interactive mode
                if token == "-i" or token == "--interactive":
                    self.interactive = True
                    self.interactive_set = True
                
            else:
                
                #is it a comment?
                if token.startswith("#"):
                    #everething next are comments
                    self.comment += " ".join( args[i-1:])
                    self.comment_set = True
                    break #break the loop since everething next are comment
                
                #if table_path is NOT set it is table_path 
                elif not self.table_path_set:
                    self.table_path = token
                    self.table_path_set = True
                
                #othervise it is one of the columns
                else:
                    self.unparsed_columns.append(token)
                    
    
    # parse columns 
    #------------------------------ ----------
    def parse_columns(self, unparsed_columns):
        """ parse columns part of arguments """
        
        columns = {}
        for unparsed_column in unparsed_columns:
            parse_result = self.parse_column(unparsed_column)
            if parse_result:
                if parse_result["quantity"] != 1:
                    #if user i.e. have naming like value_1 and 3 field 
                    #we should produse value_1 value_2 value_3
                    #so we should take the last part and see if it is 
                    #some number 
                    preg = "^.+(?P<start>[0-9]+)$"
                    m = re.match(preg, parse_result["name"])
                    start_index = 0
                    if m and m.group("start"):
                        try:
                            start_index = int(m.group("start"))
                            
                            #correct numbers will be added later
                            tmp = parse_result["name"]
                            parse_result["name"] = tmp[:-len(m.group("start"))]
                        except ValueError:
                            pass
            
                    for i in range(start_index, start_index + parse_result["quantity"]):
                        columns[parse_result["name"]+repr(i)] = parse_result["type"]
                        
                else:
                    columns[parse_result["name"]] = parse_result["type"]
        return columns
            
    
    # parse each column argument record
    #-----------------------------------
    def parse_column(self, value):
        """parse each column argument record"""
        
        result = {}
        result["type"] = "double" #default type
        result["name"] = ""       #no name
        result["quantity"] = 1    #column quantity
        result["no_columns_quantity"] = self.no_columns_quantity

        #regular expression that matches strings like this
        # <quantity><name>(<type>) or <quantity>(<pretype>)<name>
        
        preg = "(?P<quantity>^[0-9]*)(?P<name>[0-9a-zA-Z_]+)*(=(?P<type>.*))*"
        if self.no_columns_quantity:
            preg = "(?P<name>[0-9a-zA-Z_]+)*(=(?P<type>.*))*"
        
        m = re.match(preg, value)
        
        #fill results
        if not self.no_columns_quantity and m.group("quantity"):
            try:
                result["quantity"] = int(m.group("quantity"))
            except ValueError:
                pass
                        
        if(m.group("type")):
            result["type"] = m.group("type")
        
        if(m.group("name")):
            result["name"] = m.group("name")
              
        return result
            
            
    # print help
    #-----------------------------------
    def print_help(self):
        "prints help for MakeTable"
        
        print """
MakeTable or mktbl - create type table with the specified namepath and parameters

usage: 
     
    mktbl <name> -r <rows_number> <columns> #<comments>

    name        - is a /name/path
    rows_number - number of rows
    columns     - see 'columns format'
    comments    - are comments...

columns format:
    minimal columns format:
      <name1> <name2> ... <nameN>   -   create N columns, with names name1 ... nameN of type double (by default)

    full format for each column:
       <quantity><name><start_index>=<type> 

    where: 
       quantity - number of columns with such name
       type     - type of the column (int, double, string)
       name     - name of the column - the only required part
       start_index - if quantity is defined set start index for auto-naming

    It is simple! Just look at examples:
    1) 'x  y  z'   -   create 3 columns with names "x", "y", "z". The type is considered to be 'double' by default
    2) 'index=int digit=double descr=string' - create 3 columns: 'index', 'digit' and 'descr' of types int, double and string
    
    Imagine, one needs to create 50 columns for 50 channels?
    3) '50channel'        -  create 50 columns channel0,channel1, ..., channel49. The type is considered to be 'double' by default
    4) '50channel=int'    -  create 50 columns channel0,channel1, ..., channel49 of type (int)
    
    The last one is change start index of auto naming the colums
    5) '50channel1'    -  create 50 columns channel1,channel1, ..., channel50
    6) '3item_15=long - create item_15, item_16, item_17 of type long
       /   \    \   \__________
      /     \    \             \           
 <quantity><name><start_index>=<type> 

    * You can disable quantity logic with --no-quantity flag (see --no-quantity details) 

examples:

    1) mktbl /test/mytable x y z 
       creates in a directory "/test" a table with name "mytable" with 1 row (by default) and 3 columns "x", "y", "z" of type double
    
    2) mktbl /test/mytable -r 2 x y z #"This is comment for my table"
        the same as in first example, but with 2 rows and comment      
    
    3) mktbl /test/table2 5val2=int
       creates in a directory "/test" a table with name "table2" with 5 columns "val2", "val3" ... "val6" of type int.

keys:
    -r <N> or  --rows <N>       Number of rows
    -c <N> or  --columns <N>    Number of columns
    -I     or  --interactive    Interactively ask information that is not provided (rows number, comments)
                                (This option is switched ON by default if ccdbcmd is in interactive mode)
    -nq    or  --no-quantity    if set digits before column names will be NOT treated as quantities
                                i.e  mktbl ... 10val      - creates 10 columns named val0 ... val9
                                     mktbl -nq ... 10val  - creates 1 column named 10val
            """
        
    # print validation table
    #--------------------------
    def print_validation(self):
        #basic values: name rows columns path
        print
        if not len(self.table_name):
            print "Table: " + Theme.Fail + "Name is not set"
        else:
            print "Table: " + Theme.Success +  self.table_name
        
        print "Rows num: " + bool_color(self.rows) + repr(self.rows) + Theme.Reset +\
              "   Columns num: " + bool_color(len(self.columns)) + repr(len(self.columns))
        print "Full path: " + self.table_path
        #columns info 
        print
        print "Columns: "
        print "   (type)    : (name)"
        for colname, coltype in self.columns.items():
            print "   " + Theme.Type + "%-10s"%coltype + Theme.Reset + ": "+ colname
        print 
        #comment
        print "Comment: "
        if len(self.comment):
            print self.comment
        else:
            print Theme.Fail + "Comment is empty"
        
        #additional info print
        print
        print "Additional info: " 
        if self.rows_set:
            print "   Rows number is set by " + Theme.Success + "User"
        else: 
            print "   Rows number is set by " + Theme.Accent + "Default"
            
        if self.comment_set:
            print "   Comments added by " + Theme.Success + "User"
        else:
            print "   No comments are set"
         
        
    def print_settings_summary(self):
        print Theme.Success + " Summary: "
        print "  columns: ", self.columns
        print "  unparsed_columns: ", self.unparsed_columns
        print
        print "    rows            : ", self.rows
        print "    rows_set        : ", bool_color(self.rows_set) + repr(self.rows_set)
        print 
        print "    interactive     : ", bool_color(self.interactive) + repr(self.interactive)
        print "    interactive_set : ", bool_color(self.interactive_set) + repr(self.interactive_set)
        print 
        print "    comment         : ", self.comment 
        print "    comment_set     : ", bool_color(self.comment_set) + repr(self.comment_set)
        print 
        print "    table_name      : ", self.table_name 
        print
        print "    table_path      : ", self.table_path 
        print "    table_path_set  : ", bool_color(self.table_path_set) + repr(self.table_path_set)
        print
        print "    table_parent_path      : ", self.table_parent_path
        
        