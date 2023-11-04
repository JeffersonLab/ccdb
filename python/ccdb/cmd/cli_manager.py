import importlib
import pkgutil

import os
import sys
import logging
import shlex
import posixpath
import getpass
import ccdb.cmd
import ccdb.cmd.commands
import ccdb.path_utils
from ccdb.brace_log_message import BraceMessage as lfm
from ccdb import AlchemyProvider
from .cli_command import CliCommandBase
from .cli_context import CliContext
from . import themes
from . import colorama


log = logging.getLogger("ccdb.cmd.console_context")


def import_all_submodules(modules_dir, package_name):
    """Imports all modules in a package"""

    # >oO debug   for (module_loader, name, ispkg) in pkgutil.iter_modules([modules_dir]):
    # >oO debug       print("module_loader {}, name {}, ispkg {}".format(module_loader, name, ispkg))

    # parent_module =  imp.find_module('packets', path)
    for (module_loader, name, is_pkg) in pkgutil.iter_modules([modules_dir]):
        importlib.import_module('.' + name, package_name)
        # module = importlib.import_module('.' + name, package_name)
        # >oO debug   print(module)


class CliManager(object):
    """
    Class to manage console commands

    This class uses console_utilities from utils directories

    """

    prefix = None
    words = []

    def __init__(self):
        self._prov = AlchemyProvider()
        self._commands = {}
        self._ls = None
        self.silent_exceptions = True  # rethrow happened exceptions
        self.log_sqlite = False
        self.context = CliContext(self._prov, themes.NoColorTheme(), self._commands)
        self.matching_words = []

    @property
    def utils(self):
        """:rtype: {}"""
        return self._commands

    @property
    def connection_string(self):
        """:rtype: str"""
        return self.context.connection_string

    @connection_string.setter
    def connection_string(self, con_str):
        self.context.connection_string = con_str

    @property
    def provider(self):
        return self._prov

    @property
    def theme(self):
        """:rtype: themes.NoColorTheme"""
        return self.context.theme

    @theme.setter
    def theme(self, value):
        """
        :param value: new theme to set
        :type value: themes.NoColorTheme
        """
        log.debug(lfm(" |- theme(value) {0} | \\{0} |  |- theme switched to : '{1}'", os.linesep, value))
        self.context.theme = value

    # =====================================================================================
    # ------------------ C O M M A N D S   M A N A G E M E N T  ---------------------------
    # =====================================================================================

    # --------------------------------
    #  register_utilities
    # --------------------------------
    def register_utilities(self, path=""):
        """ Function to auto find and register utilities"""

        modules_dir = ccdb.cmd.commands.__path__[0]
        package_name = ccdb.cmd.commands.__name__

        # We need to import submodules at least once to get __submodules__() function work later
        import_all_submodules(modules_dir, package_name)

        # Create all subclasses of PacketInstallationInstruction and add here
        for cls in CliCommandBase.__subclasses__():
            try:
                util = cls(self.context)
            except Exception as ex:
                log.warning(lfm("Error loading command: '{}' with exception: '{}'", cls, ex))
                continue

            self._commands[util.command] = util
            util.theme = self.theme
            if util.command == "ls":
                self._ls = util

            if log.isEnabledFor(logging.DEBUG):
                log.debug("{0:<10} {1:<15} {2}:".format("(command)", "(name)", "(description)"))
                log.debug("\n".join(["{0:<10} {1:<15} {2}:".format(command, util.name, util.short_descr)
                                     for command, util
                                     in list(self._commands.items())]))

    # --------------------------------
    #   processes the arguments
    # --------------------------------
    def process(self, args, start_index=1):

        # check if there is enough arguments...
        if len(args) < (start_index + 1):
            self.print_general_usage()
            return

        # get working arguments list
        workargs = args[start_index:]

        # parse loop
        i = 0
        while i < len(workargs):
            token = workargs[i]
            assert isinstance(token, str)
            i += 1

            if token.startswith('-'):
                # it is some command, lets parse what is the command

                # connection string
                if (token == "-c" or token == "--connection") and (i < len(workargs)):
                    self.context.connection_string = workargs[i]
                    i += 1

                # it is an interactive mode
                elif token == "-I" or token == "-i" or token == "--interactive":
                    self.context.is_interactive = True

                # working run
                elif token == "-r" or token == "--run":
                    # working run
                    try:
                        self.context.current_run = int(workargs[i])
                        log.info("Working run is %i", self.context.current_run)
                    except ValueError:
                        log.warning("(!) Warning. Cannot read run from %s command" % token)
                    i += 1

                # working variation
                elif token == "-v" or token == "--variation":
                    if not ccdb.path_utils.validate_name(workargs[i]):
                        log.warning("(!) Warning. Cannot read variation from --variation flag. "
                                    "Variation name should consist of A-Z, a-z, 0-9, _")
                    else:
                        self.context.current_variation = workargs[i]
                    i += 1

                # we have to ask mysql password
                if "--mysql-pwd" in args[start_index:] and self.context.connection_string.startswith("mysql"):
                    print("Enter MySql password: ")
                    password = getpass.getpass()
                    self.context.connection_string = self.context.connection_string.replace("@", ":" + password + "@")
                    i += 1
            else:
                # looks like is is a command
                command = token
                command_args = workargs[i:]
                try:
                    return self.process_command(command, command_args)
                except Exception as ex:
                    log.error(ex)
                    if self.silent_exceptions:
                        return None
                    else:
                        raise

        if self.context.is_interactive:
            self.interactive_loop()

    # --------------------------------
    #   executes text as command
    # --------------------------------
    def process_command_line(self, command_line):
        """tries to execute a line of text"""

        log.debug("{0}Process command line: {1}{0}\\".format(os.linesep, command_line))

        # execute shell command if input starts with '!'
        if command_line.startswith('!'):
            command_line = command_line[1:]
            # noinspection PyBroadException
            try:
                os.system(command_line)
            except:
                pass
            return  # everything is done

        # split command to arguments
        is_posix = os.name == 'posix'
        tokens = shlex.split(command_line, posix=is_posix)

        # validate
        if len(tokens) == 0:
            return None

        # get our command
        command = tokens[0]
        log.debug(" |- command is : {0}".format(command))
        log.debug(" |- tokens : {0}".format(" ".join([("'" + t + "'") for t in tokens])))

        # get command arguments
        arguments = []
        if len(tokens) > 1:
            arguments = tokens[1:]

        # execute everything
        return self.process_command(command, arguments)

    # --------------------------------
    #
    # --------------------------------
    def process_command(self, cmd_name, args):
        # >oO debug
        if log.isEnabledFor(logging.DEBUG):
            log.debug(lfm("{0}Processing command: '{1}'{0}\\", os.linesep, cmd_name))
            log.debug(lfm(" |- arguments : '{0}'", "' '".join(args)))

        # try to find function...
        try:
            command = self._commands[cmd_name]
        except KeyError:
            log.error("Command " + cmd_name + " is unknown! Please, use help to see available commands")
            if self.silent_exceptions:
                return None
            else:
                raise

        # check connection and connect if needed
        if command.uses_db and (not self.provider.is_connected):
            if not self.check_connection(command):
                return None

        # is there file redirect?
        redir_to_file = False   # should we redirect to file?
        redir_file = None       # file to redirect
        redir_stream_backup = sys.stdout
        redir_theme_backup = self.theme

        if ">" in args and args.index(">") == len(args) - 2:

            redir_fname = args[-1]
            redir_to_file = True
            args = args[:-2]
            log.debug(" |- redirecting to file : {0}".format(redir_fname))

            # open file
            try:
                redir_file = open(redir_fname, 'w')
            except Exception as ex:
                log.error("Cannot open file '{0}' {1} ".format(redir_fname, ex))
                if self.silent_exceptions:
                    return None
                else:
                    raise

        # execute command
        try:
            if redir_to_file:
                colorama.deinit()
                sys.stdout = redir_file
                self.theme = themes.NoColorTheme()

            result = command.execute(args)
            if command.is_alias:
                # Aliases return the next command to execute...
                result = self.process_command_line(result)

        except Exception as ex:
            log.info(ex)
            if self.silent_exceptions:
                return None
            else:
                raise
        finally:
            if redir_to_file:
                sys.stdout = redir_stream_backup
                redir_file.close()
                self.theme = redir_theme_backup
                colorama.reinit()
        return result

    # --------------------------------
    #
    # --------------------------------
    def check_connection(self, util):

        # maybe there is nothing to do?
        if self._prov.is_connected or (not util.uses_db):
            return True

        if log.isEnabledFor(logging.DEBUG):
            log.debug(" |- check_connection(util){0} | \\".format(os.linesep))
            log.debug(" |  |- utility '{}' requires DB. CCDB not yet connected. Connecting.".format(util.name))
            log.debug(" |  |- connection string is: '{}{}{}'"
                      .format(self.theme.Accent, self.context.connection_string, self.theme.Reset))

        # connecting
        try:
            self._prov.connect(self.context.connection_string)
        except Exception as ex:
            log.critical("CCDB provider unable to connect to {0}. Aborting command. Exception details: {1}".format(
                self.context.connection_string, ex))
            return False

        # skip user for sqlite
        if (not self.log_sqlite) and (self.provider.connection_string.startswith("sqlite://")):
            log.debug(" |  |- log_sqlite == False, set user to anonymous and disable logging'")
            self.provider.logging_enabled = False

        # connected
        if log.isEnabledFor(logging.DEBUG):
            if self.provider.connection_string.startswith("mysql+mysqlconnector://"):
                log.debug(" |  |- no module MySQLdb. Fallback to mysql-connector used")
            log.debug(
                " |  |- connection string used: '" + self.theme.Accent + self.provider.connection_string + self.theme.Reset + "'")
            log.debug(" |  |- connection: " + self.theme.Success + " successful " + self.theme.Reset)

        return True

    # ----------------------------------------------------
    #       interactive_loop
    # ----------------------------------------------------
    # noinspection PyBroadException
    def interactive_loop(self):
        import readline

        self.print_interactive_intro()
        # initialise autocomplete
        self.words = list(self._commands.keys())
        # completer = Completer(words)
        colorama.deinit()  # make colorama to release stderr and stdout
        readline.parse_and_bind("tab: complete")
        readline.set_completer(self.complete)
        try:
            readline.read_history_file()
        except:
            pass  # eat it

        # readline.set_completion_display_matches_hook(self.show_completions)
        # readline.set_completion_display_matches_hook([function])

        # Set or remove the completion display function. If function is specified, it will be used as the new completion
        # display function; if omitted or None, any completion display function already installed is removed.
        # The completion display function is called as function(substitution, [matches], longest_match_length) each
        # time matches need to be displayed.

        # Begin user commands read loop
        while 1:
            colorama.deinit()

            # read command from user
            try:
                user_input = input(self.context.current_path + "> ")
            except EOFError:
                log.debug("EOF sequence received. Ending interactive loop")
                break
            except KeyboardInterrupt:
                log.debug("Break sequence received. Ending interactive loop")
                break

            colorama.reinit()

            # exit if user wishes so
            if user_input in ("quit", "q", "exit"):
                break  # quit!

            # process user input
            self.process_command_line(user_input)

            # loop ended
        try:
            readline.write_history_file()
        except:
            log.warning("unable to write history file")

            # =====================================================================================
            # ------------------------ C O M P L E T I O N ----------------------------------------
            # =====================================================================================

    # region Description

    # --------------------------------
    # show_completions
    # --------------------------------
    def show_completions(self, substitution, matches, longest_match_length):
        print(self)
        print(substitution)
        print(matches)
        print(longest_match_length)

    # --------------------------------
    # generate_completion_words
    # --------------------------------
    # noinspection PyBroadException
    def generate_completion_words(self, prefix):

        # find all words that start with this prefix
        self.matching_words = [w for w in self.words if w.startswith(prefix)]

        # get name patches
        path_prefix = posixpath.join(self.context.current_path, prefix)
        log.debug("getting path completion for: " + str(path_prefix))
        try:
            self.check_connection(self._ls)
            try:
                result = self._ls.get_name_pathes(path_prefix)
            except:
                result = None

            if result is None or (len(result[0]) == 0 and len(result[1]) == 0):
                result = self._ls.get_name_pathes(path_prefix + "*")

            dir_list = [subdir.name for subdir in result[0]]
            table_list = [table.name for table in result[1]]

            self.matching_words.extend(dir_list)
            self.matching_words.extend(table_list)

        except Exception as ex:
            log.debug("error getting competition paths: " + str(ex))

    # --------------------------------
    #       complete
    # --------------------------------
    def complete(self, prefix, index):

        # print "prefix ", prefix, "  index ", index
        # readline.insert_text("bla bla bla")
        # colorama.deinit()
        # print "ha ha ha"
        # colorama.reinit()

        if prefix != self.prefix:
            # get new completions
            self.generate_completion_words(prefix)

            # self.matching_words.append(
            self.prefix = prefix

        else:

            # print  "prefix the same, matching:", len(self.matching_words)

            # print "  ".join([word for word in self.matching_words])
            # readline.redisplay()
            pass

        try:
            return self.matching_words[index]
        except IndexError:
            return None

    # =====================================================================================
    # ------------------------- H E L P   A N D   I N F O ---------------------------------
    # =====================================================================================
    @staticmethod
    def print_general_usage():
        print("Use '-i'   option to enter interactive shell")
        print("Use 'help' option for help")
        print("Use 'help command' to get help for particular command")

    def print_info(self):
        log.info("Login as   : '" + self.context.user_name + "'")
        log.info("Connect to : '" + self.context.connection_string + "'")
        log.info("Variation  : '" + self.context.current_variation + "'")
        log.info("Default run: '" + str(self.context.current_run) + "'")

    def print_interactive_intro(self):
        print("""
+--------------------------+
  CCDB shell v.2.00.00
+--------------------------+
       """)
        print((self.theme.Title + "Interactive mode"))
        print(("print " + self.theme.Accent + "help" + self.theme.Reset + " to get help"))
        print((
            "print " + self.theme.Accent + "quit" + self.theme.Reset + " or " + self.theme.Accent + "q" + self.theme.Reset + " to exit"))
        print("print !<command> to execute shell command")
        print()
        self.print_info()
