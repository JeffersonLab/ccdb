"""Schema 6: the fresh schema, the upgrade from schema 5, the version check and `db init`.

Pins rows T1-T7 and T9 of the test matrix in space-ccdb-2.5/notes/schema6.md (section 14). Written
before the feature: every test fails until schema 6 exists.

    SqliteSchemaV6Test   always runs, on SQLite files in a temporary directory
    MySqlSchemaV6Test    runs on the database of CCDB_TEST_MYSQL_CONNECTION (MySQL 8.3 or MariaDB 10.5),
                         skipped when the variable is unset. The tests drop every table of that database;
                         at the end the class leaves it as `ccdb db init` creates it, for the modules after.
    CCDB_TEST_MYSQL_READER_CONNECTION   the same database as ccdb_reader (SELECT only,
                         scripts/schema/test_users.sql): the T9 error case, skipped when unset (section 14.1).

Schema 5 databases come from the frozen base in schema_v5_base.py, fresh schema 6 from `ccdb db init`,
the upgrade from `ccdb db upgrade`. CLI commands run in-process like integ_test_cli_manager.py, with an
empty stdin: no command prompts (section 14.1). Structures are compared with scripts/schema/compare.py,
with both link-table names left out (section 2.4). The lock clauses of T5 are read from every statement the
MySQL driver's cursors execute, so DDL sent through SQLAlchemy or through a raw DB-API cursor is seen alike.
"""
import hashlib
import importlib
import importlib.util
import logging
import os
import re
import shutil
import sys
import tempfile
import unittest
from io import StringIO

import sqlalchemy
from sqlalchemy import text
from sqlalchemy.engine import make_url

import ccdb.cmd.themes
from ccdb import AlchemyProvider
from ccdb import testing as helper
from ccdb.cmd.cli_manager import CliManager, CCDB_EXCEPTIONS_THROW
from ccdb.cmd.utility_argument_parser import ArgumentParseError
from ccdb.errors import DatabaseStructureError

# Have to import it this way as tests may be considered a package or not depending on context
try:
    from . import schema_v5_base
except ImportError:
    import schema_v5_base


