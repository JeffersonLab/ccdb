import posixpath
import logging
import os

import ccdb.model
from ccdb.errors import ObjectIsNotFoundInDbError
from ccdb.model import Directory, TypeTable, Assignment, CcdbSchemaVersion
from ccdb.provider import AlchemyProvider
from ccdb.cmd import CliCommandBase, UtilityArgumentParser
from ccdb import BraceMessage as LogFmt
from ccdb.sql.mysql_schema import init_mysql_database
from ccdb.sql.update_v5 import update_v5

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text

log = logging.getLogger("ccdb.cmd.commands.db")


def run_sql_script(file_path, db_url):
    # Create an engine and bind the session to it
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)

    # Start a session
    session = Session()

    try:
        # Start the transaction
        session.begin()

        # Read SQL commands from the file
        with open(file_path, 'r') as file:
            sql_commands = file.read()

        # Execute SQL commands
        session.execute(sql_commands)

        # Commit the changes
        session.commit()
        print("SQL script executed successfully.")
    except SQLAlchemyError as e:
        # Rollback in case of error
        session.rollback()
        print(f"An error occurred: {e}")
    finally:
        # Close the session
        session.close()

# # Example usage
# db_url = 'mysql+pymysql://username:password@localhost/dbname'  # Replace with your actual database URL
# file_path = 'path/to/your/sql/script.sql'  # Replace with the path to your SQL file
# run_sql_script(file_path, db_url)
#
#
# log = logging.getLogger("ccdb.cmd.commands.db")


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
    uses_db = False

    def __init__(self, context):
        CliCommandBase.__init__(self, context)

    def execute(self, args):
        if log.isEnabledFor(logging.DEBUG):
            log.debug(LogFmt("{0}Database command is in charge{0}\\".format(os.linesep)))
            log.debug(LogFmt(" |- arguments : '" + "' '".join(args) + "'"))

        # This command might be used as an alias
        self.is_alias = False
        assert self.context is not None

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
                self.db_init()
        elif result.sub_command == 'update':
            log.info("There is no 'update' command. Did you meant 'upgrade'?")
        elif result.sub_command == 'upgrade':
            if not result.upgrade_i_am_sure:
                log.info("(!!!) DO NOT PERFORM ON PRODUCTION DATABASE WITHOUT PROPER BACKUP (!!!)")
                log.info("This command tries to upgrade DB structure to current version")
                log.info("Add --upgrade-i-am-sure flag to this command to really execute")
            else:
                self.db_upgrade()
        elif result.sub_command == 'stats':
            self.db_stats()
        else:
            if result.sub_command:
                log.info(f"There is no '{result.sub_command}' command.")
            self.db_base_info()

    def db_init(self):
        log.debug(f" |- Initializing database : '{self.context.connection_string}'")
        log.debug(f" |- This script path : '{ os.path.abspath(__file__) }'")
        provider = self.context.provider
        provider.connect(connection_string=self.context.connection_string, check_version=False)
        init_mysql_database(provider.engine)
        log.debug(f" |- Done DB init")

    def db_upgrade(self):
        log.debug(f" |- Upgrading database : '{self.context.connection_string}'")
        provider = self.context.provider
        assert isinstance(provider, AlchemyProvider)
        provider.connect(connection_string=self.context.connection_string, check_version=False)
        update_v5(provider.engine)
        log.debug(f" |- Done DB upgrade")

    def db_stats(self):
        provider = self.context.provider
        assert isinstance(provider, AlchemyProvider)
        asgm_count = provider.session.query(Assignment).count()
        print(f"Num assignments: {asgm_count}")

    def db_base_info(self):
        provider = self.context.provider
        assert isinstance(provider, AlchemyProvider)
        provider.connect(self.context.connection_string, False)
        version = provider.session.query(CcdbSchemaVersion).one()
        assert isinstance(version, CcdbSchemaVersion)
        print(f"Connection to: {self.context.connection_string}")
        print(f"Schema version: {version.version}")

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
