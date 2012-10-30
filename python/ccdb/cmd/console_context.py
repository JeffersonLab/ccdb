import os, re, imp, sys
import ccdb.cmd
import logging
import shlex
import posixpath

from ccdb.brace_log_message import BraceMessage as lfm
from ccdb import AlchemyProvider
import themes

import colorama
import readline

log = logging.getLogger("ccdb.cmd.console_context")

class ConsoleContext:
    """
    Class to manage console commands

    This class uses console_utitilities from utils directories

    """

    anonymous_user_name = "anonymous"
    prefix = None
    words = []
    theme = themes.NoColorTheme

    def __init__(self):
        self._prov = AlchemyProvider()
        self._is_interactive = False
        self._user_name = self.anonymous_user_name
        self._is_interactive = False
        self._current_run = 0
        self._utils = {}
        self._current_path="/"
        self._ls=None
        self._connection_string = ""
        self.silent_exceptions = True #rethrow happened exceptions

    #prop verbose
    #_______________________
    def _get_verbose(self):
        """Sets or gets verbose behaviour for this class"""
        return self._verbose
    
    def _set_verbose(self, isTrue):
        self._verbose = isTrue
    verbose = property(_get_verbose, _set_verbose)

    @property
    def utils(self):
        """:rtype: {}"""
        return self._utils
    
    @property
    def connection_string(self):
        return self._connection_string

    @connection_string.setter
    def connection_string(self, str):
        self._connection_string = str

    @property
    def provider(self):
        return self._prov

    @property
    def current_path(self):
        return self._current_path

    @current_path.setter
    def current_path(self, newPath):
        self._current_path = newPath

    @property
    def current_run(self):
        """
        Sets or gets verbose behaviour for this class
        :rtype: int
        """
        return self._current_run

    @current_run.setter
    def current_run(self, new_run):
        self._current_run = new_run


    @property
    def user_name(self):
        return self._user_name

    @user_name.setter
    def user_name(self, name):
        self._user_name = name
        self._prov.log_user_name = name
    
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
    #  register_utilities
    #--------------------------------
    def register_utilities(self, path = ""):
        """ Function to auto find and register utilities"""
        if path == "": path = os.path.join(ccdb.cmd.__path__[0],"utils")

        #search modules
        modules = self.search_utils(path)
        self._utils = {}

        #register each module
        for module in modules:
            try:
                registerFunc = getattr(module, "create_util_instance")
                util = registerFunc()
                if util:
                    self._utils[util.command]=util
                    util.context = self
                    util.theme = self.theme
                    if util.command == "ls":
                        self._ls = util

            except AttributeError, ex: log.debug("Error registering module : " + repr(ex))
            except Exception as ex:    log.debug("Error registering module : " + repr(ex))

        log.debug("Utils found and registered in directory {0} are:".format(path))
        log.debug("%-10s %-15s %s:"%("(command)", "(name)", "(description)"))
        log.debug("\n".join(["%-10s %-15s %s" % (command, util.name, util.short_descr) for command, util in self._utils.items()]))


    #--------------------------------
    # search_utils
    #--------------------------------
    def search_utils(self, path):
        """Load plugins from directory and return list of modules

        :rtype: []
        """
        
        #>oO debud output
        log.debug(lfm("{0}search_utils{0}\\",os.linesep))
        log.debug(" |- searching modules in directory:")
        log.debug(" |   " + self.theme.Directories + path + self.theme.Reset)

        #get list of files and module names
        files = os.listdir( path )
        test = re.compile(".py$", re.IGNORECASE)
        files = filter(test.search, files)
        filenameToModuleName = lambda f: os.path.splitext(f)[0]
        moduleNames = sorted(map(filenameToModuleName, files))
        log.debug(lfm(" |- found '{0}' modules.{1} |- proceed loading each module {1}\\",len(moduleNames), os.linesep))
        
        modules = []
        for m in moduleNames:
            # skip any files starting with '__', such as __init__.py
            if m.startswith('__'):
                continue
            try:
                f, filename, desc = imp.find_module(m, [path])
                modules.append( imp.load_module(m, f, filename, desc))
            except ImportError, ex:
                log.debug(lfm(" |- error importing module: {0}", m))
                log.debug(lfm(" |\\{0} ||-{1}", os.linesep, repr(ex)))
                continue

        return modules


    #--------------------------------
    #
    #--------------------------------
    def process(self, args, startIndex=1):

        #check if there is enough arguments...
        if len(args) < (startIndex+1):
            self.print_general_usage()
            return

        #get working arguments list
        workargs=args[startIndex:]

        #parse loop
        i=0
        while i < len(workargs):
            token = workargs[i]
            assert isinstance(token, str)
            i+=1

            if token.startswith('-'):
                #it is some command, lets parse what is the command

                if (token == "-c" or token == "--connection") and (i < len(workargs) ):
                    #connection string
                    self.connection_string = workargs[i]
                    i+=1
                    
                elif token == "-I" or token == "-i" or token == "--interactive":
                    #it is an interactive mode
                    self._is_interactive = True
                    
                elif token == "-r" or token == "--run":
                    #working run
                    try:
                        self.current_run = int(workargs[i])
                        log.info("Working run is %i", self.current_run)
                    except ValueError:
                        log.warning("cannot read run from %s command"% token)
                    i+=1
            else:
                #looks like is is a command
                command = token
                commandArgs = workargs[i:]
                try:
                    return self.process_command(command, commandArgs)
                except Exception as ex:
                    log.error(ex)
                    if not self.silent_exceptions: raise
                    else: return 1
        
        if self._is_interactive:
            self.interactive_loop()


    #--------------------------------
    #   executes text as command
    #--------------------------------
    def process_command_line(self, command_line):
        """tries to execute a line of text"""

        log.debug("{0}Process command line: {1}{0}\\".format(os.linesep, command_line))

        # execute shell command if input starts with '!'
        if command_line.startswith('!'):
            command_line = command_line[1:]
            #noinspection PyBroadException
            try:
                os.system(command_line)
            except:
                pass
            return #all is done  
                                   
        #split command to arguments
        tokens = shlex.split(command_line)

        #validate
        if len(tokens) == 0: return;

        #get our command
        command = tokens[0]
        log.debug(" |- command is : {0}".format(command))
        log.debug(" |- tokens : {0}".format(" ".join([ ("'"+t+"'") for t in tokens])))

        #is there file redirect?
        redir_to_file = False  #should we redirect to file?
        redir_file = None      #file to redirect
        redir_stream_backup = sys.stdout
        redir_theme_backup = self.theme

        if ">" in tokens and tokens.index(">") == len(tokens) - 2:
            redir_fname = tokens[-1]
            redir_to_file = True
            tokens = tokens[:-2]
            log.debug(" |- redirecting to file : {0}".format(redir_fname))

            #open file
            try:
                redir_file = file(redir_fname, 'w')
            except Exception as ex:
                log.error("Cannot open file '{0}' {1} ".format(redir_fname, ex))
                if not self.silent_exceptions: raise
                else: return 1



        #get command arguments
        arguments = []
        if len(tokens) > 1:
            arguments = tokens[1:]

        #execute everything
        try:
            if redir_to_file:
                sys.stdout = redir_file
                colorama.deinit()
                self.theme = themes.NoColorTheme
            return self.process_command(command, arguments)
        except Exception as ex:
            log.error(ex)
            if not self.silent_exceptions: raise
            else: return 1
        finally:
            if redir_to_file:
                sys.stdout = redir_stream_backup
                redir_file.close()
                self.theme = redir_theme_backup
                colorama.reinit()


    #--------------------------------
    #
    #--------------------------------
    def process_command(self, command, commandArgs):
        
        #>oO debug
        log.debug("Processing command: {0}".format(command))
        log.debug("       commandArgs: ")
        log.debug(" ".join(["                   " + arg for arg in commandArgs]))
        
        #try to find function...
        util = None
        try:
            util = self._utils[command]
        except KeyError:
            print "Command ", command," is unknown! Please, use help to see avalable commands"


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
        if self._prov.is_connected : return #connected anyway...
        log.debug(util.name + " uses the database and there is no connection yet. Trying to connect...")
        log.debug("   Connection string is: " + self.theme.Accent + self.connection_string + self.theme.Reset)

        #connecting
        try:
            self._prov.connect(self.connection_string)
        except Exception as ex:
            log.critical("CCDB provider unable to connect to {0}. Aborting command. Exception details: {1}".format(self.connection_string, ex))
            return False

        #connected
        log.debug("   Connection " + self.theme.Success + " successfull " + self.theme.Reset)
        return True
            

    #----------------------------------------------------
    #       interactive_loop
    #----------------------------------------------------
    #noinspection PyBroadException
    def interactive_loop(self):
        self.print_interactive_intro()
        #initialise autocomplete
        self.words = self._utils.keys()
        #completer = Completer(words)
        colorama.deinit() #make colorama to release stderr and stdout
        readline.parse_and_bind("tab: complete")
        readline.set_completer(self.complete)
        try: 
            readline.read_history_file()
        except:
            pass #eat it
        
        #readline..set_completion_display_matches_hook(self.show_completions)
        #readline.set_completion_display_matches_hook([function])

        #Set or remove the completion display function. If function is specified, it will be used as the new completion
        # display function; if omitted or None, any completion display function already installed is removed. The completion
        # display function is called as function(substitution, [matches], longest_match_length) once each time matches need
        # to be displayed.
        # Begin user commands read loop
        while 1:
            colorama.deinit()
            
            # read command from user
            try:
                user_input=raw_input( self.current_path +"> ")
            except EOFError:
                log.debug("EOF sequence received. Ending interactive loop")
                break
            except KeyboardInterrupt:
                log.debug("Break sequence received. Ending interactive loop")
                break

            colorama.reinit()
                                
            # exit if user wishes so    
            if user_input in ("quit", "q", "exit"):
                break #quit!
            
            #process user input
            self.process_command_line(user_input)            
            
        #loop ended
        try:
            readline.write_history_file()
        except:
            log.warn("unable to write history file")