def _load_compare():
    path = os.path.join(helper.ccdb_path, "scripts", "schema", "compare.py")
    spec = importlib.util.spec_from_file_location("ccdb_schema_compare", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


compare = _load_compare()

INIT = "db init --init-i-am-sure"
UPGRADE = "db upgrade --upgrade-i-am-sure"
# ccdb_user has no PROCESS privilege, so the open-transaction check cannot run (section 6.2 item 3)
UPGRADE_MYSQL = UPGRADE + " --no-transaction-check"

ENV_MYSQL_READER = "CCDB_TEST_MYSQL_READER_CONNECTION"

LINK_TABLES = ("variationsToTags", "variations_has_tags")

SCHEMA6_TABLES = {"assignments", "assignmentsMaterializedView", "columns", "constantSets", "directories",
                  "eventRanges", "logs", "runRanges", "schemaVersions", "tags", "typeTables", "users",
                  "variations", "timeRanges", "properties"}

DEPRECATABLE_TABLES = ("directories", "typeTables", "variations")

SEED_VAULTS = {1: "1.11|1.991211|10.002|2.001|2.9912|20.111",
               2: "1.0|2.0|3.0|4.0|5.0|6.0",
               3: "10|20|30",
               4: "2.2|2.3|2.4|2.5|2.6|2.7",
               5: "10|11|12|13|14|15"}

HEX64 = re.compile(r"^[0-9a-f]{64}$")

# Section 11: Python 2.5 on a schema 5 database
V5_REFUSAL = ("The database schema version is 5. This CCDB version works with schema version 6. "
              "Upgrade with 'ccdb db upgrade' (docs/deployment/upgrade-2.5.md)")
# Section 11: an empty schemaVersions, two rows in it, or a missing table give today's message, which begins so
NO_STRUCTURE = "No database structure found"

V4_FILE = os.path.join(helper.ccdb_test_path, "old_schema.dbV4.sqlite")
BELOW_5_FILES = [("old_schema.ccdb.sqlite", os.path.join(helper.ccdb_test_path, "old_schema.ccdb.sqlite"), 3),
                 ("old_schema.dbV4.sqlite", V4_FILE, 4),
                 ("ccdb_v1-00.sqlite", os.path.join(helper.ccdb_path, "sql", "schemas_ccdb_v100", "ccdb_v1-00.sqlite"), 4)]
V100_MYSQL_FILE = os.path.join(helper.ccdb_path, "sql", "schemas_ccdb_v100", "ccdb_v1-00.mysql.sql")

# Section 6.1, CCDB 1.0 MySQL file: refused by the foreign-key stop of section 6.2 item 5, naming the
# constraints. These are the file's five, measured in information_schema.REFERENTIAL_CONSTRAINTS on both servers.
V100_FOREIGN_KEYS = ("fk_assignmentsMaterializedView_assignments1", "fk_assignmentsMaterializedView_variations1",
                     "fk_assignmentsMaterializedView_constantSets1", "fk_assignmentsMaterializedView_typeTables1",
                     "fk_assignmentsMaterializedView_runRanges1")

# 2.4's ccdb.sql.update_v5.sqlite_update_v5_queries, frozen here like schema_v5_base.py: the v4-era SQLite
# variant of section 6.1 is a version 4 file that 2.4 took to 5, and 2.5 may change or remove update_v5.
V4_TO_V5_SQLITE = [
    "ALTER TABLE variations ADD COLUMN isLocked TINYINT(1) NOT NULL DEFAULT 0;",
    "ALTER TABLE variations ADD COLUMN lockTime TIMESTAMP NULL DEFAULT NULL;",
    "ALTER TABLE variations ADD COLUMN lockAuthorId INT(11) NULL DEFAULT NULL;",
    "ALTER TABLE variations ADD COLUMN goBackBehavior INT(11) NOT NULL DEFAULT 0;",
    "ALTER TABLE variations ADD COLUMN goBackTime TIMESTAMP NULL DEFAULT NULL;",

    "ALTER TABLE typeTables ADD COLUMN isDeprecated TINYINT(1) NOT NULL DEFAULT 0;",
    "ALTER TABLE typeTables ADD COLUMN deprecatedById INT(11) NOT NULL DEFAULT -1;",
    "ALTER TABLE typeTables ADD COLUMN isLocked TINYINT(1) NOT NULL DEFAULT 0;",
    "ALTER TABLE typeTables ADD COLUMN lockAuthorId INT(11) NULL DEFAULT NULL;",
    "ALTER TABLE typeTables ADD COLUMN lockTime TIMESTAMP NULL DEFAULT NULL;",

    "ALTER TABLE directories ADD COLUMN isDeprecated TINYINT(1) NOT NULL DEFAULT 0;",
    "ALTER TABLE directories ADD COLUMN deprecatedById INT(11) NOT NULL DEFAULT -1;",

    """
        CREATE TABLE IF NOT EXISTS assignmentsMaterializedView (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            assignmentsId INTEGER NOT NULL,
            variationsId INTEGER NOT NULL,
            constantSetsId INTEGER NOT NULL,
            typeTablesId INTEGER NOT NULL,
            runRangesId INTEGER NOT NULL,
            runMin INTEGER NOT NULL,
            runMax INTEGER NOT NULL,
            assignmentTime TIMESTAMP NOT NULL
        );
        """,

    "UPDATE schemaVersions SET schemaVersion = 5 WHERE id = 1;",
]

# Section 6.1, v4-era SQLite: the remaining difference to fresh schema 6 is exactly these extra columns
V4_ERA_EXTRA = {("column", "directories.deprecatedById"), ("column", "typeTables.deprecatedById"),
                ("column", "typeTables.lockAuthorId"), ("column", "variations.lockAuthorId")}


# ----------------------------------------------------------------------------------------------------
# Structure dumps
# ----------------------------------------------------------------------------------------------------
TABLE_RE = re.compile(r"^table (\S+) engine=(\S+)")
COLUMN_RE = re.compile(r"^column ([^.\s]+)\.(\S+) type=(.*?) null=(YES|NO) default=(.*?)(?: extra=(.*))?$")
INDEX_RE = re.compile(r"^index ([^.\s]+)\.(.+) unique=(\d) columns=(.*)$")


def sqlite_url(path):
    return "sqlite:///" + os.path.abspath(path)


def dump(connection):
    """compare.py dump without the link tables, the one accepted difference (section 2.4)"""
    return compare.dump(connection, ignore_tables=LINK_TABLES)


def dump_text(lines):
    return "\n".join(lines) + "\n"


def line_key(line):
    """('column', 'table.column') for a dump line: the object the line describes"""
    if line.startswith("table "):
        return "table", line.split()[1]
    if line.startswith("index "):
        return "index", INDEX_RE.match(line).group(1) + "." + INDEX_RE.match(line).group(2)
    return "column", line.split()[1]


def diff_pairs(old, new):
    return {("-", line) for line in set(old) - set(new)} | {("+", line) for line in set(new) - set(old)}


def _normal_type(column_type):
    # MariaDB prints integer display widths (int(11), int(10) unsigned), MySQL 8 does not
    return re.sub(r"\b(int|bigint|smallint|mediumint)\(\d+\)", r"\1", column_type.lower())


def _normal_default(default):
    default = default.strip()
    if default.lower() in ("none", "null"):
        return None
    return default.lower().replace("()", "")


def parse_dump(lines):
    tables, columns, indexes = {}, {}, {}
    for line in lines:
        if line.startswith("table "):
            name, engine = TABLE_RE.match(line).groups()
            tables[name] = engine
        elif line.startswith("column "):
            table, column, column_type, null, default, extra = COLUMN_RE.match(line).groups()
            columns[(table, column)] = (_normal_type(column_type), null, _normal_default(default), extra)
        elif line.startswith("index "):
            table, name, unique, cols = INDEX_RE.match(line).groups()
            indexes[(table, name)] = (int(unique), cols)
    return tables, columns, indexes


def _schema6_columns(dialect):
    integer = "integer" if dialect == "sqlite" else "int"
    spec = {("constantSets", "sha256"): ("char(64)", "NO", None),
            ("constantSets", "size"): ("integer" if dialect == "sqlite" else "int unsigned", "NO", None),
            ("assignments", "timeRangeId"): (integer, "YES", None),
            ("columns", "units"): ("varchar(64)", "YES", None)}
    for table in DEPRECATABLE_TABLES:
        spec[(table, "deprecatedTime")] = ("datetime", "YES", None)
        spec[(table, "deprecationComment")] = ("text", "YES", None)
    return spec


def _schema6_tables(dialect):
    integer = "integer" if dialect == "sqlite" else "int"
    return {
        "tags": {"id": (integer, "NO", None), "name": ("varchar(100)", "NO", None),
                 "variationId": (integer, "NO", None), "snapshotTime": ("datetime", "NO", None),
                 "comment": ("text", "YES", None), "authorId": (integer, "NO", "1"),
                 "created": ("datetime", "NO", "current_timestamp")},
        "timeRanges": {"id": (integer, "NO", None), "timeFrom": ("datetime", "NO", None),
                       "timeTo": ("datetime", "YES", None), "comment": ("text", "YES", None)},
        "properties": {"id": (integer, "NO", None), "ownerType": ("varchar(16)", "NO", None),
                       "ownerId": (integer, "NO", None), "name": ("varchar(64)", "NO", None),
                       "value": ("text", "NO", None), "authorId": (integer, "NO", "1"),
                       "modified": ("datetime", "NO", "current_timestamp")},
    }


def _schema6_indexes(dialect, fresh):
    """The indexes of sections 2.1 and 2.2; those 'kept from schema 5' only for fresh=True, since a schema 5
    variant may never have had them (the mysql2sqlite file has an inline UNIQUE ("id") on tags instead)"""
    if dialect == "sqlite":
        spec = {("constantSets", "uq_constantSets_table_sha256"): (1, "constantTypeId,sha256"),
                ("tags", "uq_tags_name"): (1, "name"),
                ("tags", "fk_tags_variations1_idx"): (0, "variationId"),
                ("properties", "uq_properties_owner_name"): (1, "ownerType,ownerId,name")}
        if fresh:
            spec[("constantSets", "constantSets_fk_constantSets_constantTypes1_idx")] = (0, "constantTypeId")
            spec[("tags", "tags_id_UNIQUE")] = (0, "id")
        return spec
    spec = {("constantSets", "uq_constantSets_table_sha256"): (1, "constantTypeId,sha256"),
            ("assignments", "fk_assignments_timeRanges1_idx"): (0, "timeRangeId"),
            ("tags", "PRIMARY"): (1, "id"),
            ("tags", "uq_tags_name"): (1, "name"),
            ("tags", "fk_tags_variations1_idx"): (0, "variationId"),
            ("timeRanges", "PRIMARY"): (1, "id"),
            ("properties", "PRIMARY"): (1, "id"),
            ("properties", "uq_properties_owner_name"): (1, "ownerType,ownerId,name")}
    if fresh:
        spec[("constantSets", "fk_constantSets_constantTypes1_idx")] = (0, "constantTypeId")
        spec[("tags", "id_UNIQUE")] = (1, "id")
    return spec


def schema6_problems(lines, dialect, fresh):
    """What a dump lacks against sections 2.1-2.4; fresh=True also demands exactly the fresh table set"""
    tables, columns, indexes = parse_dump(lines)
    problems = []

    def check_column(table, column, expected):
        actual = columns.get((table, column))
        if actual is None:
            problems.append(f"missing column {table}.{column}")
        elif expected is not None and actual[:3] != expected:
            problems.append(f"column {table}.{column} is {actual[:3]}, expected {expected}")

    for (table, column), expected in _schema6_columns(dialect).items():
        check_column(table, column, expected)
    for table in DEPRECATABLE_TABLES:
        for column in ("isDeprecated", "deprecatedByUserId", "isLocked", "lockedByUserId"):
            check_column(table, column, None)
    for table, spec in _schema6_tables(dialect).items():
        if table not in tables:
            problems.append(f"missing table {table}")
            continue
        names = {c for (t, c) in columns if t == table}
        if names != set(spec):
            problems.append(f"table {table} has columns {sorted(names)}, expected {sorted(spec)}")
        for column, expected in spec.items():
            check_column(table, column, expected)
    for key, expected in _schema6_indexes(dialect, fresh).items():
        actual = indexes.get(key)
        if actual is None:
            problems.append(f"missing index {key[0]}.{key[1]}")
        elif actual != expected:
            problems.append(f"index {key[0]}.{key[1]} is {actual}, expected {expected}")
    if dialect == "sqlite" and (0, "timeRangeId") not in [v for (t, _), v in indexes.items() if t == "assignments"]:
        problems.append("no index on assignments.timeRangeId")
    if fresh:
        if set(tables) != SCHEMA6_TABLES:
            problems.append(f"tables {sorted(tables)}, expected {sorted(SCHEMA6_TABLES)}")
        if ("constantSets", "ix_constantSets_table_sha256") in indexes:
            problems.append("a fresh database has the interim index ix_constantSets_table_sha256")
    return problems


# ----------------------------------------------------------------------------------------------------
# Database access
# ----------------------------------------------------------------------------------------------------
def query(connection, sql, **params):
    engine = compare.engine_for(connection)
    try:
        with engine.connect() as conn:
            return [tuple(row) for row in conn.execute(text(sql), params)]
    finally:
        engine.dispose()


def execute(connection, statements, sql_mode=None):
    """Runs (sql) or (sql, params) items in one transaction"""
    engine = compare.engine_for(connection)
    try:
        with engine.begin() as conn:
            if sql_mode is not None:
                conn.execute(text("SET SESSION sql_mode = :m"), {"m": sql_mode})
            for statement in statements:
                if isinstance(statement, tuple):
                    conn.execute(text(statement[0]), statement[1])
                else:
                    conn.execute(text(statement))
    finally:
        engine.dispose()


def table_names(connection):
    if connection.startswith("sqlite"):
        return {row[0] for row in query(connection, "SELECT name FROM sqlite_master WHERE type = 'table' "
                                                    "AND name NOT LIKE 'sqlite_%'")}
    return {row[0] for row in query(connection, "SELECT TABLE_NAME FROM information_schema.TABLES "
                                                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_TYPE = 'BASE TABLE'")}


def table_rows(connection, exclude=()):
    """Every row of every table, for 'nothing changed' checks"""
    quote = '"%s"' if connection.startswith("sqlite") else "`%s`"
    return {name: query(connection, "SELECT * FROM %s ORDER BY 1" % (quote % name))
            for name in sorted(table_names(connection)) if name not in exclude}


def schema_versions(connection):
    return query(connection, "SELECT schemaVersion FROM schemaVersions")


def hash_problems(connection):
    """Every stored sha256 and size against Python's SHA-256 of the UTF-8 vault (section 1)"""
    problems = []
    for set_id, vault, sha256, size in query(connection, "SELECT id, vault, sha256, size FROM constantSets ORDER BY id"):
        data = vault.encode("utf-8")
        if (sha256, size) != (hashlib.sha256(data).hexdigest(), len(data)):
            problems.append(f"constant set {set_id}: stored ({sha256}, {size})")
    return problems


def build_v5_sqlite(path):
    engine = sqlalchemy.create_engine(sqlite_url(path))
    schema_v5_base.create_v5_sqlite(engine)
    engine.dispose()


def build_mysql2sqlite_v5(path):
    """The frozen schema 5 in the shape scripts/mysql2sqlite gives a MySQL dump.

    The converter turns `id` into INTEGER PRIMARY KEY AUTOINCREMENT, writes each UNIQUE INDEX as an unnamed
    inline UNIQUE ("id") (SQLite names it sqlite_autoindex_<table>_1) and prefixes the other indexes with idx_.
    """
    statements = []
    for statement in schema_v5_base._sqlite_statements(schema_v5_base.sqlite_init_script):
        if statement.startswith("CREATE INDEX"):
            name = statement.split('"')[1]
            if name.endswith("_UNIQUE"):
                continue
            statement = statement.replace('"%s"' % name, '"idx_%s"' % name, 1)
        elif statement.startswith("CREATE TABLE") and re.search(r'"id" integer\s+NOT NULL ,', statement):
            statement = re.sub(r'"id" integer\s+NOT NULL ,', '"id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,', statement)
            statement = statement.replace('PRIMARY KEY ("id")', 'UNIQUE ("id")')
        statements.append(statement)
    execute(sqlite_url(path), statements)


def drop_everything(connection):
    """Empties a MySQL database: tables, views and their foreign keys"""
    engine = compare.engine_for(connection)
    try:
        with engine.begin() as conn:
            conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
            rows = conn.execute(text("SELECT TABLE_NAME, TABLE_TYPE FROM information_schema.TABLES "
                                     "WHERE TABLE_SCHEMA = DATABASE()")).fetchall()
            for name, kind in rows:
                conn.execute(text(("DROP VIEW `%s`" if kind == "VIEW" else "DROP TABLE `%s`") % name))
            conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
    finally:
        engine.dispose()


def build_v5_mysql(connection):
    engine = compare.engine_for(connection)
    try:
        schema_v5_base.create_v5_mysql(engine)
    finally:
        engine.dispose()


def build_hallddb_shaped_v5(connection):
    """Schema 5 shaped like hallddb: InnoDB, latin1, tinyint(4), variations_has_tags, parentId default 0"""
    tables = {}
    for name, commands in schema_v5_base.mysql_tables.items():
        create = commands["create"].replace("ENGINE = MyISAM", "ENGINE = InnoDB DEFAULT CHARSET = latin1")
        create = create.replace("TINYINT(1)", "TINYINT(4)")
        create = create.replace("`parentId` INT NOT NULL DEFAULT 1,", "`parentId` INT NOT NULL DEFAULT 0,")
        tables[name] = (create.replace("variationsToTags", "variations_has_tags"), commands["data"])
    statements = ["ALTER DATABASE CHARACTER SET latin1 COLLATE latin1_swedish_ci"]
    for create, data in tables.values():
        statements.append(create)
        statements.extend(data)
    execute(connection, statements)


def v100_statements():
    """sql/schemas_ccdb_v100/ccdb_v1-00.mysql.sql without its DROP/CREATE SCHEMA and USE lines"""
    with open(V100_MYSQL_FILE) as sql_file:
        lines = sql_file.read().splitlines()
    statement = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            continue
        statement.append(line)
        if stripped.endswith(";"):
            joined = "\n".join(statement)
            statement = []
            if not re.match(r"\s*((DROP|CREATE) SCHEMA|USE )", joined, re.IGNORECASE):
                yield joined


def build_v100_mysql(connection):
    # the 1.0 file creates its schema with DEFAULT CHARACTER SET latin1
    execute(connection, ["ALTER DATABASE CHARACTER SET latin1 COLLATE latin1_swedish_ci"] + list(v100_statements()))


def mysql_charsets(connection):
    columns = {(t, c): (cs, coll, data_type) for t, c, cs, coll, data_type in query(
        connection, "SELECT TABLE_NAME, COLUMN_NAME, CHARACTER_SET_NAME, COLLATION_NAME, DATA_TYPE "
                    "FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE()")}
    tables = {t: (engine, coll, row_format) for t, engine, coll, row_format in query(
        connection, "SELECT TABLE_NAME, ENGINE, TABLE_COLLATION, ROW_FORMAT FROM information_schema.TABLES "
                    "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_TYPE = 'BASE TABLE'")}
    return {"columns": columns, "tables": tables}


def mysql_charset_problems(info, bin_columns=frozenset()):
    """Section 3 targets for the CCDB tables: utf8mb4_general_ci, utf8mb4_bin where named, sha256 ascii_bin"""
    problems = []
    for (table, column), (charset, collation, _) in sorted(info["columns"].items()):
        if table not in SCHEMA6_TABLES or collation is None:
            continue
        if (table, column) == ("constantSets", "sha256"):
            expected = ("ascii", "ascii_bin")
        elif (table, column) in bin_columns:
            expected = ("utf8mb4", "utf8mb4_bin")
        else:
            expected = ("utf8mb4", "utf8mb4_general_ci")
        if (charset, collation) != expected:
            problems.append(f"column {table}.{column} is {charset}/{collation}, expected {expected[1]}")
    for table, (engine, collation, _) in sorted(info["tables"].items()):
        if table in SCHEMA6_TABLES and (engine, collation) != ("InnoDB", "utf8mb4_general_ci"):
            problems.append(f"table {table} is {engine}/{collation}, expected InnoDB/utf8mb4_general_ci")
    return problems


def collation_map(info):
    return {key: value[:2] for key, value in info["columns"].items() if key[0] not in LINK_TABLES}


def database_default(connection):
    return query(connection, "SELECT DEFAULT_CHARACTER_SET_NAME, DEFAULT_COLLATION_NAME FROM information_schema.SCHEMATA "
                             "WHERE SCHEMA_NAME = DATABASE()")[0]


def foreign_keys(connection):
    """The foreign key constraints of the database, which compare.py does not dump (section 6.2 item 5)"""
    return sorted(query(connection, "SELECT CONSTRAINT_NAME, TABLE_NAME, REFERENCED_TABLE_NAME "
                                    "FROM information_schema.REFERENTIAL_CONSTRAINTS WHERE CONSTRAINT_SCHEMA = DATABASE()"))


class DriverStatements(object):
    """Collects every statement the MySQL drivers' cursors execute while active.

    Patched at the DB-API level, so a statement is seen whether it goes through SQLAlchemy or through
    engine.raw_connection().cursor(); the note does not say which one the upgrade uses.
    """
    CURSORS = (("pymysql.cursors", "Cursor"), ("MySQLdb.cursors", "BaseCursor"))

    def __enter__(self):
        self.statements = []
        self._patched = []
        for module_name, class_name in self.CURSORS:
            try:
                cursor_class = getattr(importlib.import_module(module_name), class_name)
            except ImportError:
                continue
            original = cursor_class.execute

            def execute(cursor, query, args=None, _original=original):
                self.statements.append(query.decode("utf-8", "replace") if isinstance(query, bytes) else str(query))
                return _original(cursor, query, args)

            cursor_class.execute = execute
            self._patched.append((cursor_class, original))
        return self

    def __exit__(self, *exc_info):
        for cursor_class, original in reversed(self._patched):
            cursor_class.execute = original
        return False


def connect_error(connection):
    """The exception AlchemyProvider.connect raises on this database, or None"""
    provider = AlchemyProvider()
    try:
        provider.connect(connection)
    except Exception as ex:
        return ex
    finally:
        provider.disconnect()
    return None


# ----------------------------------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------------------------------
class CliRun(object):
    def __init__(self, command, result, error, output):
        self.command = command
        self.result = result
        self.error = error
        self.output = output

    @property
    def exit_code(self):
        """The exit code `ccdb` would give (ccdb/__init__.py): None or False returned, or an exception, is 1"""
        if isinstance(self.error, SystemExit):
            code = self.error.code
            return 0 if code is None else code if isinstance(code, int) else 1
        if self.error is not None:
            return 1
        return 1 if self.result is None or self.result is False else 0

    @property
    def ok(self):
        """Section 14.1: exit code 0 on success"""
        return self.exit_code == 0

    @property
    def text(self):
        return self.output + ("\n" + str(self.error) if self.error is not None else "")


def run_cli(connection, command):
    """Runs one ccdb command in-process with its own CliManager; prints and log lines are captured.

    stdin is empty: no command prompts (section 14.1), so a prompt ends in EOFError instead of waiting.
    """
    cli = CliManager()
    cli.exception_handling = CCDB_EXCEPTIONS_THROW
    cli.force_exceptions = True
    cli.theme = ccdb.cmd.themes.NoColorTheme()
    cli.connection_string = connection
    cli.context.user_name = "test_user"
    cli.register_utilities()

    buffer = StringIO()
    handler = logging.StreamHandler(buffer)
    logger = logging.getLogger("ccdb")
    old_level = logger.level
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    saved_stdout, saved_stdin = sys.stdout, sys.stdin
    sys.stdout, sys.stdin = buffer, StringIO("")
    result = error = None
    try:
        result = cli.process_command_line(command)
    except (Exception, SystemExit) as ex:
        error = ex
    finally:
        sys.stdout, sys.stdin = saved_stdout, saved_stdin
        logger.removeHandler(handler)
        logger.setLevel(old_level)
        cli.provider.disconnect()  # an open session would hold metadata locks on MySQL
    return CliRun(command, result, error, buffer.getvalue())


class SchemaV6TestCase(unittest.TestCase):
    maxDiff = None

    def assert_ok(self, run):
        if not run.ok:
            self.fail(f"`{run.command}` did not succeed: {run.error!r}\n{run.output[-3000:]}")

    def assert_refused(self, run):
        """The command refused in its own checks with exit code 1 (section 14.1), not in argument parsing
        and not at a prompt; returns its messages"""
        if run.ok:
            self.fail(f"`{run.command}` succeeded, a refusal was expected\n{run.output[-3000:]}")
        if isinstance(run.error, ArgumentParseError) or run.exit_code != 1:
            self.fail(f"`{run.command}` was refused by the argument parser, not by the command: {run.error!r}")
        if isinstance(run.error, EOFError):
            self.fail(f"`{run.command}` prompted for input; section 14.1: no command prompts")
        return run.text

    def assert_no_structure(self, error):
        """Section 11: DatabaseStructureError with today's message, which begins 'No database structure found'"""
        self.assertIsInstance(error, DatabaseStructureError)
        self.assertTrue(str(error).startswith(NO_STRUCTURE), f"message does not begin {NO_STRUCTURE!r}: {error}")

    def assert_names_version(self, message, version):
        """Section 6.2 item 1: the refusal names the version found; the note gives no wording"""
        self.assertRegex(message, r"(?i)\b(version|schema)\b")
        self.assertRegex(message, r"\b%d\b" % version)


# ----------------------------------------------------------------------------------------------------
# SQLite
# ----------------------------------------------------------------------------------------------------
class SqliteSchemaV6Test(SchemaV6TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def path(self, name):
        return os.path.join(self.tmp, name)

    def fresh(self, name="fresh.sqlite"):
        path = self.path(name)
        self.assert_ok(run_cli(sqlite_url(path), INIT))
        return sqlite_url(path)

    def upgraded_v5(self, name="upgraded.sqlite"):
        path = self.path(name)
        build_v5_sqlite(path)
        self.assert_ok(run_cli(sqlite_url(path), UPGRADE))
        return sqlite_url(path)

    def test_fresh_objects(self):
        """T1 (§2.1-2.4): `db init` over a schema 5 file gives every schema 6 object, version 6, no link table."""
        path = self.path("fresh.sqlite")
        build_v5_sqlite(path)  # re-initializing an old file must remove its link table too (§2.4)
        self.assert_ok(run_cli(sqlite_url(path), INIT))
        problems = schema6_problems(compare.dump(sqlite_url(path)), "sqlite", fresh=True)
        self.assertEqual(problems, [])
        self.assertEqual(schema_versions(sqlite_url(path)), [(6,)])

    def test_seed_hashes(self):
        """T1 (§1, §4.1, §4.2): the seed's literal sha256 and size in both schema modules equal vault_digest."""
        from ccdb.model import vault_digest
        from ccdb.sql import mysql_schema, sqlite_schema

        mysql_seed = "\n".join(mysql_schema.mysql_tables["constantSets"]["data"])
        for set_id, vault in SEED_VAULTS.items():
            data = vault.encode("utf-8")
            digest = hashlib.sha256(data).hexdigest()
            self.assertEqual(vault_digest(vault), (digest, len(data)))
            self.assertIn(digest, sqlite_schema.sqlite_init_script, f"seed set {set_id} in sqlite_schema")
            self.assertIn(digest, mysql_seed, f"seed set {set_id} in mysql_schema")

        connection = self.fresh()
        rows = query(connection, "SELECT id, vault, sha256, size FROM constantSets ORDER BY id")
        self.assertEqual({row[0]: row[1] for row in rows if row[0] in SEED_VAULTS}, SEED_VAULTS)
        for set_id, vault, sha256, size in rows:
            self.assertRegex(sha256, HEX64)
            self.assertEqual((sha256, size), vault_digest(vault), f"constant set {set_id}")

    def test_upgrade_equals_fresh(self):
        """T2 (§2, §6.4): the frozen schema 5 upgraded equals fresh schema 6, link tables left out by name."""
        fresh = self.fresh()
        upgraded = self.upgraded_v5()
        self.assertMultiLineEqual(dump_text(dump(fresh)), dump_text(dump(upgraded)))
        self.assertEqual(schema_versions(upgraded), [(6,)])
        self.assertEqual(hash_problems(upgraded), [])
        self.assertIn("variations_has_tags", table_names(upgraded))  # nothing is dropped (§2.4)

    def test_upgrade_idempotent(self):
        """T3 (§6.2 item 1): a second upgrade of a schema 6 file refuses, names version 6 and changes nothing."""
        upgraded = self.upgraded_v5()
        # section 14.1: a present <file>.v5 makes the upgrade refuse on its own; moved away, as you would when
        # satisfied (section 6.4), so the version is the only reason left to refuse
        kept_original = self.path("upgraded.sqlite") + ".v5"
        if os.path.exists(kept_original):
            os.remove(kept_original)
        before = (dump(upgraded), table_rows(upgraded), sorted(os.listdir(self.tmp)))
        message = self.assert_refused(run_cli(upgraded, UPGRADE))
        self.assert_names_version(message, 6)
        self.assertEqual((dump(upgraded), table_rows(upgraded), sorted(os.listdir(self.tmp))), before)

    def test_upgrade_variants(self):
        """T4 (§6.1): the v4-era and mysql2sqlite SQLite variants pass their criteria; versions below 5 are refused."""
        fresh_lines = set(dump(self.fresh()))

        with self.subTest("SQLite upgraded from v4 by 2.4's update_v5"):
            path = self.path("v4era.sqlite")
            shutil.copy(V4_FILE, path)
            self.assertEqual(schema_versions(sqlite_url(path)), [(4,)])
            execute(sqlite_url(path), V4_TO_V5_SQLITE)
            self.assertEqual(schema_versions(sqlite_url(path)), [(5,)], "the frozen update_v5 statements did not run")
            self.assert_ok(run_cli(sqlite_url(path), UPGRADE))
            upgraded = set(dump(sqlite_url(path)))
            self.assertEqual(sorted(fresh_lines - upgraded), [], "fresh schema 6 lines missing after the upgrade")
            self.assertEqual({line_key(line) for line in upgraded - fresh_lines}, V4_ERA_EXTRA)
            self.assertEqual(hash_problems(sqlite_url(path)), [])

        with self.subTest("converted by scripts/mysql2sqlite: unnamed inline unique indexes"):
            path = self.path("mysql2sqlite.sqlite")
            build_mysql2sqlite_v5(path)
            self.assert_ok(run_cli(sqlite_url(path), UPGRADE))
            self.assertEqual(schema_versions(sqlite_url(path)), [(6,)])
            self.assertEqual(schema6_problems(dump(sqlite_url(path)), "sqlite", fresh=False), [])
            self.assertEqual(hash_problems(sqlite_url(path)), [])

        for name, source, version in BELOW_5_FILES:
            with self.subTest(f"{name}: version {version} is refused"):
                directory = tempfile.mkdtemp(dir=self.tmp)
                path = os.path.join(directory, name)
                shutil.copy(source, path)
                with open(path, "rb") as f:
                    before = f.read()
                message = self.assert_refused(run_cli(sqlite_url(path), UPGRADE))
                self.assert_names_version(message, version)
                with open(path, "rb") as f:
                    self.assertEqual(f.read(), before, "the refused file changed")
                self.assertEqual(os.listdir(directory), [name], "the preflight wrote a file")

    def test_version_check(self):
        """T7 (§4.1, §11): Python 2.5 accepts schema 6 and refuses 5, an empty, a doubled and a missing version table."""
        from ccdb.sql.sqlite_schema import create_sqlite_database

        def fresh_file(name):
            path = self.path(name)
            create_sqlite_database(path)
            return sqlite_url(path)

        with self.subTest("schema 6 is accepted"):
            connection = fresh_file("v6.sqlite")
            self.assertIsNone(connect_error(connection))
            self.assertEqual(schema_versions(connection), [(6,)])

        with self.subTest("schema 5 is refused with the message of §11"):
            path = self.path("v5.sqlite")
            build_v5_sqlite(path)
            error = connect_error(sqlite_url(path))
            self.assertIsInstance(error, DatabaseStructureError)
            self.assertIn(V5_REFUSAL, str(error))

        with self.subTest("an empty schemaVersions gives the no-structure message"):
            connection = fresh_file("empty.sqlite")
            execute(connection, ["DELETE FROM schemaVersions"])
            self.assert_no_structure(connect_error(connection))

        with self.subTest("two schemaVersions rows give the no-structure message"):
            connection = fresh_file("two.sqlite")
            execute(connection, ["INSERT INTO schemaVersions (id, schemaVersion) VALUES (2, 6)"])
            self.assert_no_structure(connect_error(connection))

        with self.subTest("a missing schemaVersions gives the no-structure message"):
            connection = fresh_file("missing.sqlite")
            execute(connection, ["DROP TABLE schemaVersions"])
            self.assert_no_structure(connect_error(connection))


# ----------------------------------------------------------------------------------------------------
# MySQL and MariaDB
# ----------------------------------------------------------------------------------------------------
LOCKED_DDL = re.compile(r"^\s*(ALTER\s+TABLE|CREATE\s+(UNIQUE\s+)?INDEX|DROP\s+INDEX)\b", re.IGNORECASE)
ADDS_COLUMN = re.compile(r"\bADD (?!(INDEX|UNIQUE|KEY|PRIMARY|CONSTRAINT|FULLTEXT|SPATIAL|FOREIGN)\b)")

# T6: each case changes a schema 5 base so that one stop of §3 applies:
# (name, servers, statements, table, column, row ids). Section 14.1: the message names the table, the column and
# the number of rows, with up to 10 row ids. The offending rows get ids no seed row has, so naming them means something.
CHARSET_STOPS = [
    ("cp1251 value that does not survive the conversion", "both",
     ["ALTER TABLE `runRanges` MODIFY `comment` TEXT CHARACTER SET cp1251 NULL DEFAULT NULL",
      "INSERT INTO `runRanges` (`id`, `runMin`, `runMax`, `comment`) VALUES (77, 900, 901, 0x98)"],  # 0x98 has no Unicode character in cp1251
     "runRanges", "comment", (77,)),
    ("ascii column holding bytes from 0x80", "mariadb",
     ["ALTER TABLE `runRanges` MODIFY `comment` TEXT CHARACTER SET ascii NULL DEFAULT NULL",
      "INSERT INTO `runRanges` (`id`, `runMin`, `runMax`, `comment`) VALUES (77, 900, 901, 0xE9)"],
     "runRanges", "comment", (77,)),
    ("TEXT value that no longer fits in utf8mb4", "both",
     ["ALTER TABLE `directories` MODIFY `comment` TEXT CHARACTER SET latin1 COLLATE latin1_swedish_ci NULL DEFAULT NULL",
      ("INSERT INTO `directories` (`id`, `name`, `parentId`, `authorId`, `comment`) VALUES (78, 'long_comment', 1, 2, :v)",
       {"v": "é" * 40000})],  # 40 000 bytes, 80 000 in utf8mb4
     "directories", "comment", (78,)),
    ("two directory names that become equal", "both",
     ["ALTER TABLE `directories` MODIFY `name` VARCHAR(255) CHARACTER SET latin1 COLLATE latin1_swedish_ci NOT NULL DEFAULT ''",
      ("INSERT INTO `directories` (`id`, `name`, `parentId`, `authorId`) VALUES (81, :a, 1, 2), (82, :b, 1, 2)",
       {"a": "Uber", "b": "Über"})],  # different in latin1_swedish_ci, equal in utf8mb4_general_ci
     "directories", "name", (81, 82)),
    ("two directory names that differ only by a trailing space at utf8mb4_0900_ai_ci", "mysql",
     # the collation is set here, not inherited from a server default that may be utf8mb4_general_ci
     ["ALTER TABLE `directories` MODIFY `name` VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL DEFAULT ''",
      "INSERT INTO `directories` (`id`, `name`, `parentId`, `authorId`) VALUES (83, 'test_vars ', 1, 2)"],
     "directories", "name", (3, 83)),  # 3 is the seed's 'test_vars'
    ("binary vault column", "both",
     ["ALTER TABLE `constantSets` MODIFY `vault` LONGBLOB NOT NULL"],
     "constantSets", "vault", ()),  # a declared type, no rows to name
]


@unittest.skipUnless(helper.ENV_TEST_MYSQL in os.environ, f"{helper.ENV_TEST_MYSQL} is not set")
class MySqlSchemaV6Test(SchemaV6TestCase):

    @classmethod
    def setUpClass(cls):
        cls.connection = os.environ[helper.ENV_TEST_MYSQL]
        version = query(cls.connection, "SELECT VERSION()")[0][0]
        cls.is_mariadb = "mariadb" in version.lower()
        cls.server_version = tuple(int(part) for part in re.match(r"(\d+)\.(\d+)\.(\d+)", version).groups())
        cls.mariadb_before_10_6_9 = cls.is_mariadb and cls.server_version < (10, 6, 9)
        cls.original_default = database_default(cls.connection)

    @classmethod
    def tearDownClass(cls):
        """Leaves the shared test database as `db init` creates it, as unit_test_upgrade_v6, unit_test_dedup and
        unit_test_rehash do, for the modules that run after this one"""
        cls.reset_database()
        run = run_cli(cls.connection, INIT)
        if not run.ok:
            raise RuntimeError(f"`{INIT}` after the schema 6 tests failed: {run.error!r}\n{run.output[-3000:]}")

    def setUp(self):
        self.reset_database()

    def tearDown(self):
        self.reset_database()

    @classmethod
    def reset_database(cls):
        drop_everything(cls.connection)
        charset, collation = cls.original_default
        execute(cls.connection, [f"ALTER DATABASE CHARACTER SET {charset} COLLATE {collation}"])

    def snapshot(self):
        """What a refused command must leave unchanged: the structure, every column's charset and collation, every
        table's engine, collation and row format, every row, the database default and the foreign keys"""
        return (compare.dump(self.connection, with_charset=True), mysql_charsets(self.connection),
                table_rows(self.connection), database_default(self.connection), foreign_keys(self.connection))

    def init_fresh(self):
        self.assert_ok(run_cli(self.connection, INIT))

    def upgrade(self):
        self.assert_ok(run_cli(self.connection, UPGRADE_MYSQL))

    def test_fresh_objects(self):
        """T1 (§2, §3): `db init` gives every schema 6 object, InnoDB, utf8mb4_general_ci columns, sha256 ascii_bin."""
        self.init_fresh()
        self.assertEqual(schema6_problems(compare.dump(self.connection), "mysql", fresh=True), [])
        self.assertEqual(mysql_charset_problems(mysql_charsets(self.connection)), [])
        self.assertEqual(schema_versions(self.connection), [(6,)])

    def test_seed_hashes(self):
        """T1 (§1, §4.2): the seed committed by `db init` carries sha256 and size equal to vault_digest."""
        from ccdb.model import vault_digest
        self.init_fresh()
        rows = query(self.connection, "SELECT id, vault, sha256, size FROM constantSets ORDER BY id")
        self.assertEqual({row[0]: row[1] for row in rows if row[0] in SEED_VAULTS}, SEED_VAULTS)
        for set_id, vault, sha256, size in rows:
            self.assertRegex(sha256, HEX64)
            self.assertEqual((sha256, size), vault_digest(vault), f"constant set {set_id}")

    def test_upgrade_equals_fresh(self):
        """T2 (§2, §3, §6.3): the frozen schema 5 upgraded equals fresh schema 6, COLLATION_NAME of every column included."""
        self.init_fresh()
        fresh_lines = dump(self.connection)
        fresh_info = mysql_charsets(self.connection)
        self.reset_database()
        build_v5_mysql(self.connection)
        self.upgrade()
        self.assertMultiLineEqual(dump_text(fresh_lines), dump_text(dump(self.connection)))
        upgraded_info = mysql_charsets(self.connection)
        self.assertEqual(collation_map(upgraded_info), collation_map(fresh_info))
        self.assertEqual({t: v[:2] for t, v in upgraded_info["tables"].items() if t not in LINK_TABLES},
                         {t: v[:2] for t, v in fresh_info["tables"].items()})
        self.assertEqual(schema_versions(self.connection), [(6,)])
        self.assertEqual(hash_problems(self.connection), [])
        self.assertIn("variationsToTags", table_names(self.connection))  # nothing is dropped (§2.4)

    def test_upgrade_idempotent(self):
        """T3 (§6.1, §6.2 item 1, §6.3): a second upgrade refuses on 6; a rerun at version 5 changes nothing."""
        build_v5_mysql(self.connection)
        self.upgrade()
        before = self.snapshot()

        # section 14.1: on version 6 the upgrade refuses, naming the version, and writes nothing
        message = self.assert_refused(run_cli(self.connection, UPGRADE_MYSQL))
        self.assert_names_version(message, 6)
        self.assertEqual(self.snapshot(), before)

        # the state after step 4 with the version not yet written: every step finds its work done. Section 14.1:
        # the upgrade writes no logs row (schemaVersions records it), so every row of every table is as before
        execute(self.connection, ["UPDATE schemaVersions SET schemaVersion = 5"])
        self.upgrade()
        self.assertEqual(self.snapshot(), before)

    def test_upgrade_variants(self):
        """T4 (§6.1): hallddb-shaped and CCDB 1.0 MySQL variants pass their criteria; version 4 is refused."""
        self.init_fresh()
        fresh_lines = dump(self.connection)

        with self.subTest("hallddb-shaped: InnoDB, latin1, tinyint(4), variations_has_tags, parentId default 0"):
            self.reset_database()
            build_v5_mysql(self.connection)
            fresh5_lines = dump(self.connection)
            self.reset_database()
            build_hallddb_shaped_v5(self.connection)
            hall5_lines = dump(self.connection)
            self.upgrade()
            upgraded_lines = dump(self.connection)
            other_v5_differences = {pair for pair in diff_pairs(fresh5_lines, hall5_lines)
                                    if not pair[1].startswith("table ")}  # table lines carry the engine
            self.assertEqual(sorted(diff_pairs(fresh_lines, upgraded_lines)), sorted(other_v5_differences))
            self.assertEqual(mysql_charset_problems(mysql_charsets(self.connection)), [])
            self.assertEqual(database_default(self.connection), ("utf8mb4", "utf8mb4_general_ci"))
            self.assertIn("variations_has_tags", table_names(self.connection))

        with self.subTest("CCDB 1.0 MySQL file: refused by the foreign-key stop, naming the constraints"):
            self.reset_database()
            build_v100_mysql(self.connection)
            self.assertEqual(schema_versions(self.connection), [(5,)])
            self.assertEqual({row[0] for row in foreign_keys(self.connection)}, set(V100_FOREIGN_KEYS))
            before = self.snapshot()
            message = self.assert_refused(run_cli(self.connection, UPGRADE_MYSQL))
            for constraint in V100_FOREIGN_KEYS:
                self.assertRegex(message, rf"\b{constraint}\b")
            self.assertEqual(self.snapshot(), before)  # the preflight writes nothing (§6.2)
            self.assertEqual(schema_versions(self.connection), [(5,)])

        with self.subTest("version 4 is refused"):
            self.reset_database()
            build_v5_mysql(self.connection)
            execute(self.connection, ["UPDATE schemaVersions SET schemaVersion = 4"])
            before = self.snapshot()
            message = self.assert_refused(run_cli(self.connection, UPGRADE_MYSQL))
            self.assert_names_version(message, 4)
            self.assertEqual(self.snapshot(), before)

    def test_upgrade_engine_and_charset(self):
        """T5 (§3, §6.3): engines, collations, converted bytes, TEXT, row format, zero dates and the lock clause of every ALTER."""
        build_v5_mysql(self.connection)
        cyrillic, units, latin = "Калибровка", "μs Ω", "Müller"
        setup = [
            "ALTER TABLE `directories` MODIFY `comment` TEXT CHARACTER SET latin1 COLLATE latin1_swedish_ci NULL DEFAULT NULL",
            ("UPDATE `directories` SET `comment` = :v WHERE `id` = 1", {"v": latin}),
            "ALTER TABLE `typeTables` MODIFY `comment` TEXT CHARACTER SET latin1 COLLATE latin1_bin NULL DEFAULT NULL",
            "ALTER TABLE `variations` MODIFY `comment` TEXT CHARACTER SET latin1 COLLATE latin1_general_cs NULL DEFAULT NULL",
            "ALTER TABLE `runRanges` MODIFY `comment` TEXT CHARACTER SET cp1251 NULL DEFAULT NULL",
            ("UPDATE `runRanges` SET `comment` = :v WHERE `id` = 1", {"v": cyrillic}),
            "ALTER TABLE `eventRanges` MODIFY `comment` TEXT CHARACTER SET utf8mb3 NULL DEFAULT NULL",
            ("UPDATE `eventRanges` SET `comment` = :v WHERE `id` = 1", {"v": units}),
            "ALTER TABLE `logs` ENGINE = InnoDB ROW_FORMAT = COMPACT",
            # `columns` then needs only its new column (the instant branch), `assignments` a column and an index
            "ALTER TABLE `columns` ENGINE = InnoDB, CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci",
            "ALTER TABLE `assignments` ENGINE = InnoDB, CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci",
            "ALTER TABLE `runRanges` ALTER COLUMN `created` SET DEFAULT '0000-00-00 00:00:00'",
            "UPDATE `runRanges` SET `created` = '0000-00-00 00:00:00' WHERE `id` = 3",
        ]
        execute(self.connection, setup, sql_mode="")
        types_before = {key: value[2] for key, value in mysql_charsets(self.connection)["columns"].items()}
        instant_before = self.instant_alter_count()

        with DriverStatements() as captured:  # through SQLAlchemy or a raw DB-API cursor alike
            self.upgrade()
        statements = captured.statements

        info = mysql_charsets(self.connection)
        self.assertEqual(mysql_charset_problems(info, bin_columns={("typeTables", "comment"), ("variations", "comment")}), [])
        self.assertEqual(info["columns"][("users", "name")][:2], ("utf8mb4", "utf8mb4_general_ci"))
        self.assertEqual({key: info["columns"][key][2] for key in types_before}, types_before, "a column changed its type")
        self.assertEqual(info["tables"]["logs"][2], "Dynamic")
        self.assertEqual(database_default(self.connection), ("utf8mb4", "utf8mb4_general_ci"))
        for table, value in (("directories", latin), ("runRanges", cyrillic), ("eventRanges", units)):
            self.assertEqual(query(self.connection, "SELECT HEX(`comment`) FROM `%s` WHERE `id` = 1" % table),
                             [(value.encode("utf-8").hex().upper(),)], f"bytes of {table}.comment")
        self.assertEqual(query(self.connection, "SELECT CAST(`created` AS CHAR) FROM `runRanges` WHERE `id` = 3"),
                         [("0000-00-00 00:00:00",)])
        self.assertEqual(schema_versions(self.connection), [(6,)])

        self.assert_lock_clauses([s for s in statements if LOCKED_DDL.match(s)])
        if self.is_mariadb:
            self.assertEqual(self.instant_alter_count(), instant_before, "a table was left in the instant format")

    def instant_alter_count(self):
        rows = query(self.connection, "SHOW GLOBAL STATUS LIKE 'Innodb_instant_alter_column'")
        return rows[0][1] if rows else None  # MySQL 8.3 has no such counter

    def assert_lock_clauses(self, statements):
        """The lock-clause table of §6.3 for the captured DDL"""
        self.assertTrue(statements, "no ALTER was captured")
        by_table = {}
        for statement in statements:
            flat = re.sub(r"\s+", " ", statement)  # the schema modules write their DDL across several lines
            normal = re.sub(r"\s*=\s*", "=", flat.upper())
            table = re.search(r"(?i)(?:ALTER TABLE|\bON) (?:`?\w+`?\.)?`?(\w+)`?", flat)
            by_table.setdefault(table.group(1) if table else "", []).append(normal)
            algorithm = re.search(r"ALGORITHM=(\w+)", normal)
            lock = re.search(r"LOCK=(\w+)", normal)
            with self.subTest(statement=statement):
                self.assertIsNotNone(algorithm, "names no ALGORITHM")
                if algorithm.group(1) == "COPY":
                    self.assertEqual(lock and lock.group(1), "SHARED")
                if algorithm.group(1) == "INPLACE":
                    self.assertEqual(lock and lock.group(1), "NONE")
                if "ENGINE=" in normal:
                    self.assertEqual(algorithm.group(1), "COPY", "an engine change")
                if self.mariadb_before_10_6_9:
                    self.assertNotEqual(algorithm.group(1), "INSTANT", "MDEV-18519")
                    if ADDS_COLUMN.search(normal) and algorithm.group(1) == "INPLACE":
                        self.assertIn("FORCE", normal, "MDEV-18519: adding columns rebuilds")
        for table, expected in (("columns", "INSTANT"), ("assignments", "INPLACE")):
            if table == "columns" and self.mariadb_before_10_6_9:
                expected = "INPLACE"
            self.assertIn(table, by_table, f"no ALTER of {table}")
            for normal in by_table[table]:
                self.assertIn("ALGORITHM=" + expected, normal, f"{table}: {normal}")
                if self.mariadb_before_10_6_9:
                    self.assertIn("FORCE", normal, f"{table}: {normal}")

    def test_upgrade_charset_stops(self):
        """T6 (§3, §6.2 item 5): each charset stop refuses before any change, naming the column."""
        for name, servers, statements, table, column, row_ids in CHARSET_STOPS:
            with self.subTest(name):
                if servers == "mariadb" and not self.is_mariadb:
                    self.skipTest("MySQL rejects these bytes in an ascii column")
                if servers == "mysql" and self.is_mariadb:
                    self.skipTest("MariaDB 10.5 has no utf8mb4_0900_ai_ci")
                self.reset_database()
                build_v5_mysql(self.connection)
                execute(self.connection, statements)
                before = self.snapshot()  # the database default too: §3 says before any change, ALTER DATABASE included
                message = self.assert_refused(run_cli(self.connection, UPGRADE_MYSQL))
                # section 14.1: the message names the table, the column and the number of rows, with up to 10 row ids
                self.assertRegex(message, rf"\b{table}\b")
                self.assertRegex(message, rf"\b{column}\b")
                for row_id in row_ids:
                    self.assertRegex(message, rf"\b{row_id}\b", f"row id {row_id} not named")
                self.assertEqual(self.snapshot(), before)
                self.assertEqual(schema_versions(self.connection), [(5,)])

    def test_version_check(self):
        """T7 (§4.1, §11): Python 2.5 accepts 6 and refuses 5, an empty, a doubled and a missing version table."""
        with self.subTest("a database without CCDB tables gives the no-structure message"):
            self.assert_no_structure(connect_error(self.connection))

        with self.subTest("schema 5 is refused with the message of §11"):
            self.reset_database()
            build_v5_mysql(self.connection)
            error = connect_error(self.connection)
            self.assertIsInstance(error, DatabaseStructureError)
            self.assertIn(V5_REFUSAL, str(error))

        with self.subTest("schema 6 is accepted"):
            self.reset_database()
            self.init_fresh()
            self.assertIsNone(connect_error(self.connection))
            self.assertEqual(schema_versions(self.connection), [(6,)])

        with self.subTest("an empty schemaVersions gives the no-structure message"):
            self.reset_database()
            self.init_fresh()
            execute(self.connection, ["DELETE FROM schemaVersions"])
            self.assert_no_structure(connect_error(self.connection))

        with self.subTest("two schemaVersions rows give the no-structure message"):
            self.reset_database()
            self.init_fresh()
            execute(self.connection, ["INSERT INTO schemaVersions (id, schemaVersion) VALUES (2, 6)"])
            self.assert_no_structure(connect_error(self.connection))

    def reader_connection_or_skip(self):
        """CCDB_TEST_MYSQL_READER_CONNECTION (section 14.1), which must name the database under test"""
        url = os.environ.get(ENV_MYSQL_READER)
        if not url:
            self.skipTest(f"{ENV_MYSQL_READER} is not set")
        reader, main = make_url(url), make_url(self.connection)
        self.assertEqual((reader.host, reader.port, reader.database), (main.host, main.port, main.database),
                         f"{ENV_MYSQL_READER} must name the database of {helper.ENV_TEST_MYSQL}")
        return url

    def test_init_commits(self):
        """T9 (§10, F8): `db init` commits the seed on InnoDB and exits non-zero on an error."""
        with self.subTest("the seed is committed on InnoDB"):
            self.init_fresh()
            # a new connection sees only committed rows
            tables = mysql_charsets(self.connection)["tables"]
            self.assertEqual({t: v[0] for t, v in tables.items()}, {t: "InnoDB" for t in SCHEMA6_TABLES})
            self.assertEqual(query(self.connection, "SELECT COUNT(*) FROM constantSets"), [(5,)])
            self.assertEqual(query(self.connection, "SELECT COUNT(*) FROM assignments"), [(5,)])
            self.assertEqual(query(self.connection, "SELECT name FROM users ORDER BY id"), [("anonymous",), ("test_user",)])
            self.assertEqual(schema_versions(self.connection), [(6,)])

        with self.subTest("an error exits non-zero"):
            reader = self.reader_connection_or_skip()
            self.reset_database()
            # ccdb_reader may only SELECT, so init fails on its first DDL, whatever it drops or creates first
            self.assert_refused(run_cli(reader, INIT))
            self.assertEqual(table_names(self.connection), set())


if __name__ == "__main__":
    unittest.main()
