"""
Runs CCDB local Web GUI
"""
import logging
import os

from ccdb.cmd import CliCommandBase, UtilityArgumentParser
from ccdb import BraceMessage as LogFmt
from ccdb.provider import hide_password


# logger must be set to ccdb.cmd.commands.<command name>
log = logging.getLogger("ccdb.cmd.commands.gui")


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
    uses_db = False  # the web GUI opens its own engine; a CLI connection would sit idle for the server's lifetime

    def execute(self, args):
        """This is an entry point for each time the command is called"""
        from ccdb import webgui

        if log.isEnabledFor(logging.DEBUG):
            log.debug(LogFmt("{0}WebGui is in charge{0}\\".format(os.linesep)))
            log.debug(LogFmt(" |- arguments : '" + "' '".join(args)+"'"))

        assert self.context
        parsed_args = self.process_arguments(args)
        connection_string = self.context.connection_string
        app = webgui.cerate_ccdb_flask_app(connection_string)

        # Connect and check the schema before the server starts, so a wrong connection string fails here
        # instead of at the first page. The dev server does not fork, so creating the engine now is safe.
        try:
            webgui.db.get_database(app).ensure_engine()
        except Exception as ex:
            log.critical("CCDB web GUI unable to connect to {0}. Exception details: {1}".format(
                hide_password(connection_string), hide_password(str(ex), connection_string)))
            return False

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
