import posixpath
import logging
from ccdb.errors import DirectoryNotFound

from ccdb.model import Directory, TypeTable
from ccdb.provider import AlchemyProvider
from ccdb.cmd import ConsoleUtilBase


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
        self.reset()

    def reset(self):
        """Resets variables for each 'process'"""
        self.raw_entry = "/"       #object path with possible pattern, like /mole/*
        self.parent_path = "/"    #parent path
        self.parent_dir = None    # @type parent_dir DDirectory
        self.pattern = ""         #pattern on the end of parent path like file?*


    def process(self, args):
        log.debug("ListUtil gained control")
        log.debug("Arguments: " + " ".join(args))
        
        assert self.context is not None
        provider = self.context.provider
        assert isinstance(provider, AlchemyProvider)
        self.reset()

        #PARSE ARGUMENTS
        #-------------------------------

        #dump as tree
        if "--dump-tree" in args:
            self.parent_dir = provider.get_root_directory()
            self.print_directory_tree(self.parent_dir, False, 0)
            return

        #dump as dump
        if "--dump" in args:
            self.parent_dir = provider.get_root_directory()
            self.print_directory_tree(self.parent_dir, True, 0)
            return

        #dump variations
        if "-v" in args or "--variations" in args:
            self.print_variations()
            return

        #dump type_tables
        if "-t" in args or "--tables" in args:
            self.print_tables()
            return

        if len(args) > 0:
            self.raw_entry = args[0]
        else:
            self.raw_entry = self.context.current_path

        #prepare path
        self.raw_entry = self.prepare_path(self.raw_entry)
        
        #SEARCH LOGIC

        #brute assumption that user has entered a simple dir path
        try:
            self.parent_dir = provider.get_directory(self.raw_entry)
        except KeyError:
            #we have not find the directory by brute rawentry.
            #but maybe it is just /path/plus*some*pattern
            (head, tale) = posixpath.split(self.raw_entry)
            self.parent_path = head
            self.pattern = tale

            #try to find such dir once more
            try:
                self.parent_dir = provider.get_directory(self.parent_path)
            except KeyError:
                self.parent_dir = None

        #found a directory
        if self.parent_dir:
            assert isinstance(self.parent_dir, Directory)

            #>oO debug
            log.debug("  path: {0}".format(self.parent_path))
            if len(self.pattern): log.debug("  pattern: {0}".format(self.pattern))
            
            #part 1 directories for this path
            sub_dirs = []
            if self.pattern == "":
                sub_dirs = self.parent_dir.sub_dirs
            else:
                sub_dirs = self.context.provider.search_directories(self.pattern, self.parent_path)
           
            for subdir in sub_dirs:
                print self.theme.Directories + subdir.name + "    "
            
            #part 2 is tables for this path
            tables = []
            if self.pattern == "":
                tables = self.context.provider.get_type_tables(self.parent_dir)
            else:
                tables = self.context.provider.search_type_tables(self.pattern, self.parent_path)
                        
            for table in tables:
                print table.name
            print
        else:
            print "Can't find the directory"


    def get_name_pathes(self, path):
        assert self.context is not None
        provider = self.context.provider
        assert isinstance(provider, AlchemyProvider)
        self.reset()

        self.raw_entry = path
        #prepare path
        log.debug(" |  |- ls.get_name_pathes")
        log.debug(" |  | \\")
        log.debug(" |  |  |- before prepare_path: " + self.raw_entry)

        self.raw_entry = self.prepare_path(self.raw_entry)
        log.debug("   get_name_pathes=>  after prepare_path:  " + self.raw_entry)
        
        #SEARCH LOGIC
        #---------------------------

        #brute assumption that user has entered a simple dir path
        try:
            self.parent_dir = provider.get_directory(self.raw_entry)
            self.parent_path = self.raw_entry
            self.pattern = ""
        except KeyError:
            self.parent_dir = None
            log.debug("   get_name_pathes=>  directory {0} not found.".format(self.raw_entry))
        except DirectoryNotFound:
            self.parent_dir = None
            log.debug("   here_we_are=>  directory {0} not found.".format(self.raw_entry))

        if not self.parent_dir:
            #we have not find the directory by brute rawentry.
            #but maybe it is just /path/plus*some*pattern
            (head, tale) = posixpath.split(self.raw_entry)
            self.parent_path = head
            self.pattern = tale
            log.debug("   get_name_pathes=>  searching parent directory as:")
            log.debug("   get_name_pathes=>  new path: " + self.parent_path)
            if len(self.pattern): log.debug("   get_name_pathes=> pattern: " + self.pattern)

            #try to find such dir once more
            self.parent_dir = provider.get_directory(self.parent_path)

        #found a directory
        assert isinstance(self.parent_dir, Directory)
        log.debug("   get_name_pathes=>  searching subdirectoris ")
        log.debug("   get_name_pathes=>  full path: " +self.parent_dir.path)
        if len(self.pattern): log.debug("    get_name_pathes=> pattern: " + self.pattern)

        #part 1 directories for this path
        if self.pattern == "":
            sub_dirs = self.parent_dir.sub_dirs
        else:
            sub_dirs = provider.search_directories(self.pattern, self.parent_path)

        #fill list of directory names
        dir_list = [subdir.name for subdir in sub_dirs]

        log.debug("   get_name_pathes=>  found dirs:" + " ".join([d for d in dir_list]))

        log.debug("   get_name_pathes=>  searching tables ")
        #part 2 is tables for this path
        tables = []
        if self.pattern == "":
            tables = self.context.provider.get_type_tables(self.parent_dir)
        else:
            tables = self.context.provider.search_type_tables(self.pattern, self.parent_path)

        #fill list of tables
        table_list=[table.name for table in tables]

        return dir_list, table_list


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
        #correct ending /

        if path.endswith("/"):
            path = path[:-1]

        #local or absolute path?
        if not path.startswith("/"):
            path = posixpath.join(self.context.current_path , path)

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
        if len(sub_dirs)>0:
            for subDir in sub_dirs:
                self.print_directory_tree(subDir, printFullPath, level+1)

    def print_variations(self):
        variations = self.context.provider.get_variations()
        for var in variations:
            print var.name
            #TODO more sophisticated output

    def print_tables(self):
        tables = self.context.provider.search_type_tables("*")
        for table in tables:
            assert (isinstance(table, TypeTable))
            print(str(table.parent_dir.path)+"==>"+table.path)

    def print_help(self):
        "Prints help of the command"
        print """
Displays directories and tables for current directory

keys:
    -v or --variations - prints all variations
    -t or --tables     - prints full path for all tables
          --dump       - prints all directories
          --dump-tree  - draws directory tree
"""