#=====================================================================================
#------------------------ C O M P L E T I O N ----------------------------------------
#=====================================================================================
    #region Description

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
        self.matching_words = [w for w in self.words if w.startswith(prefix)]


        #get name patches
        path_prefix = posixpath.join(self.current_path, prefix)
        log.debug("getting path completion for: " + path_prefix)
        try:
            self.check_connection(self._ls)
            try:
                result = self._ls.get_name_pathes(path_prefix)
            except:
                result = None

            if result is None or ( len(result[0]) ==0 and len(result[1])==0 ):
                result = self._ls.get_name_pathes(path_prefix + "*")

            self.matching_words.extend(result[0])
            self.matching_words.extend(result[1])
            
        except Exception as ex:
            log.debug("error getting competition paths: " + ex.message)
        
    
    
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

    #endregion

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
        except ValueError:
            self.run_min = 0
        
        #parse run max 
        try:
            run_max = int(str_max)
            run_max_set = True
        except ValueError:
            self.run_max = ccdb.INFINITE_RUN
        
        return run_min, run_max, run_min_set, run_max_set


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
  CCDB shell v.0.5
  HallD JLab
+--------------------------+
       """
        print self.theme.Title + "Interactive mode"
        print "print " + self.theme.Accent + "help" + self.theme.Reset + " to get help"
        print "print " + self.theme.Accent + "quit" + self.theme.Reset + " or " + self.theme.Accent + "q" + self.theme.Reset +" to exit"
        print "print !<command> to execute shell command"
        print
        print "You login as: '"+self._user_name+"'"
        
        
                
                    





