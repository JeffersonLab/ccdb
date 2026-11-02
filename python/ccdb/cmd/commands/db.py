import itertools
import logging
import os

import ccdb.model
from ccdb.model import Assignment, CcdbSchemaVersion
from ccdb.provider import AlchemyProvider, hide_password
from ccdb.cmd import CliCommandBase, UtilityArgumentParser
from ccdb import BraceMessage as LogFmt
from ccdb.sql.mysql_schema import init_mysql_database
from ccdb.sql.sqlite_schema import init_sqlite_database
from ccdb.sql.update_v6 import upgrade_v6, UpgradeRefusedError
from ccdb.sql.rollback_v6 import rollback_v6
from ccdb.sql.shared_sets import dedup, rehash

from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

log = logging.getLogger("ccdb.cmd.commands.db")

SUBCOMMANDS = ["init", "update", "upgrade", "stats", "rollback-v6", "dedup", "rehash"]
LEGACY_FLAGS = ["--init-i-am-sure", "--upgrade-i-am-sure"]     # the only flags of CCDB 2.4's `ccdb db`


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

        # 2.4 had one flat parser, so its two flags could also come before the subcommand, as in
        # 'ccdb db --upgrade-i-am-sure upgrade'; the subparsers expect them after it
        leading_flags = list(itertools.takewhile(lambda arg: arg in LEGACY_FLAGS, args))
        if leading_flags:
            rest = args[len(leading_flags):]
            if not rest:
                return self.db_base_info()    # 2.4: a flag without a subcommand showed the database info
            args = rest[:1] + leading_flags + rest[1:]

        # 2.4 answered an unknown subcommand with a hint and the database info; argparse would raise instead
        if args and not args[0].startswith("-") and args[0] not in SUBCOMMANDS:
            log.info(f"There is no '{args[0]}' command.")
            return self.db_base_info()

        # utility argument parser is argparse which raises errors instead of exiting app
        result = self.argument_parser().parse_args(args)

        if result.sub_command == 'init':
            if not result.init_i_am_sure:
                log.info("NEVER DO THIS ON PRODUCTION DATABASE(!!!)")
                log.info("This command removes DB tables and recreates them. ALL DATA IS LOST")
                log.info("Add --init-i-am-sure flag to this command to really execute")
            else:
                return self.db_init()
        elif result.sub_command == 'update':
            log.info("There is no 'update' command. Did you meant 'upgrade'?")
        elif result.sub_command == 'upgrade':
            if result.dry_run:
                return self.db_upgrade(result)
            if not result.upgrade_i_am_sure:
                log.info("(!!!) DO NOT PERFORM ON PRODUCTION DATABASE WITHOUT PROPER BACKUP (!!!)")
                log.info("This command tries to upgrade DB structure to current version")
                log.info("Run it with --dry-run first to see what it would do")
                log.info("Add --upgrade-i-am-sure flag to this command to really execute")
                return False  # nothing changed: exit code 1
            return self.db_upgrade(result)
        elif result.sub_command == 'rollback-v6':
            if not result.rollback_i_am_sure:
                log.info("(!!!) DO NOT PERFORM ON PRODUCTION DATABASE WITHOUT PROPER BACKUP (!!!)")
                log.info("This command returns the database from schema version 6 to 5, for CCDB 2.4")
                log.info("Add --rollback-i-am-sure flag to this command to really execute")
                return False  # nothing changed: exit code 1
            return self.db_rollback(result)
        elif result.sub_command == 'dedup':
            return self.db_dedup(result)
        elif result.sub_command == 'rehash':
            return self.db_rehash(result)
        elif result.sub_command == 'stats':
            return self.db_stats()
        else:
            return self.db_base_info()

    @staticmethod
    def argument_parser():
        """One subparser per subcommand. Every subcommand that changes data acts only with its --<verb>-i-am-sure flag;
        without it, it reports, verifies or warns and changes nothing. No subcommand prompts or makes a backup."""
        parser = UtilityArgumentParser(prog="ccdb db")
        subcommands = parser.add_subparsers(dest="sub_command")

        init = subcommands.add_parser("init")
        init.add_argument("--init-i-am-sure", action="store_true")

        subcommands.add_parser("update")      # a frequent typo of 'upgrade': answered with a hint
        subcommands.add_parser("stats")

        upgrade = subcommands.add_parser("upgrade")
        upgrade.add_argument("--upgrade-i-am-sure", action="store_true")
        upgrade.add_argument("--dry-run", action="store_true", help="print what the upgrade would do, write nothing")
        upgrade.add_argument("--duplicates", choices=["none", "sample", "all"], default="none",
                             help="dry run: count duplicate sets reading no vault (none), the vaults of the tables "
                                  "with most sets (sample) or every vault (all)")
        upgrade.add_argument("--skip-privilege-check", action="store_true")
        upgrade.add_argument("--no-transaction-check", action="store_true")
        upgrade.add_argument("--in-place", action="store_true", help="SQLite: change the file itself, not a copy")

        rollback = subcommands.add_parser("rollback-v6")
        rollback.add_argument("--rollback-i-am-sure", action="store_true")
        rollback.add_argument("--drop-v6-data", action="store_true")
        rollback.add_argument("--allow-non-strict", action="store_true")
        rollback.add_argument("--in-place", action="store_true")
        rollback.add_argument("--skip-privilege-check", action="store_true")
        rollback.add_argument("--no-transaction-check", action="store_true")

        dedup = subcommands.add_parser("dedup")
        dedup.add_argument("--table", metavar="PATH")
        dedup.add_argument("--dedup-i-am-sure", action="store_true")
        dedup.add_argument("--no-transaction-check", action="store_true")

        rehash = subcommands.add_parser("rehash")
        rehash.add_argument("--sample", type=int, metavar="N")
        rehash.add_argument("--server", action="store_true")
        rehash.add_argument("--rehash-i-am-sure", action="store_true")
        return parser

    def db_init(self):
        log.debug(f" |- Initializing database : '{hide_password(self.context.connection_string)}'")
        log.debug(f" |- This script path : '{ os.path.abspath(__file__) }'")
        provider = self.context.provider
        # the DDL keeps the server's time zone (see AlchemyProvider.attach)
        provider.connect(connection_string=self.context.connection_string, check_version=False,
                         client_time_zone=False)
        # both functions commit at the end and raise on the first error, which makes the command exit non-zero
        if provider.engine.dialect.name == "sqlite":
            init_sqlite_database(provider.engine)
        else:
            init_mysql_database(provider.engine)
        log.debug(" |- Done DB init")
        return True

    def connected_provider(self, check_version, client_time_zone=True):
        provider = self.context.provider
        assert isinstance(provider, AlchemyProvider)
        provider.connect(connection_string=self.context.connection_string, check_version=check_version,
                         client_time_zone=client_time_zone)
        return provider

    def db_upgrade(self, options):
        log.debug(f" |- Upgrading database : '{hide_password(self.context.connection_string)}'")
        provider = self.connected_provider(check_version=False, client_time_zone=False)
        # upgrade_v6 checks the version first: any version other than 5 is refused, naming it, and nothing changes
        try:
            upgrade_v6(provider.engine, dry_run=options.dry_run, duplicates=options.duplicates,
                       skip_privilege_check=options.skip_privilege_check,
                       transaction_check=not options.no_transaction_check, in_place=options.in_place)
        except UpgradeRefusedError as refusal:
            log.error(str(refusal))
            return False  # a refusal changed nothing: exit code 1
        log.debug(" |- Done DB upgrade")
        return True

    def db_rollback(self, options):
        log.debug(f" |- Rolling back database : '{hide_password(self.context.connection_string)}'")
        provider = self.connected_provider(check_version=False, client_time_zone=False)
        try:
            rollback_v6(provider.engine, drop_v6_data=options.drop_v6_data, allow_non_strict=options.allow_non_strict,
                        in_place=options.in_place, skip_privilege_check=options.skip_privilege_check,
                        transaction_check=not options.no_transaction_check)
        except UpgradeRefusedError as refusal:
            log.error(str(refusal))
            return False  # a refusal changed nothing: exit code 1
        return True

    def db_dedup(self, options):
        provider = self.connected_provider(check_version=True)
        return dedup(provider, table_path=options.table, apply=options.dedup_i_am_sure,
                     transaction_check=not options.no_transaction_check)

    def db_rehash(self, options):
        provider = self.connected_provider(check_version=True)
        return rehash(provider, sample=options.sample, server=options.server, apply=options.rehash_i_am_sure)

    def db_stats(self):
        provider = self.context.provider
        assert isinstance(provider, AlchemyProvider)
        provider.connect(self.context.connection_string, True)
        asgm_count = provider.session.query(Assignment).count()
        print(f"Num assignments: {asgm_count}")

        constant_set_count = provider.session.query(ccdb.ConstantSet).count()
        print(f"Num constant sets: {constant_set_count}")

        # sets used by more than one assignment: equal data of one table is stored once and shared
        shared_sets = select(Assignment.constant_set_id) \
            .group_by(Assignment.constant_set_id) \
            .having(func.count(Assignment.id) > 1) \
            .subquery()
        shared_set_count = provider.session.execute(select(func.count()).select_from(shared_sets)).scalar()
        print(f"Num shared constant sets: {shared_set_count}")

        return True

    def db_base_info(self):
        provider = self.context.provider
        assert isinstance(provider, AlchemyProvider)
        provider.connect(self.context.connection_string, False)
        version = provider.session.query(CcdbSchemaVersion).one()
        assert isinstance(version, CcdbSchemaVersion)
        print(f"Connection to: {hide_password(self.context.connection_string)}")
        print(f"Schema version: {version.version}")
        return True

    def print_help(self):
        """Prints help of the command"""

        print("""
Provides information and management commands for used Database

    ccdb db     # provides information about the connected database

subcommands:
    init      - initialize the database (add --init-i-am-sure)
    upgrade   - upgrade the database from schema version 5 to 6 (add --upgrade-i-am-sure)
                --dry-run [--duplicates none|sample|all]  print what the upgrade would do, write nothing
                --skip-privilege-check, --no-transaction-check  proceed although the preflight cannot see
                    a privilege granted through a role, or other sessions' transactions (no PROCESS privilege)
                --in-place  SQLite: change the file itself; by default a copy replaces it, keeping <file>.v5
    stats     - provide database statistics: assignments, constant sets, sets shared by several assignments
    dedup     - report constant sets of one table with equal data and unused sets; --dedup-i-am-sure merges
                them into the oldest set, removes the unused ones and creates the unique index
                [--table PATH] [--no-transaction-check]
    rehash    - verify the stored sha256 and size of every constant set; --sample N checks N sets,
                --server (MySQL) also compares with the server's SHA2, --rehash-i-am-sure rewrites mismatches
    rollback-v6 - return the database from schema version 6 to 5 for CCDB 2.4 (add --rollback-i-am-sure)
                [--drop-v6-data] [--allow-non-strict] [--in-place] [--skip-privilege-check] [--no-transaction-check]
""")
