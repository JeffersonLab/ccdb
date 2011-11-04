import os, re, os.path, imp, sys
import ccdb.cmd
import logging

#from ccdb.ccdb_pyllapi import MySQLDataProvider
from ccdb.MySQLProvider import MySQLProvider
from Theme import Theme
import colorama
import readline
from Globals import get_verbose, VerboseModes
import posixpath

log = logging.getLogger("ccdb.cmd.ccontext")

class ConsoleContext:
    """
    Class to manage console commands

    This class uses console_utitilities from utils directories

    """
    _utils = {}
    _verbose = VerboseModes.No
    _connectionString = "mysql://ccdb_user@localhost"
    _provider = MySQLProvider()
    _current_path="/"
    anononymous_user_name = "anonymous"
    _user_name = anononymous_user_name
    _is_interactive = False
    _current_run = 0
    prefix = None
    words = []
    _ls = None
    


    def __init__(self):
        self.verbose = get_verbose()
        self._prov = MySQLProvider()
        self._is_interactive = False

    #prop verbose
    #_______________________
    def _get_verbose(self):
        """Sets or gets verbose behaviour for this class"""
        return self._verbose
    
    def _set_verbose(self, isTrue):
        self._verbose = isTrue;
    verbose = property(_get_verbose, _set_verbose)

    @property
    def utils(self):
        return self._utils
    
    @property
    def connection_string(self):
        return self._connectionString

    @connection_string.setter
    def connection_string(self, str):
        self._connectionString = str

    @property
    def provider(self):
        return self._prov

    @property
    def current_path(self):
        return self._current_path

    @current_path.setter
    def current_path(self, newPath):
        self._current_path = newPath
        
    ##property current_run
    #_______________________
    def _get_current_run(self):
        """Sets or gets verbose behaviour for this class"""
        return self._current_run
    
    def _set_current_run(self, isTrue):
        self._current_run = isTrue;
    current_run = property(_get_current_run, _set_current_run)

    @property
    def user_name(self):
        return self._user_name

    @user_name.setter
    def usef_name(self, name):
        self._user_name = name
        self._prov.SetUserName(name)
    
    @property 
    def is_interactive(self):
        return self._is_interactive
    
    @is_interactive.setter
    def is_interactive(self, value):
        self._is_interactive = value
        
    

#=====================================================================================
#------------------ P L U G I N   M A N A G E M E N T  -------------------------------
#=====================================================================================

#--------------------------------
#       
#--------------------------------
    def register_utilities(self, path = None):
        """ Function to auto find and registe utilites"""
        if path == None: path = os.path.join(ccdb.cmd.__path__[0],"utils")
        modules = []
        modules = self.search_utils(path)
        for module in modules:
            try:
                registerFunc = getattr(module, "create_util_instance")
                util = registerFunc()
                if util:
                    self._utils[util.command]=util;
                    util.context = self
                    if util.command == "ls":
                        self._ls = util
            except AttributeError, ex:
                if self.verbose >= VerboseModes.Debug:
                    print "      " + repr(ex)

        if self.verbose >= VerboseModes.Debug:
            print "Utils registred in directory %s are:"%(path,)
            print "%-10s %-15s %s:"%("(command)", "(name)", "(description)")
            print "\n".join(["%-10s %-15s %s" % (command, util.name, util.short_descr) for command, util in self._utils.items()])


#--------------------------------
#       
#--------------------------------            
    def search_utils(self, path):
        """Load plugin from directory and return list of modules"""
        
        #>oO debud output
        if self.verbose >= VerboseModes.Debug:
            print Theme.Title + "searching modules in dircory:"
            print "   " + Theme.Directories + path
        
        #get list of files and module names
        files = os.listdir( path )
        test = re.compile(".py$", re.IGNORECASE)
        files = filter(test.search, files)
        filenameToModuleName = lambda f: os.path.splitext(f)[0]
        moduleNames = sorted(map(filenameToModuleName, files))
        
        modules = []
        for m in moduleNames:
            # skip any files starting with '__', such as __init__.py
            if m.startswith('__'):
                continue
            try:
                f, filename, desc = imp.find_module(m, [path])
                modules.append( imp.load_module(m, f, filename, desc))
            except ImportError, ex:
                if self.verbose >= VerboseModes.Debug:
                    print "error importing module: "
                    print "      " + repr(ex)
                continue

        return modules
    
