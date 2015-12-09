import logging
import os

from ccdb import Directory, TypeTable, Variation, read_ccdb_text_file, TextFileDOM
from ccdb.cmd import ConsoleUtilBase, UtilityArgumentParser
from ccdb import AlchemyProvider
from ccdb import BraceMessage as LogFmt


log = logging.getLogger("ccdb.cmd.utils.info")


#ccdbcmd module interface
def create_util_instance():
    log.debug("      registering Info")
    return Info()


#*********************************************************************
#   Class Info - Prints extended information of object by the path   *
#                                                                    *
#*********************************************************************
class Info(ConsoleUtilBase):
    """ Prints extended information of object by the path """

    # ccdb utility class descr part 
    #------------------------------
    command = "info"
    name = "Info"
    short_descr = "Prints extended information of object by the path"
    uses_db = True

    #----------------------------------------
    #   process
    #----------------------------------------
    def process(self, args):
        if log.isEnabledFor(logging.DEBUG):
            log.debug(LogFmt("{0}Info is in charge{0}\\".format(os.linesep)))
            log.debug(LogFmt(" |- arguments : '" + "' '".join(args) + "'"))

        assert self.context
        provider = self.context.provider
        assert isinstance(provider, AlchemyProvider)

        #process arguments
        obj_name, obj_type = self._process_arguments(args)
        path = self.context.prepare_path(obj_name)  # more likely obj_name is path to dir or table

        if not obj_name:
            log.warning("No path or name is given. Use 'help info' for getting help.")

        #it is a type table
        if obj_type == InfoTypes.type_table:
            self.print_type_table(provider.get_type_table(path))

        #it is a directory
        if obj_type == InfoTypes.directory:
            self.print_directory(provider.get_directory(path))

        #it is a variation
        if obj_type == InfoTypes.variation:
            self.print_variation(provider.get_variation(obj_name))

        #it is a file!!!
        if obj_type == InfoTypes.file:
            self.print_file(obj_name)

        #everything is fine!
        return 0

    #----------------------------------------
    #   process_arguments
    #----------------------------------------

    @staticmethod
    def _process_arguments(args):
        #solo arguments

        #utility argument parser is argparse which raises errors instead of exiting app
        parser = UtilityArgumentParser()
        parser.add_argument("obj_name", default="")
        parser.add_argument("-v", "--variation", action="store_true")
        parser.add_argument("-d", "--directory", action="store_true")
        parser.add_argument("-f", "--file", action="store_true")

        result = parser.parse_args(args)

        if result.variation:
            obj_type = InfoTypes.variation
        elif result.directory:
            obj_type = InfoTypes.directory
        elif result.file:
            obj_type = InfoTypes.file
        else:
            obj_type = InfoTypes.type_table

        log.debug(LogFmt(" |- parsed as (obj: '{0}', type: '{1}')", result.obj_name, obj_type))

        return result.obj_name, obj_type

    # ----------------------------------------
    #   print_directory
    # ----------------------------------------
    def print_directory(self, directory):
        assert isinstance(directory, Directory)
        print " Name      :  " + self.theme.Success + directory.name
        print " Full path :  " + directory.path
        try:
            print " Created   :  " + directory.created.strftime("%Y-%m-%d %H-%M-%S")
        except Exception as ex:
            log.warning("Directory created time getting error: " + str(ex))
        try:
            print " Modified  :  " + directory.modified.strftime("%Y-%m-%d %H-%M-%S")
        except Exception as ex:
            log.warning("Directory modify time getting error: " + str(ex))

        #comment
        print " Comment: "
        print directory.comment
        print

    #----------------------------------------
    #   print_type_table
    #----------------------------------------
    def print_type_table(self, table):
        #basic values: name rows columns path
        assert isinstance(table, TypeTable)
        print "+------------------------------------------+"
        print "| Type table information                   |"
        print "+------------------------------------------+"
        print " Name       :  " + self.theme.Success + table.name
        print " Full path  :  " + table.path
        print " Rows       :  " + self.theme.Accent + repr(int(table.rows_count))
        print " Columns    :  " + self.theme.Accent + repr(int(table.columns_count))
        print " Created    :  " + table.created.strftime("%Y-%m-%d %H-%M-%S")
        print " Modified   :  " + table.modified.strftime("%Y-%m-%d %H-%M-%S")
        print " DB Id      :  " + repr(int(table.id))
        print "+------------------------------------------+"
        print "| Columns info                             |"
        print "+------------------------------------------+"
        #columns info 
        print
        print "Columns info "
        print " N.   (type)    : (name)"
        for column in table.columns:
            print " " + repr(int(column.order)).ljust(4) \
                  + " " + self.theme.Type + "%-10s" % column.type + self.theme.Reset + ": " + column.name

        print
        print "+------------------------------------------+"
        #comment
        print "Comment: "
        print table.comment
        print

    #----------------------------------------
    #   print_variation
    #----------------------------------------
    def print_variation(self, variation):
        #basic values: name rows columns path
        assert isinstance(variation, Variation)
        print "+------------------------------------------+"
        print "| Variation information                    |"
        print "+------------------------------------------+"
        print " Name       :  " + self.theme.Success + variation.name
        print " Created    :  " + variation.created.strftime("%Y-%m-%d %H-%M-%S")
        print " DB Id      :  " + repr(int(variation.id))
        print " Parent     :  " + (variation.parent.name if variation.parent else "--")
        print " Comment:  "
        print variation.comment
        print

    #----------------------------------------
    #   print_help
    #----------------------------------------
    def print_help(self):
        """Prints help of the command"""

        print """Prints extended info about the object
    info <type table path>   - info about type table with given path
    info -d <directory path> - info about directory with given path
    info -v <variation name> - info about variation with given name
    info -f <file name>      - info about text file (col. names), rows, etc.
    
    """

    def print_file(self, file_path):
        #reading file
        try:
            dom = read_ccdb_text_file(file_path)
        except IOError as error:
            log.warning(LogFmt("Unable to read file '{0}'. The error message is: '{1}'", file_path, error))
            raise

        #Is there data at all?
        if not dom.has_data:
            message = "Seems like file has no data"
            log.warning(message)
            raise ValueError(message=message)

        #check what we've got
        assert isinstance(dom, TextFileDOM)
        if not dom.data_is_consistent:
            message = "Inconsistency error. " + dom.inconsistent_reason
            log.warning(message)
            raise ValueError(message=message)

        log.info(LogFmt("Rows: {}{}{}", self.theme.Accent, len(dom.rows), self.theme.Reset))
        log.info(LogFmt("Columns: {}{}{}", self.theme.Accent, len(dom.rows[0]), self.theme.Reset))


        #column names
        if dom.column_names:
            log.info("Column names:")
            log.info("    " + (os.linesep + "    ").join(
                [self.theme.Accent + col_name + self.theme.Reset for col_name in dom.column_names]))
        else:
            log.info("No column names found (column name string starts with #&)")

        #meta data
        if dom.metas:
            log.info("Meta data:")
            log.info((os.linesep + "    ").join([key + " = " + val for key, val in dom.metas]))

        #comments
        if dom.comment_lines:
            log.info(LogFmt("{0}Comments in file: {0}{1}", os.linesep, os.linesep.join(ln for ln in dom.comment_lines)))
        else:
            log.info("No comments in file found")

        ccdb_prefix = "ccdb " if not self.context.is_interactive else ""
        log.info("")
        log.info(LogFmt("Type '{1}mktbl -f {0}' to see how to create a table for the file", file_path, ccdb_prefix))
        log.info(LogFmt("Type '{1}add <table name> {0} #<comments>' to add the file to existing table"
                        " (rows and columns must consist)", file_path, ccdb_prefix))


class InfoTypes(object):
    variation = "variation"
    type_table = "type_table"
    directory = "directory"
    file = "file"
