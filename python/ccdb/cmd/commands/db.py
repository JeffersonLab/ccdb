import posixpath
import logging
import os

from ccdb.errors import ObjectIsNotFoundInDbError
from ccdb.model import Directory, TypeTable
from ccdb.provider import AlchemyProvider
from ccdb.cmd import CliCommandBase, UtilityArgumentParser
from ccdb import BraceMessage as LogFmt

log = logging.getLogger("ccdb.cmd.commands.db")


# ********************************************************************
#   Class Database - Database info, statistics, maintenance          *
# ********************************************************************

class Database(CliCommandBase):
    """ List objects in a given directory """

    # ccdb utility class descr part 
    #------------------------------
    command = "db"
    name = "Database"
    short_descr = "Database information and management"
    uses_db = True

    def __init__(self, context):
        CliCommandBase.__init__(self, context)


    def execute(self, args):
        if log.isEnabledFor(logging.DEBUG):
            log.debug(LogFmt("{0}Database is in charge{0}\\".format(os.linesep)))
            log.debug(LogFmt(" |- arguments : '" + "' '".join(args) + "'"))

        # This command might be used as an alias
        self.is_alias = False

        assert self.context is not None
        provider = self.context.provider
        assert isinstance(provider, AlchemyProvider)

        # PARSE ARGUMENTS
        # -------------------------------
        # utility argument parser is argparse which raises errors instead of exiting app
        parser = UtilityArgumentParser()
        parser.add_argument("sub_command", nargs='?', default="")
        parser.add_argument("--init-i-am-sure",  action="store_true")
        parser.add_argument("--upgrade-i-am-sure",  action="store_true")
        result = parser.parse_args(args)

        if result.sub_command == 'init':
            if not result.init_i_am_sure:
                log.info("NEVER DO THIS ON PRODUCTION DATABASE(!!!)")
                log.info("This command removes DB tables and recreates them. ALL DATA IS LOST")
                log.info("Add --init-i-am-sure flag to this command to really execute")
            else:
                self.db_init(provider)
        elif result.sub_command == 'upgrade':
            if not result.upgrade_i_am_sure:
                log.info("(!!!) DO NOT PERFORM ON PRODUCTION DATABASE WITHOUT PROPER BACKUP (!!!)")
                log.info("This command tries to upgrade DB structure to current version")
                log.info("Add --upgrade-i-am-sure flag to this command to really execute")
            else:
                self.db_upgrade(provider)
        elif result.sub_command == 'stats':
            self.db_stats(provider)
        else:
            self.db_base_info(provider)



    def db_init(self, provider):
        log.error("NOT IMPLEMENTED YET")
        pass

    def db_upgrade(self, provider):
        log.error("NOT IMPLEMENTED YET")
        pass

    def db_stats(self, provider):
        log.error("NOT IMPLEMENTED YET")
        pass

    def db_base_info(self, provider):
        log.error("NOT IMPLEMENTED YET")
        pass

    def print_help(self):
        """Prints help of the command"""

        print("""
Provides information and management commands for used Database

    ccdb db     # provides information about the connected database

subcommands:
    init      - initialize the database
    upgrade   - upgrade the database to current version
    stats     - provide database statistics
""")