#--------------------------------
#       
#--------------------------------
    def process(self, args, startIndex=1):

        #check if there is enough argumens...
        if len(args) < (startIndex+1):
            self.print_general_usage()
            return

        #get working arguments list
        workargs=args[startIndex:]

        #parse loop
        i=0
        while i < len(workargs):
            token = workargs[i]
            i+=1

            if token.startswith('-'):
                #it is some command, lets parse what is the command

                if (token == "-c" or token == "--connection") and (i < len(workargs) ):
                    #connection string
                    self.connection_string = workargs[i]
                    i+=1
                    
                elif (token == "-I" or token == "-i" or token == "--interactive"):
                    #it is an interactive mode
                    self._is_interactive = True
                    
                elif (token == "-r" or token == "--run"):
                    #working run
                    try:
                        self.current_run = int(workargs[i])
                        log.info("Working run is %i", self.current_run)
                    except ValueError:
                        log.warning("cannot read run from %s command"%(token))
                    i+=1
            else:
                #looks like is is a command
                command = token;
                commandArgs = workargs[i:]
                return self.process_command(command, commandArgs)
        
        if self._is_interactive:
            self.interactive_loop()
   
#--------------------------------
#       
#--------------------------------        
    def process_command(self, command, commandArgs):
        
        #>oO debug
        if self.verbose >= VerboseModes.Debug:
            print "Processing command: ", command
            print "       commandArgs: "
            print "\n".join(["                   " + arg for arg in commandArgs])
        
        #try to find function...
        util = None
        try:
            util = self._utils[command]
        except KeyError:
            print "command ", command," is unknown! please use help to see avalable commands"


        if not util: return 1;
        
        #check connection and connect if needed
        if util.uses_db and (not self.provider.is_connected):
            if not self.check_connection(util): return False
               
        #execute command
        return util.process(commandArgs)            


#--------------------------------
#       
#--------------------------------       
    def check_connection(self, util):
        if(self.verbose):
            print util.name + " uses the database and there is no connection yet. Trying to connect..."
            print "   Connection string is: " + Theme.Accent, self.connection_string

        if self._prov.is_connected : return #connected anyway...
        
        #connecting
        result = self._prov.connect(self.connection_string)
        if not result:
            #not connected
            print "CCDB provider unable to connect. Aborting command"
            return False
        else:
            #connected
            if(self.verbose):
                print "   Connection " + Theme.Success + " successfull "
            return True
            

#--------------------------------
#       
#--------------------------------
    def interactive_loop(self):
        import shlex
        self.print_interactive_intro()
        #initialise autocomplete
        self.words = self._utils.keys()
        #completer = Completer(words)
        colorama.pause() #make colorama to release stderr and stdout
        readline.parse_and_bind("tab: complete")
        readline.set_completer(self.complete)
        try: 
            readline.read_history_file()
        except:
            pass #eat it
        
        #readline..set_completion_display_matches_hook(self.show_completions)
#readline.set_completion_display_matches_hook([function])
#Set or remove the completion display function. If function is specified, it will be used as the new completion display function; if omitted or None, any completion display function already installed is removed. The completion display function is called as function(substitution, [matches], longest_match_length) once each time matches need to be displayed.
        #begin user commands read loop
        command = ""
        while 1:
            colorama.pause()
            
            # read command from user
            user_input=""
            try:
                user_input=raw_input( self.current_path +"> ")
            except EOFError:
                if self.verbose: print "EOF sequence recieved. Ending interactive loop"
                break
            except KeyboardInterrupt:
                if self.verbose: print "Break sequence recieved. Ending interactive loop"
                break
                                
            # exit if user wishes so    
            if user_input in ("quit", "q", "exit"):
                break #quit!
            
            # execute shell command if input starts with '!'
            if user_input.startswith('!'):
                user_input = user_input[1:]
                try:     
                    os.system(user_input)
                except:
                    pass
                continue #skip to next command     
                                   
                    
            tokens = shlex.split(user_input)
            
            if len(tokens) > 0:
                command = tokens[0]
                
                if self.verbose >= VerboseModes.Debug:
                    print "command is : ", command
                    print tokens
                
                arguments = []
                if len(tokens) > 1:
                    arguments = tokens[1:]
                
                colorama.resume()
                
                self.process_command(command, arguments)
        #loop ended
        try:
            readline.write_history_file()
        except:
            log.warn("unable to write history file")


