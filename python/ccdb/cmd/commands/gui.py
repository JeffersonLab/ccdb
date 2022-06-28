"""
Runs CCDB local Web GUI
"""
import logging
import os

import ccdb
import ccdb.path_utils
from ccdb.cmd import CliCommandBase, UtilityArgumentParser
from ccdb import AlchemyProvider
from ccdb import BraceMessage as LogFmt


# logger must be set to ccdb.cmd.commands.<command name>
log = logging.getLogger("ccdb.cmd.commands.empty")


#*********************************************************************
#   Class WebGui - empty utility example with description             *
#                                                                    *
#*********************************************************************
class WebGui(CliCommandBase):
    """Empty utility example"""
    
    # ccdb command related attributes:

    command = "gui"
    name = "WebGui"
    short_descr = "Starts local web GUI"
    uses_db = True

    def execute(self, args):
        """This is an entry point for each time the command is called"""
        from ccdb import webgui

        if log.isEnabledFor(logging.DEBUG):
            log.debug(LogFmt("{0}WebGui is in charge{0}\\".format(os.linesep)))
            log.debug(LogFmt(" |- arguments : '" + "' '".join(args)+"'"))

        # get provider class which has functions for all CCDB database operation
        assert self.context
        provider = self.context.provider
        assert isinstance(provider, AlchemyProvider)

        parsed_args = self.process_arguments(args)

        app = webgui.cerate_ccdb_flask_app()
        app.config["db"] = provider
        app.config["cli_context"] = self.context

        if parsed_args.port:
            app.run(port=parsed_args.port)
        else:
            app.run()

    @staticmethod
    def process_arguments(args):
        parser = UtilityArgumentParser()
        # parser.add_argument("raw_path")
        parser.add_argument("-p", "--port", default=0)

        return parser.parse_args(args)

    def print_help(self):
        """Prints help for the command"""
        
        print("""Starts CCDB local web GUI. 
        (Launches local web server with new CCDB web site with local parameters (user-name, db connection, etc.)  
        
        --port - sets the port number.  

    """)
