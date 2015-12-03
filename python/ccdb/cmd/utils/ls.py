import posixpath
import logging
import os

from ccdb.errors import DirectoryNotFound
from ccdb.model import Directory, TypeTable
from ccdb.provider import AlchemyProvider
from ccdb.cmd import ConsoleUtilBase, UtilityArgumentParser
from ccdb import BraceMessage as LogFmt

log = logging.getLogger("ccdb.cmd.utils.ls")

#ccdbcmd module interface
def create_util_instance():
    log.debug("      registering ListUtil")
    return List()


#*********************************************************************
#   Class List - List objects in a given directory                   *
#                                                                    *
#*********************************************************************
class List(ConsoleUtilBase):
    """ List objects in a given directory """

    # ccdb utility class descr part 
    #------------------------------
    command = "ls"
    name = "List"
    short_descr = "List objects in a given directory"
    uses_db = True

    def __init__(self):
        ConsoleUtilBase.__init__(self)
        self.raw_entry = "/"  # object path with possible pattern, like /mole/*
        self.parent_path = "/"  # parent path
        self.parent_dir = None  # @type parent_dir DDirectory
        self.pattern = ""  # pattern on the end of parent path like file?*
        self.is_extended = False

    def reset(self):
        """Resets variables for each 'process'"""
        self.raw_entry = "/"  # object path with possible pattern, like /mole/*
        self.parent_path = "/"  # parent path
        self.parent_dir = None  # @type parent_dir DDirectory
        self.pattern = ""  # pattern on the end of parent path like file?*
        self.is_extended = False


    def process(self, args):
        if log.isEnabledFor(logging.DEBUG):
            log.debug(LogFmt("{0}List is in charge{0}\\".format(os.linesep)))
            log.debug(LogFmt(" |- arguments : '" + "' '".join(args) + "'"))

        assert self.context is not None
        provider = self.context.provider
        assert isinstance(provider, AlchemyProvider)
        self.reset()

        #PARSE ARGUMENTS
        #-------------------------------
        raw_path, task, is_extended = self._process_arguments(args)

        #dump as tree
        if task == ListTasks.directory_tree:
            self.parent_dir = provider.get_root_directory()
            self.print_directory_tree(self.parent_dir, False, 0)
            return

        #dump as directories
        if task == ListTasks.directories:
            self.parent_dir = provider.get_root_directory()
            self.print_directory_tree(self.parent_dir, True, 0)
            return

        #dump variations
        if task == ListTasks.variations:
            self.print_variations()
            return

        #dump type_tables
        if task == ListTasks.type_tables:
            self.print_tables()
            return

        if len(args) > 0:
            self.raw_entry = raw_path
        else:
            self.raw_entry = self.context.current_path



        dirs, tables = self.get_name_pathes(self.raw_entry)

        if (not dirs) and (not tables):
            log.info("Can't find the directory or tables")

        # it is not a wild card search, and
        if ("*" not in self.raw_entry) and\
           ("?" not in self.raw_entry) and\
           (not dirs) and\
           (len(tables) == 1):
            self.table_info(tables[0], is_extended)
            return

        for directory in dirs:
            log.info(self.theme.Directories + directory.name + self.theme.Reset)

        for table in tables:
            log.info(table.name)

    @staticmethod
    def _process_arguments(args):
        # solo arguments

        # utility argument parser is argparse which raises errors instead of exiting app
        parser = UtilityArgumentParser()
        parser.add_argument("raw_path", nargs='?', default="")
        parser.add_argument("-x", "--dtree", action="store_true")
        parser.add_argument("-d", "--directories", action="store_true")
        parser.add_argument("-t", "--tables", action="store_true")
        parser.add_argument("-v", "--variations", action="store_true")
        parser.add_argument("-l", "--extended", action="store_true")

        result = parser.parse_args(args)

        if result.variations:
            task = ListTasks.variations
        elif result.directories:
            task = ListTasks.directories
        elif result.dtree:
            task = ListTasks.directory_tree
        elif result.tables:
            task = ListTasks.type_tables
        else:
            task = ListTasks.default

        log.debug(LogFmt(" |- parsed as (obj: '{0}', type: '{1}')", result.raw_path, task))

        return result.raw_path, task, result.extended

    def get_name_pathes(self, path):
        assert self.context is not None
        provider = self.context.provider
        assert isinstance(provider, AlchemyProvider)
        self.reset()

        #prepare path
        log.debug(" |  |- ls.get_name_pathes")
        log.debug(" |  | \\")
        log.debug(" |  |  |- before prepare_path: " + path)

        self.raw_entry = self.prepare_path(path)
        log.debug(" |  |  |- after prepare_path:  " + self.raw_entry)

        #SEARCH LOGIC
        #---------------------------

        #brute assumption that user has entered a simple dir path
        try:
            self.parent_dir = provider.get_directory(self.raw_entry)
            self.parent_path = self.raw_entry
            self.pattern = ""
        except DirectoryNotFound:
            self.parent_dir = None
            log.debug(" |  |  |- directory {0} not found.".format(self.raw_entry))

        if not self.parent_dir:
            #we have not find the directory by brute rawentry.
            #but maybe it is just /path/plus*some*pattern
            (head, tale) = posixpath.split(self.raw_entry)
            self.parent_path = head
            self.pattern = tale
            log.debug(" |  |  |- searching parent directory as:")
            log.debug(" |  |  |- new path: " + self.parent_path)
            if self.pattern:
                log.debug(" |  |  |- pattern: " + self.pattern)

            #try to find such dir once more
            self.parent_dir = provider.get_directory(self.parent_path)

        #found a directory
        assert isinstance(self.parent_dir, Directory)
        log.debug(" |  |  |- searching sub directories ")
        log.debug(" |  |  |- full path: " + self.parent_dir.path)
        if self.pattern:
            log.debug(" |  |  |- pattern: " + self.pattern)

        #part 1 directories for this path
        if self.pattern == "":
            sub_dirs = self.parent_dir.sub_dirs
            log.debug(" |  |  |- simply taking sub directories ")
        else:
            sub_dirs = provider.search_directories(self.pattern, self.parent_path)
            log.debug(" |  |  |- use database search for directories ")

        #fill list of directory names
        dir_list = [subdir.name for subdir in sub_dirs]

        log.debug(" |  |  |- found dirs:" + " ".join([d for d in dir_list]))

        log.debug(" |  |  |- searching tables ")
        #part 2 is tables for this path
        if self.pattern == "":
            tables = self.context.provider.get_type_tables(self.parent_dir)
        else:
            tables = self.context.provider.search_type_tables(self.pattern, self.parent_path)

        return sub_dirs, tables

    def prepare_path(self, path):
        """
        prepares path:
            makes path absolute if it is relative
            removes path artifacts like / in the end, /../ in the middle etc.

        :param path: raw uncoocked path
        :type path: str
        :return: Well done path
        :rtype: str
        """
        # correct ending /

        if path.endswith("/"):
            path = path[:-1]

        #local or absolute path?
        if not path.startswith("/"):
            path = posixpath.join(self.context.current_path, path)

        #normalize
        path = posixpath.normpath(path)

        return path

    def print_directory_tree(self, directory, printFullPath, level):
        """prints a full tree of directories
            This is recursive function"""

        #print this directory
        if not printFullPath:
            print "".join(["   " for i in range(0, level)]) + directory.name
        else:
            print directory.path

        #print subdirectories recursively
        sub_dirs = directory.sub_dirs
        if len(sub_dirs) > 0:
            for subDir in sub_dirs:
                self.print_directory_tree(subDir, printFullPath, level + 1)

    def print_variations(self):
        default_variation = self.context.provider.get_variation("default")
        print( self._get_variation_tree_str(default_variation) )

    def _get_variation_tree_str(self, variation, level=0):
        ret = "  "*level + str(variation.name)+"\n"
        for child in variation.children:
            ret += self._get_variation_tree_str(child, level+1)
        return ret

    def print_tables(self):
        tables = self.context.provider.search_type_tables("*")
        for table in tables:
            assert (isinstance(table, TypeTable))
            print(table.path)

    def table_info(self, table, is_extended):
        log.info(table.path)
        if is_extended:
            self.context.process_command("info", [table.path])
        self.context.process_command("vers", [table.path])

    def print_help(self):
        """Prints help of the command"""

        print """
Lists directories and tables for current directory

- Accepts wildcards symbols '*', and '?'

- When used on single table name, gives table data version as 'vers <table name>' command
  note(!): vers command allows you to filter data by variation or run, ls - not

keys:
    -v or --variations   - prints all variations
    -t or --tables       - prints full path for all tables
    -d or --directories  - prints all directories
    -x or --dtree        - draws directory tree

    -l or --extended     - shows extended info when is used on table
"""


class ListTasks(object):
    default = "default"
    variations = "variations"
    type_tables = "type_tables"
    directories = "directories"
    directory_tree = "directory_tree"