#=====================================================================================
#------------------------ C O M P L E T I O N ----------------------------------------
#=====================================================================================
        
#--------------------------------
# show_completions      
#-------------------------------- 
    def show_completions(self, substitution, matches, longest_match_length):
        print self
        print substitution
        print matches
        print longest_match_length


#--------------------------------
# generate_completition_words      
#--------------------------------     
    def generate_completition_words(self, prefix):
        
        # find all words that start with this prefix
        self.matching_words = [  w 
                                 for w in self.words 
                                 if w.startswith(prefix)]
        
        #get name pathes
        try:
            self.check_connection(self._ls)
            result = self._ls.get_name_pathes(prefix)
            
            if result == None or (len(result[0]) ==0 and len(result[1])==0):
                result = self._ls.get_name_pathes(prefix + "*")    
                if result == None : return;
            self.matching_words.extend(result[0])
            self.matching_words.extend(result[1])
            
        except Exception as ex:
            log.debug("error getting completition paths: " + ex.message)
        
    
    
#--------------------------------
#       complete
#--------------------------------        
    def complete(self, prefix, index):
       
        #print "prefix ", prefix, "  index ", index
        #readline.insert_text("bla bla bla")
        #colorama.resume()
        #print "ha ha ha"
        #colorama.pause()
        
        if prefix != self.prefix:
            #get new completions
            self.generate_completition_words(prefix)
            
            #self.matching_words.append(
            self.prefix = prefix
            
        else:
            
            #print  "prefix the same, matching:", len(self.matching_words)
            
            #print "  ".join([word for word in self.matching_words])
            #readline.redisplay()
            pass
            
        try:
            return self.matching_words[index]
        except IndexError:
            return None


#=====================================================================================
#--------  G E T T I N G    O B J E C T S  -------------------------------------------
#=====================================================================================

#--------------------------------
#  prepare_path      
#--------------------------------
    def prepare_path(self, path):
        
        #correct ending /
        if path.endswith("/"):
            path = path[:-1]

        #local or absolute path?
        if not path.startswith("/"):
            path = posixpath.join(self.current_path , path)
        #normalize
        path = posixpath.normpath(path)
        
        return path


#--------------------------------
#  parse_run_range  
#--------------------------------    
    def parse_run_range(self, run_range_str):
        """ @brief parse run range string in form of <run_min>-<run-max>

            if one inputs '<run_min>-' this means <run_min>-<infinit run>
            if one inputs '-<run_max>' this means <0>-<run_max> 

            @return (run_min, run_max, run_min_set, run_max_set)
            run_min_set, run_max_set - are flags indicating that values was set by user
            """

        assert isinstance(run_range_str, str)
        if not "-" in run_range_str:
            return None
        
        #split <>-<>     
        (str_min, str_max) = run_range_str.split("-")   
        run_min = 0
        run_min_set = False
        run_max = ccdb.INFINITE_RUN
        run_max_set = False
        
        #parse run min 
        try:
            run_min = int(str_min)
            run_min_set = True
        except ValueError as error:
            self.run_min = 0
        
        #parse run max 
        try:
            run_max = int(str_max)
            run_max_set = True
        except ValueError as error:
            self.run_max = ccdb.INFINITE_RUN
        
        return (run_min,  run_max, run_min_set, run_max_set)


#=====================================================================================
#------------------------- H E L P   A N D   I N F O ---------------------------------
#=====================================================================================


    def print_general_usage(self):
        print "Use '-i'   option to enter interactive shell"
        print "Use 'help' option for help"
        print "Use 'help command' to get help for particular command"


    def print_interactive_intro(self):
        print """
+--------------------------+
  CCDB shell v.0.1.2
  HallD JLab
+--------------------------+
       """
        print Theme.Title + "Interactive mode"
        print "print " + Theme.Accent + "help" + Theme.Reset + " to get help"
        print "print " + Theme.Accent + "quit" + Theme.Reset + " or " + Theme.Accent + "q" + Theme.Reset +" to exit"
        print "print !<command> to execute shell command"
        print
        
        
                
                    





