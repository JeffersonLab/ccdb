"""@package AlchemyProvider
Documentation for this module.

More details.
"""

import re
import os
import logging

from ccdb.path_utils import parse_request, ParseRequestResult
from .model import CcdbSchemaVersion
from . import path_utils
from datetime import datetime, timezone

import sqlalchemy
from sqlalchemy import select, func, exists, or_
from sqlalchemy.exc import OperationalError, ProgrammingError, IntegrityError, DBAPIError
import sqlalchemy.orm
from sqlalchemy.orm import contains_eager
from sqlalchemy.orm.attributes import set_committed_value
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound, ObjectDeletedError
from sqlalchemy.orm.util import identity_key
from sqlalchemy.sql.expression import desc
from .model import Directory, TypeTable, TypeTableColumn, ConstantSet, Assignment, RunRange, Variation, User, LogRecord
from .model import Property, Tag
from .model import vault_digest, list_to_blob, gen_flatten_data
from .errors import ObjectIsNotFoundInDbError, AnonymousUserForbiddenError, DatabaseStructureError, UserNotFoundError, \
    UserExistsError, DataCollisionError, SessionHasPendingChangesError

from .table_file import TextFileDOM
from .authentication import Authentication

import posixpath

log = logging.getLogger("ccdb.provider")

# The database schema version this CCDB version reads and writes, and nothing else
SCHEMA_VERSION = 6

# MySQL and MariaDB errors after which a write transaction is rolled back and run again from its start:
# InnoDB chose it as the victim of a deadlock (1213), or a row lock did not come within innodb_lock_wait_timeout (1205).
# Writers that share constant sets lock them, and two of them can wait for each other; the restarted call is correct
RESTARTABLE_MYSQL_ERRORS = (1213, 1205)
MAX_TRANSACTION_RESTARTS = 3

# logs.description holds at most this many characters
LOG_DESCRIPTION_LENGTH = 255


class _ConstantSetIdChanged(Exception):
    """A locking re-read found an assignment on another constant set than the plain read before it.

    `ccdb db dedup` does that when it merges equal sets into the oldest one. The write transaction is rolled back and
    restarted, so it locks the set the assignment uses now.
    """


def hide_password(text, connection_string=None):
    """
    Masks a database password for logs and messages: 'mysql://user:secret@host/db' → 'mysql://user:***@host/db'

    With one argument, text is a connection string. With connection_string given, text is any message
    (an exception text, for example) and every copy of that connection string and its password in it is masked.
    The mask reaches up to the last '@', so a password with an unescaped '@' is hidden whole.
    """
    pattern = re.compile(r"^([A-Za-z0-9+.\-]+://[^:/@]*:).*@")
    if connection_string is None:
        return pattern.sub(r"\1***@", text)
    masked = text.replace(connection_string, hide_password(connection_string))
    try:
        password = sqlalchemy.engine.make_url(connection_string).password
    except Exception:
        password = None
    if password:
        masked = masked.replace(password, "***")
    return masked


class AlchemyProvider:
    """
    CCDB data provider that uses SQLAlchemy for accessing databases
    """

    error_parse_value_message = "Error parsing data value. " \
                                "Column '{0}' column_index='{1}' row_index='{2}'. " \
                                "The type of column is '{3}'. The value='{4}'"

    def __init__(self):
        self._is_connected = False
        self._are_dirs_loaded = False
        self.dirs_by_id = {}
        self.dirs_by_path = {}
        self.root_dir = Directory()
        self.root_dir.path = '/'
        self.root_dir.name = ''
        self.root_dir.id = 0
        self.path_name_regex = re.compile(r'^[\w\-_]+$', re.IGNORECASE)
        self._connection_string = ""
        self._auth = Authentication(self)
        self._auth.current_user_name = "anonymous"
        self.logging_enabled = True
        self.engine = None  # is set after connect function
        self.session = None  # is set after connect function
        self._owns_engine = False  # True when connect() created the engine, so disconnect() disposes it
        self._no_structure_message = "No database structure found. Possibly you are trying to connect " + \
                                     "to wrong SQLite file or to MySQL database without schema. " + \
                                     "Original SqlAlchemy error is: " + os.linesep + os.linesep + "{0}"

    # ------------------------------------------------
    #  Connects to database using connection string
    # ------------------------------------------------
    def connect(self, connection_string="", check_version=True):
        """
        Connects to database using connection string

        connection string might be in form:
        mysql://<username>:<password>@<mysql.address>:<port> <database>
        sqlite:///path/to/file.sqlite

        :param connection_string: connection string
        :param check_version: Instantly check the schema version
        :type connection_string: str
        :raises RuntimeError: the provider is connected already; call disconnect() first
        """
        if self._is_connected:
            raise RuntimeError("connect() called on a provider that is connected already; call disconnect() first")

        # Schema 6 text is utf8mb4. PyMySQL uses it by default, but mysqlclient, which
        # 'mysql://' tries first, would use its library default; so the charset is pinned for both drivers.
        engine_options = {"connect_args": {"charset": "utf8mb4"}} if connection_string.startswith("mysql") else {}
        try:
            engine = sqlalchemy.create_engine(connection_string, **engine_options)
        except ImportError as err:
            # sql alchemy uses MySQLdb by default. But it might not be installed in the system
            # in such case we fallback to mysqlconnector which is included in CCDB
            if connection_string.startswith("mysql://") \
                    and "No module named" in repr(err) \
                    and "MySQLdb" in repr(err):
                connection_string = connection_string.replace("mysql://", "mysql+pymysql://")
                engine = sqlalchemy.create_engine(connection_string, **engine_options)
            else:
                raise

        session_type = sqlalchemy.orm.sessionmaker(bind=engine)
        session = session_type()

        try:
            self.attach(engine, session, check_version)
        except Exception:
            # nobody else holds this session and engine. The attach error is what the caller needs,
            # so a failing cleanup is only logged: raising here would replace that error
            for cleanup in (session.close, engine.dispose):
                try:
                    cleanup()
                except Exception as cleanup_error:
                    log.warning("Cleanup after a failed connect raised: %r", cleanup_error)
            raise
        self._owns_engine = True
        self._connection_string = connection_string

    # ------------------------------------------------
    #  Attaches to an existing engine and session
    # ------------------------------------------------
    def attach(self, engine, session, check_version=True):
        """
        Uses an existing SQLAlchemy engine and session instead of opening a new connection.

        A web server keeps one engine (connection pool) per process and gives each request its own
        session; connect() would build a new engine and pool on every call. The caller owns both
        objects: it creates them and closes or removes the session. disconnect() marks the provider
        as disconnected and closes the session, which keeps a scoped session reusable.

        :param engine: engine the session is bound to
        :type engine: sqlalchemy.engine.Engine
        :param session: session bound to that engine; a scoped_session registry is accepted
        :type session: sqlalchemy.orm.Session | sqlalchemy.orm.scoped_session
        :param check_version: Instantly check the schema version
        :raises TypeError: engine or session has the wrong type
        :raises ValueError: the session has no bind or is bound to another engine
        :raises RuntimeError: the provider is connected already; call disconnect() first
        :raises DatabaseStructureError: the database has no CCDB schema or the wrong schema version
        """
        if not isinstance(engine, sqlalchemy.engine.Engine):
            raise TypeError(f"attach() expects 'engine' to be a sqlalchemy.engine.Engine, got {type(engine).__name__}")
        if not isinstance(session, (sqlalchemy.orm.Session, sqlalchemy.orm.scoped_session)):
            raise TypeError(f"attach() expects 'session' to be a sqlalchemy.orm.Session or scoped_session, got {type(session).__name__}")
        try:
            bound_engine = session.get_bind()
        except sqlalchemy.exc.UnboundExecutionError:
            raise ValueError("attach() expects a session bound to the given engine, but the session has no bind")
        if bound_engine is not engine:
            raise ValueError("attach() expects the session to be bound to the given engine, "
                             f"but it is bound to {bound_engine}")
        if self._is_connected:
            raise RuntimeError("attach() called on a provider that is connected already; call disconnect() first")
        if check_version:
            self._check_schema_version(session)  # before any state changes: a failed attach leaves the provider untouched

        self.engine = engine
        self.session = session
        self._owns_engine = False  # the caller owns the engine; connect() sets True for its own
        self._is_connected = True
        self._connection_string = engine.url.render_as_string(hide_password=False)

        # the data behind a new engine may differ, so directories are reloaded on demand
        self._are_dirs_loaded = False

    def _check_schema_version(self, session):
        """Raises DatabaseStructureError unless the database behind the session has CCDB schema version 6.

        schemaVersions must hold exactly one row. An empty table, two rows or no table at all mean the database
        has no CCDB structure this version can trust, and get the 'No database structure found' message.
        """
        # A session given to attach() belongs to the caller and may hold pending changes: the query must not flush
        # them, and only a transaction the check itself began is ended. A scoped_session registry is asked for its
        # current session, since scoped_session does not proxy in_transaction().
        if isinstance(session, sqlalchemy.orm.scoped_session):
            session = session()
        had_transaction = session.in_transaction()
        try:
            with session.no_autoflush:
                versions = [record.version for record in session.query(CcdbSchemaVersion).all()]
        except (OperationalError, ProgrammingError) as err:
            # SQLite: 'no such table' (OperationalError); MySQL and MariaDB: error 1146 (ProgrammingError)
            error_code = err.orig.args[0] if err.orig is not None and err.orig.args else None
            if "no such table" in str(err) or error_code == 1146:
                raise DatabaseStructureError(self._no_structure_message.format(err))
            raise
        finally:
            # the check must not leave a transaction open: on MySQL it would hold a metadata lock on schemaVersions
            if not had_transaction:
                session.rollback()

        if len(versions) != 1:
            raise DatabaseStructureError(self._no_structure_message.format(
                f"The schemaVersions table holds {len(versions)} rows; exactly one is expected"))
        version = versions[0]
        if version == 5:
            raise DatabaseStructureError(
                f"The database schema version is 5. This CCDB version works with schema version {SCHEMA_VERSION}. "
                "Upgrade with 'ccdb db upgrade' (docs/deployment/upgrade-2.5.md)")
        if version != SCHEMA_VERSION:
            raise DatabaseStructureError(
                f"Version mismatch. The database schema version is '{version}'. "
                f"This CCDB version works with schema version {SCHEMA_VERSION}")

    # ------------------------------------------------
    # Closes connection to data
    # ------------------------------------------------
    def disconnect(self):
        """
        Closes the session. Disposes the engine (its connection pool) when connect() created it;
        an engine given to attach() belongs to the caller and stays open.
        Safe to call on a provider that never connected or whose connect() failed.
        """
        self._is_connected = False
        if self.session is not None:
            self.session.close()
        if self._owns_engine and self.engine is not None:
            self.engine.dispose()
        self._owns_engine = False

    # -------------------------------------------------
    # indicates ether the connection is open or not
    # -------------------------------------------------
    @property
    def is_connected(self):
        """
        indicates ether the connection is open or not

        :return: bool True if connection is opened
        :rtype: bool
        """
        return self._is_connected

    # ------------------------------------------------
    # Connection string that was used
    # ------------------------------------------------
    @property
    def connection_string(self):
        """
        Connection string that was used on last connect()

        :return: connection string
        :rtype: str
        """
        return self._connection_string

    # ----------------------------------------------------------------------------------------
    #   D I R E C T O R Y   M A N G E M E N T
    # ----------------------------------------------------------------------------------------

    # ------------------------------------------------
    # Gets directory by its full path
    # ------------------------------------------------
    def get_directory(self, path):
        """
        Gets directory by its full path

        :param path: Full path of the directory
        :type path: str
        :return: Directory object if directory exists, NULL otherwise
        :rtype: Directory
        """
        self._ensure_dirs_loaded()

        # Better reporting for empty path
        if not path:
            raise ValueError(f"Can't get directory as 'path' is null or empty: '{path}'")

        # we don't have this directory
        if path not in self.dirs_by_path:
            raise ObjectIsNotFoundInDbError(Directory, "Can't find the directory with path '{0}'".format(path))

        return self.dirs_by_path[path]

    # ------------------------------------------------
    # return reference to root directory
    # ------------------------------------------------
    def get_root_directory(self):
        """
        return reference to root directory

        @warning User should not delete this object

        :return:reference to root directory
        :rtype: Directory
        """
        self._ensure_dirs_loaded()
        return self.root_dir

    # ------------------------------------------------
    # Gets subdirectories of a directory
    # ------------------------------------------------
    def get_directories(self, dir_obj_or_path="/", include_deprecated=True):
        """
        Gets the subdirectories of a directory, as the directory tree holds them

        :param dir_obj_or_path: parent Directory object or its full path
        :type dir_obj_or_path: str or Directory

        :param include_deprecated: False leaves deprecated directories out
        :type include_deprecated: bool

        :return: subdirectories of the directory
        :rtype: [] of Directory
        """
        self._ensure_dirs_loaded()

        if isinstance(dir_obj_or_path, str):
            parent_dir = self.get_directory(dir_obj_or_path)
        else:
            assert isinstance(dir_obj_or_path, Directory)
            parent_dir = dir_obj_or_path

        if include_deprecated:
            return list(parent_dir.sub_dirs)
        return [sub_dir for sub_dir in parent_dir.sub_dirs if not sub_dir.is_deprecated]

    # ------------------------------------------------
    # Searches directories that matches the pattern
    # ------------------------------------------------
    def search_directories(self, searchPattern, parentPath="", limit=0, offset=0, include_deprecated=True):
        """
        Searches directories that matches the pattern
        inside parent directory with path parentPath
        or globally through all type tables if parentPath is empty
        The pattern might contain wildcard characters:
        '*' - any character sequence
        '?' - any single character

        :param searchPattern: Pattern to search. May have wildcards '*' and '?'
        :type searchPattern: str

        :param parentPath: Parent path. If empty search through all directories
        :type parentPath: str

        :param limit: number of records to select. 0 means select all records
        :type limit: int

        :param offset: record number to start with
        :type offset: int

        :param include_deprecated: False leaves deprecated directories out
        :type include_deprecated: bool

        :return: Directories to find
        :rtype: [] of Directory
        """

        self._ensure_dirs_loaded()

        searchPattern = searchPattern.replace("_", "\\_").replace("*", "%").replace("?", "_")

        query = self.session.query(Directory).filter(Directory.name.like(searchPattern, escape="\\"))

        if parentPath != "":
            parent_dir = self.dirs_by_path[parentPath]
            query = query.filter(Directory.parent_id == parent_dir.id)

        if not include_deprecated:
            query = query.filter(_not_deprecated(Directory))

        if limit != 0:
            query = query.limit(limit)
        if offset != 0:
            query = query.offset(offset)

        result = query.all()

        return result

    # ------------------------------------------------
    # Creates directory using parent path
    # ------------------------------------------------
    def create_directory(self, new_dir_name, parent_dir_or_path, comment=""):
        """
        Creates directory using parent with parentDirFullPath

        :param new_dir_name: Name of the directory. May contain only A-Z, a-z,0-9, _, -,
        :type new_dir_name:str
        :param parent_dir_or_path: Path of the parent directory
        :type parent_dir_or_path: str
        :param comment: comment on this dir. Might be None
        :type comment:
        :return: new created Directory
        :rtype: Directory
        """
        self._ensure_dirs_loaded()

        # get parent directory
        if isinstance(parent_dir_or_path, str):
            parent_dir = self.dirs_by_path[parent_dir_or_path]
        else:
            assert (isinstance(parent_dir_or_path, Directory))
            parent_dir = parent_dir_or_path

        # check if no such directory exists
        new_full_path = posixpath.join(parent_dir.path, new_dir_name)
        if new_full_path in self.dirs_by_path:
            raise ValueError("The directory with path '{0}' already exist".format(new_full_path))

        # Get user
        user = self.get_current_user()

        if user.name == 'anonymous':  # anonymous user can't create directories

            raise AnonymousUserForbiddenError
        else:

            # create the directory
            directory = Directory()
            directory.name = new_dir_name
            if comment != "":
                directory.comment = comment
            else:
                directory.comment = None
            directory.parent_dir = parent_dir
            directory.parent_id = parent_dir.id
            parent_dir.sub_dirs.append(directory)
            directory.author_id = user.id

            # add to database
            self.session.add(directory)
            self.session.commit()

            # add log
            self.create_log_record(user=user,
                                   affected_ids=[directory.__tablename__ + str(directory.id)],
                                   action="create",
                                   description="Created directory '{0}'".format(new_full_path),
                                   comment=directory.comment)

            # refresh directory structure
            self._load_dirs()

            return directory

    def get_directory_by_id(self, dir_id):
        """
        Gets Directory by its database id

        :raises ObjectIsNotFoundInDbError: no directory has this id
        :rtype: Directory
        """
        self._ensure_dirs_loaded()
        try:
            return self.dirs_by_id[dir_id]
        except KeyError:
            raise ObjectIsNotFoundInDbError(Directory, "Directory with id='{0}' is not found in the DB".format(dir_id))

    def get_type_table_by_id(self, table_id):
        """
        Gets TypeTable by its database id, with parent_dir set so that table.path is complete

        :raises ObjectIsNotFoundInDbError: no table has this id
        :rtype: TypeTable
        """
        try:
            type_table = self.session.query(TypeTable).filter(TypeTable.id == table_id).one()
        except NoResultFound:
            raise ObjectIsNotFoundInDbError(TypeTable, "TypeTable with id='{0}' is not found in the DB".format(table_id))

        # parent_dir comes from the directory cache: only there do directories carry their full paths.
        # Set as the committed value, so this read records no change the session would count as pending
        set_committed_value(type_table, "parent_dir", self.get_directory_by_id(type_table.parent_dir_id))
        return type_table

    # @brief Updates directory
    #
    # @warning in current realization, if operation succeeded
    # the directories structure will be rebuilt. This mean that
    # (!) all previous pointers to DDirectory objects except Root Directory
    # will become deleted => unusable
    #
    # @param [in] ccdb.Directory object - Directory to update
    # @return bool True if success
    #
    def update_directory(self, directory):
        """Updates directory"""
        self._ensure_dirs_loaded()

        # get user or get user error if there is no user
        user = self.get_current_user()

        self.session.commit()

        # Log
        self.create_log_record(user,
                               affected_ids=[directory.__tablename__ + directory(directory.id)],
                               action="update",
                               description="Updated directory '{0}'".format(directory.path),
                               comment=directory.comment)

        # refresh directory structure
        self._load_dirs()

    # ------------------------------------------------
    # Deletes directory using path or Directory obj
    # ------------------------------------------------
    # noinspection PyUnresolvedReferences
    def delete_directory(self, dir_or_path):
        """
        Deletes directory using parent path or Directory object

        :param dir_or_path:parent path or Directory object
        :type dir_or_path: str or Directory
        :return: None
        """

        self._ensure_dirs_loaded()

        # get user here to fail if no such user
        user = self.get_current_user()

        # check the type
        if isinstance(dir_or_path, str):
            directory = self.get_directory(dir_or_path)
        else:
            assert (isinstance(dir_or_path, Directory))
            directory = dir_or_path

        if len(directory.sub_dirs) != 0 or len(directory.type_tables) != 0:
            err_message = "Directory '{0}' contains {1} subdirectories and {2} tables." + \
                          "Impossible to delete directory which contains another directories or tables"
            err_message = err_message.format(directory.path, len(directory.sub_dirs), len(directory.type_tables))
            raise ValueError(err_message)

        # the properties of the directory are deleted with it, in one transaction
        directory_id, directory_path, directory_comment = directory.id, directory.path, directory.comment
        try:
            properties_count = self._delete_properties_of("directory", [directory_id])
            self.session.delete(directory)
            self.session.commit()
        except Exception:
            self._rollback_quietly()
            raise

        # refresh directory structure
        self._load_dirs()

        # Log
        self.create_log_record(user,
                               affected_ids=[Directory.__tablename__ + str(directory_id)],
                               action="delete",
                               description=self._with_properties_note(
                                   "Deleted directory '{0}'".format(directory_path), properties_count),
                               comment=directory_comment)

    # ------------------------------------------------
    # Load all directories
    # ------------------------------------------------
    def _load_dirs(self):
        try:
            self.dirs_by_id = self._get_dirs_by_id_dic(self.session.query(Directory).all())
        except OperationalError as err:
            if 'no such table' in str(err):
                raise DatabaseStructureError(self._no_structure_message.format(err))
            else:
                raise

        self.dirs_by_path = self._structure_dirs(self.dirs_by_id)
        self._are_dirs_loaded = True

    # ------------------------------------------------
    # Structure directories by hierarchy
    # ------------------------------------------------
    def _structure_dirs(self, directories):
        """
        :type directories: {} dictionary with dir.id as a key
        """
        assert (isinstance(directories, type({})))

        # clear the full path dictionary
        dirs_by_full_path = {self.root_dir.path: self.root_dir}

        # clear subdirectories to append them from the beginning in the next step
        for directory in directories.values():
            directory.sub_dirs = []

        # root dir is artificial (not from database).
        # have to clear it
        self.root_dir.sub_dirs = []

        # begin loop through the directories
        for directory in directories.values():
            assert (isinstance(directory, Directory))

            parent_dir = self.root_dir

            # and check if it have parent directory
            if directory.parent_id > 0:
                # this directory must have a parent! so now search it
                parent_dir = directories[directory.parent_id]

            parent_dir.sub_dirs.append(directory)
            directory.path = posixpath.join(parent_dir.path, directory.name)
            directory.parent_dir = parent_dir
            dirs_by_full_path[directory.path] = directory

        return dirs_by_full_path

    # ------------------------------------------------
    # create dictionary by directory id
    # ------------------------------------------------
    def _get_dirs_by_id_dic(self, dirs):
        result = {}
        for directory in dirs:
            assert (isinstance(directory, Directory))
            result[directory.id] = directory

        return result

    # ------------------------------------------------
    # Checks that directory structure is loaded
    # and ready for use. Loads everything if not
    # ------------------------------------------------
    def _ensure_dirs_loaded(self):
        if not self._are_dirs_loaded:
            self._load_dirs()

    # ----------------------------------------------------------------------------------------
    #   C O N S T A N T   T Y P E   T A B L E
    # ----------------------------------------------------------------------------------------

    # ------------------------------------------------
    # Gets TypeTable from the DB by absolute path
    # ------------------------------------------------
    def get_type_table(self, exact_path):
        """
        Gets TypeTable from the DB by absolute path
        :param exact_path: absolute path of the type table
        :type exact_path: str
        :return: TypeTable that matches this path
        :rtype: TypeTable
        """
        self._ensure_dirs_loaded()  # even with self.get_directory do not remove it

        # Better reporting for empty path
        if not exact_path:
            raise ValueError(f"Can't get type table as 'exact_path' path variable is null or empty: '{exact_path}'")

        parent_dir_path = posixpath.dirname(exact_path)
        table_name = posixpath.basename(exact_path)
        parent_dir = self.get_directory(parent_dir_path)

        query = self.session.query(TypeTable).filter(TypeTable.name == table_name,
                                                     TypeTable.parent_dir_id == parent_dir.id)

        try:
            table = query.one()
        except sqlalchemy.orm.exc.NoResultFound:
            message = "No type table found by exact path: '{0}'".format(exact_path)
            raise ObjectIsNotFoundInDbError(TypeTable, message)

        return table

    # ------------------------------------------------
    # Get all tables in the directory
    # ------------------------------------------------
    def get_type_tables(self, dir_obj_or_path, include_deprecated=True):
        """
        Get all tables in the directory

        :param dir_obj_or_path: directory or path to directory where to look
        :type dir_obj_or_path: str or Directory
        :param include_deprecated: False leaves deprecated tables out
        :type include_deprecated: bool
        :return: [] of TypeTables for the directory
        :rtype: [] of TypeTable
        """
        self._ensure_dirs_loaded()

        if isinstance(dir_obj_or_path, str):
            parent_dir = self.get_directory(dir_obj_or_path)
        else:
            assert isinstance(dir_obj_or_path, Directory)
            parent_dir = dir_obj_or_path

        query = self.session.query(TypeTable).filter(TypeTable.parent_dir_id == parent_dir.id)
        if not include_deprecated:
            query = query.filter(_not_deprecated(TypeTable))
        return query.all()

    # ------------------------------------------------
    # Searches for type tables that matches the patten
    # ------------------------------------------------
    def search_type_tables(self, pattern, dir_obj_or_path=None, limit=0, offset=0, include_deprecated=True):
        """
        Searches for type tables that matches the patten

        inside parent directory with path @see parentPath
        or globally through all type tables if parentPath is empty
        The pattern might contain
        '*' - any character sequence
        '?' - any single character

        :param pattern: Search pattern. May contain with wildcard '*' and '?' symbols
        :type pattern: str

        :param dir_obj_or_path: parent Directory object, full path of parent directory or None if
        :type dir_obj_or_path: str, Directory, None

        :param limit: number of records to select. 0 means select all records
        :type limit: int

        :param offset: record number to start with
        :type offset: int

        :param include_deprecated: False leaves deprecated tables out
        :type include_deprecated: bool

        :return: found TypeTables
        :rtype: []
        """

        self._ensure_dirs_loaded()

        # prepare search pattern for SQL
        pattern = pattern.replace("_", "\\_").replace("*", "%").replace("?", "_")

        # initial query
        query = self.session.query(TypeTable).filter(TypeTable.name.like(pattern, escape="\\"))

        # does parent directory specified?
        parent_dir = None
        if dir_obj_or_path is not None:
            self._ensure_dirs_loaded()

            if isinstance(dir_obj_or_path, str) and dir_obj_or_path != "":
                parent_dir = self.get_directory(dir_obj_or_path)
            else:
                assert isinstance(dir_obj_or_path, Directory)
                parent_dir = dir_obj_or_path

        # add parent directory to query
        if parent_dir is not None:
            query = query.filter(TypeTable.parent_dir_id == parent_dir.id)

        if not include_deprecated:
            query = query.filter(_not_deprecated(TypeTable))

        # add limits to query
        if limit != 0: query = query.limit(limit)
        if offset != 0: query = query.offset(offset)

        # execute and return
        return query.all()

    # --------------------------------------------------
    # Counts number of type tables for a given directory
    # --------------------------------------------------
    def count_type_tables(self, dir_obj_or_path):
        """
        Counts number of type tables for a given directory

        :param dir_obj_or_path: parent directory or full path of parent directory
        :type dir_obj_or_path: str or Directory

        :return: number of type tables in a directory
        :rtype: int
        """

        self._ensure_dirs_loaded()

        if isinstance(dir_obj_or_path, str):
            parent_dir = self.get_directory(dir_obj_or_path)
        else:
            assert isinstance(dir_obj_or_path, Directory)
            parent_dir = dir_obj_or_path

        return self.session.query(TypeTable).filter(TypeTable.parent_dir_id == parent_dir.id).count()

    # --------------------------------------------------
    # Creates constant table in database
    # --------------------------------------------------
    def create_type_table(self, name, dir_obj_or_path, rows_num, columns, comment=""):
        """@brief Creates constant table in database

             Creates  constants type table in database and returns reference to
             created table if operation is succeeded (NULL otherwise)

             The map "columns" should contains [("name1", "type"), ("name2", "type", "units"),...] tuples where:
              -- "name" is the name of the column.
                  Should have the same naming conventions
                  as names of directories and type tables  @see ValidateName()
              -- "type" is the type of the column
                 might be: int, uint, long, ulong, double, bool, string
                 other values will lead to "double" type to be used.
                 @see ccdb::ConstantsTypeColumn::StringToType
                 Thus <"px", "">, <"py", ""> will create two double typed columns
              -- "units" is optional, free text of at most 64 characters, e.g. "MeV".
                 A pair without it, None or "" leave the column without units

             @param [in] name:              name of the new constants type table
             @param [in] dir_obj_or_path:   parent directory path or ccdb.model.Directory
             @param [in] rows_num:          Number of rows
             @param [in] columns:           a list of (name, type) or (name, type, units) tuples
             @param [in] comment:           description for this type table
             @return: NULL if failed, pointer to created object otherwise
        """

        assert len(columns) > 0
        assert rows_num > 0

        # The units column is VARCHAR(64); MySQL in non-strict mode would silently truncate a longer string
        for column_def in columns:
            if len(column_def) > 2 and column_def[2] and len(column_def[2]) > 64:
                raise ValueError("Units of column '{0}' are longer than 64 characters: '{1}'"
                                 .format(column_def[0], column_def[2]))
            if len(column_def) > 2 and column_def[2] and ('\r' in column_def[2] or '\n' in column_def[2]):
                raise ValueError("Units of column '{0}' can not contain line breaks: {1!r}"
                                 .format(column_def[0], column_def[2]))

        self._ensure_dirs_loaded()

        if isinstance(dir_obj_or_path, str):
            parent_dir = self.get_directory(dir_obj_or_path)
        else:
            assert isinstance(dir_obj_or_path, Directory)
            parent_dir = dir_obj_or_path

        # check, if the table already exists
        data_count = self.session.query(TypeTable).filter(TypeTable.parent_dir_id == parent_dir.id).filter(
            TypeTable.name == name).count()
        if data_count > 0:
            message = "Can't create a type table. Such table already exists in this directory"
            raise ValueError(message)

        # get user
        user = self.get_current_user()

        if user.name == 'anonymous':  # anonymous user can't create table types

            raise AnonymousUserForbiddenError
        else:
            table = TypeTable()
            table.name = name
            table.comment = comment
            table.rows_count = rows_num
            table.parent_dir = parent_dir
            table.parent_dir_id = parent_dir.id
            table.author_id = user.id

            for i, column_def in enumerate(columns):
                # (name, type) pairs stay valid, so callers written before units existed keep working
                name, col_type = column_def[0], column_def[1]
                units = column_def[2] if len(column_def) > 2 else None
                column = TypeTableColumn()
                column.name = name
                column.order = i
                col_type = col_type or 'double'
                column.type = col_type
                column.units = units or None
                table.columns.append(column)

            table._columns_count = len(columns)

            self.session.add(table)
            self.session.commit()

            # add log
            self.create_log_record(user=user,
                                   affected_ids=[table.__tablename__ + str(table.id)],
                                   action="create",
                                   description="Created table with path '{0}'".format(table.path),
                                   comment=table.comment)

            return table

    # ------------------------------------------------
    # Updates constant table in database
    # ------------------------------------------------
    def update_type_table(self, type_table):

        # get user here to fail if no such user
        user = self.get_current_user()

        self.session.commit()

        # Log
        self.create_log_record(user=user,
                               affected_ids=[type_table.__tablename__ + str(type_table.id)],
                               action="update",
                               description="Updated table with path '{0}'".format(type_table.path),
                               comment=type_table.comment)

    # ------------------------------------------------
    # Deletes constant type table
    # ------------------------------------------------
    def delete_type_table(self, type_table):
        """
        @brief Deletes constant type table

        Deletes constant type table.
        The type table will not be deleted if any assignment for this table exists
        Used should delete assignments first and only than delete the type table.
        Constant sets of the table that no assignment uses are deleted with it.

        One transaction: the table's row is locked first (FOR UPDATE), so no create_assignment can add data to the
        table while the assignments are counted and the sets and the table are deleted. On a deadlock or lock
        timeout the transaction is restarted.

        :param type_table:   table table info
        :type type_table: TypeTable
        :raises ValueError: the table has assignments
        :raises ObjectIsNotFoundInDbError: the table is already gone
        """
        assert isinstance(type_table, TypeTable)

        # get user here to fail if no such user
        user = self.get_current_user()
        table_id, table_path, table_comment = type_table.id, type_table.path, type_table.comment

        def attempt():
            self._begin_write_transaction()
            self._lock_type_table(table_id, table_path, for_update=True)

            # A locking read: it sees assignments committed while this call waited for the table lock
            assignments_count = self.session.execute(
                select(func.count(Assignment.id))
                .join(ConstantSet, ConstantSet.id == Assignment.constant_set_id)
                .where(ConstantSet.type_table_id == table_id)
                .with_for_update(read=True)).scalar()
            if assignments_count > 0:
                message = ("Can't delete type table that has data assigned to it. "
                           "The type table '{0}' with id '{1}' has {2} assignments. "
                           "Please, delete the assignments first").format(table_path, table_id, assignments_count)
                raise ValueError(message)

            # The sets left are unused: rm -a deletes a set with its last assignment, older CCDB versions did not
            sets_table, assignments_table = ConstantSet.__table__, Assignment.__table__
            # Under the table lock with no assignment counted, every set of the table is unused; their ids are read
            # only to take the deleted sets out of the session
            unused_set_ids = self.session.execute(
                select(sets_table.c.id).where(sets_table.c.constantTypeId == table_id)).scalars().all()
            self.session.execute(
                sets_table.delete()
                .where(sets_table.c.constantTypeId == table_id)
                .where(~exists().where(assignments_table.c.constantSetId == sets_table.c.id)))
            for set_id in unused_set_ids:
                self._forget_constant_set(set_id)

            # The properties of the table and of its columns go with them. The column ids are read before the
            # cascade below deletes the columns
            column_ids = self.session.execute(
                select(TypeTableColumn.id).where(TypeTableColumn.type_table_id == table_id)).scalars().all()
            properties_count = self._delete_properties_of("table", [table_id]) \
                + self._delete_properties_of("column", column_ids)

            # Deleting the table through the ORM deletes its columns too (cascade). For TypeTable.constant_sets the
            # ORM would set constantTypeId to NULL in every set the collection holds; expired, it is reloaded at the
            # flush and is empty now
            self.session.expire(type_table, ["constant_sets"])
            self.session.delete(type_table)
            self.session.flush()

            self.create_log_record(user=user,
                                   affected_ids=[TypeTable.__tablename__ + str(table_id)],
                                   action="delete",
                                   description=self._with_properties_note(
                                       "Deleted table with path '{0}'".format(table_path), properties_count),
                                   comment=table_comment,
                                   commit=False)
            self.session.commit()

        self._run_write_transaction(attempt)

    # ----------------------------------------------------------------------------------------
    #   R U N   R A N G E S
    # ----------------------------------------------------------------------------------------
    # ------------------------------------------------
    # GetRun Range from db by name or max and min run
    # ------------------------------------------------
    def get_run_range(self, min_run, max_run, name=""):
        if name:
            return self.get_named_run_range(name)
        try:
            return self.session.query(RunRange).filter(RunRange.min == min_run).filter(RunRange.max == max_run).one()
        except sqlalchemy.orm.exc.NoResultFound:
            raise ObjectIsNotFoundInDbError(RunRange, "Run range '{0}-{1}' is not found".format(min_run, max_run))

    # ------------------------------------------------
    # GetRun Range from db by name
    # ------------------------------------------------
    def get_named_run_range(self, name):
        """
        Get named run range from db

        :param name:
        :return:
        """
        try:
            return self.session.query(RunRange).filter(RunRange.name == name).one()
        except sqlalchemy.orm.exc.NoResultFound:
            raise ObjectIsNotFoundInDbError(RunRange, "Run range with name '{0}' is not found".format(name))

    # ------------------------------------------------
    # Gets run range from DB Or Creates RunRange in DB
    # ------------------------------------------------
    def get_or_create_run_range(self, min_run, max_run, name="", comment="", commit=True):
        """
        Gets run range from DB Or Creates RunRange in DB

        :param min_run: min run
        :param max_run: max run
        :param name: name
        :param comment: comment in case we will have to create a new run range
        :param commit: False only flushes a new run range, so it belongs to the caller's transaction
                       (create_assignment rolls it back when the assignment fails)
        :return: RunRange object
        :rtype: RunRange
        """

        try:
            run_range = self.get_run_range(min_run, max_run, name)
            return run_range
        except (ObjectIsNotFoundInDbError, MultipleResultsFound):
            # several equal run ranges exist on some old databases; as before, a new one is made then.
            # A database error is not caught: inside a write transaction it must reach the restart rule
            pass

        # if we here we was unable to find a run range
        run_range = RunRange()
        run_range.min = min_run
        run_range.max = max_run
        run_range.name = name
        run_range.comment = comment

        self.session.add(run_range)
        if commit:
            self.session.commit()
        else:
            self.session.flush()
        return run_range

    # ------------------------------------------------
    # Updates run range
    # ------------------------------------------------
    def update_run_range(self):
        """
        Updates run range
        """

        self.session.commit()

    # ------------------------------------------------
    # Deletes run range
    # ------------------------------------------------
    def delete_run_range(self, run_range):
        """
        Deletes run range

        :param run_range: RunRange object to delete
        :return: None
        """
        data_count = self.session.query(Assignment).filter(Assignment.run_range_id == run_range.id).count()
        if data_count > 0:
            message = ("Can't delete run range that has data assigned to it."
                       "The run range with id '{0}', name '{1}' [{2} - {3}] has {4} data sets which reference it."
                       "Please, delete the data first"). \
                format(run_range.id,
                       run_range.name,
                       run_range.min,
                       run_range.max,
                       data_count)
            raise ValueError(message)

        self.session.delete(run_range)
        self.session.commit()

    # ----------------------------------------------------------------------------------------
    #   V A R I A T I O N S
    # ----------------------------------------------------------------------------------------
    # ------------------------------------------------
    # Get variation by name
    # ------------------------------------------------
    def get_variation(self, name):
        """
        Get variation by name

        :param name: Variation name
        :return: Variation object
        :rtype: Variation
        """
        try:
            return self.session.query(Variation).filter(Variation.name == name).one()
        except NoResultFound:
            message = "No variation found with name: '{0}'".format(name)
            raise ObjectIsNotFoundInDbError(Variation, message)

    # ----------------------------------------- --------------
    # Searches all variations associated with this type table
    # -------------------------------------------------------
    # noinspection PyUnresolvedReferences
    def get_variations(self, pattern="", include_deprecated=True):
        """
        Returns all variations associated with this type table

        :param include_deprecated: False leaves deprecated variations out
        :type include_deprecated: bool
        :return: list of variations
        :rtype: [Variation]
        """

        # initial query
        query = self.session.query(Variation)

        if len(pattern):
            # prepare search pattern for SQL
            pattern = pattern.replace("_", "\\_").replace("*", "%").replace("?", "_")
            query = query.filter(Variation.name.like(pattern, escape="\\"))

        if not include_deprecated:
            query = query.filter(_not_deprecated(Variation))

        return query.all()

    # ------------------------------------------------
    # Searches all variations associated with this type table
    # ------------------------------------------------
    # noinspection PyUnresolvedReferences
    def search_variations(self, table_or_path, run=0, name=None, limit=0, offset=0):
        """
        Searches all variations associated with this type table

        :param table_or_path: table table to search run ranges in
        :param run: specified run to search for, if run<0 searches for all run ranges
        :param name: Name pattern. Wildcards allowed
        :param limit: how many records to take. 0 - take all records
        :param offset: offset of first record to take.
        :
        :return: list of variations
        :rtype: [Variation]
        """

        if isinstance(table_or_path, str):
            table = self.get_type_table(table_or_path)
        else:
            assert isinstance(table_or_path, TypeTable)
            table = table_or_path
        if not table:
            return []

        query = self.session.query(Variation) \
            .join(Assignment).join(ConstantSet).join(TypeTable).join(RunRange) \
            .filter(TypeTable.id == table.id)
        if run >= 0:
            query = query.filter(RunRange.min <= run).filter(RunRange.max >= run)
        if limit > 0:
            query = query.limit(limit)
        if offset > 0:
            query = query.offset(offset)
        if name and len(name):
            name = name.replace("_", "\\_").replace("*", "%").replace("?", "_")
            query = self.session.query(Variation).filter(Variation.name.like(name, escape="\\"))

        return query.all()

    # ----------------------.--------------------------
    # Create variation by name
    # ------------------------------------------------
    def create_variation(self, name, comment="", parent_name=""):
        """
        Create variation by name

        :param name: Name of the variation
        :param comment: Comment for the variation

        :return: new created variation
        :rtype: Variation
        """
        # Get user
        user = self.get_current_user()

        if user.name == 'anonymous':  # anonymous user can't create variations

            raise AnonymousUserForbiddenError
        else:

            variation = Variation()

            if self.session.query(Variation).filter(Variation.name == name).count() > 0:
                raise ValueError("Cannot create a new variation with name {0}. "
                                 "Variation with that name already exists".format(name))

            if parent_name:
                parent = self.get_variation(parent_name)
                variation.parent = parent

            variation.comment = comment
            variation.name = name
            variation.author_id = user.id
            self.session.add(variation)
            self.session.commit()

            # add log
            self.create_log_record(user=user,
                                   affected_ids=[variation.__tablename__ + str(variation.id)],
                                   action="create",
                                   description="Created variation '{0}' parent is '{1}'".format(variation.name,
                                                                                                variation.parent.name),
                                   comment=variation.comment)

            return variation

    # @brief Update variation
    #
    # Function updates:
    # variation comments
    # variation name if there is no variations with this name
    #
    # @param   [in]  variation to update
    # @return true if success
    def update_variation(self, variation):

        # get user here to fail if no such user
        user = self.get_current_user()

        self.session.commit()
        # Log
        self.create_log_record(user=user,
                               affected_ids=[variation.__tablename__ + str(variation.id)],
                               action="update",
                               description="Updated variation '{0}'".format(variation.name),
                               comment=variation.comment)

    ## @brief Delete variation
    #
    # Variation will be deleted only
    # if there is no assignments for this variation
    # @param    [in] variation to delete
    # @return   bool
    #
    # ------------------------------------------------
    # ------------------------------------------------
    def delete_variation(self, variation):
        assert isinstance(variation, Variation)

        # get user here to fail if no such user
        user = self.get_current_user()

        data_count = self.session.query(Assignment).filter(Assignment.variation_id == variation.id).count()
        if data_count > 0:
            message = ("Can't delete variation that has data assigned to it. "
                       "The variation '{0}' with id '{1}' has {2} data sets which reference it."
                       "Please, delete the data first").format(variation.name, variation.id, data_count)
            raise ValueError(message)

        tag_names = [tag.name for tag in
                     self.session.query(Tag).filter(Tag.variation_id == variation.id).order_by(Tag.name).all()]
        if tag_names:
            message = ("Can't delete variation that has tags referencing it. "
                       "The variation '{0}' with id '{1}' is referenced by tags: {2}. "
                       "Please, delete the tags first").format(variation.name, variation.id, ", ".join(tag_names))
            raise ValueError(message)

        # the properties of the variation are deleted with it, in one transaction
        variation_id, variation_name, variation_comment = variation.id, variation.name, variation.comment
        try:
            properties_count = self._delete_properties_of("variation", [variation_id])
            self.session.delete(variation)
            self.session.commit()
        except Exception:
            self._rollback_quietly()
            raise
        # Log
        self.create_log_record(user=user,
                               affected_ids=[Variation.__tablename__ + str(variation_id)],
                               action="delete",
                               description=self._with_properties_note(
                                   "Deleted variation '{0}'".format(variation_name), properties_count),
                               comment=variation_comment)

    # ----------------------------------------------------------------------------------------
    #   D E P R E C A T I O N
    # ----------------------------------------------------------------------------------------
    def deprecate(self, obj, comment):
        """
        Marks a directory, a type table or a variation as deprecated.

        The object stays fully usable: requests, cat, vers and info work as before;
        listings may leave it out (include_deprecated=False)

        :param obj: object to deprecate
        :type obj: Directory or TypeTable or Variation
        :param comment: why the object is deprecated and what to use instead. Required
        :type comment: str
        """
        description = self._deprecation_subject(obj)
        if isinstance(obj, Directory) and obj.id == 0:
            raise ValueError("The root directory can not be deprecated")
        if comment is None or not str(comment).strip():
            raise ValueError("A comment is required to deprecate {0}".format(description))

        # get user here to fail if no such user
        user = self.get_current_user()
        if user.name == 'anonymous':
            raise AnonymousUserForbiddenError

        try:
            obj.is_deprecated = True
            obj.deprecated_by_user_id = user.id
            obj.deprecated_time = datetime.now()
            obj.deprecation_comment = comment

            # 'update' as the action: the log action column holds 7 characters
            self.create_log_record(user=user,
                                   affected_ids=[obj.__tablename__ + str(obj.id)],
                                   action="update",
                                   description="Deprecated {0}".format(description),
                                   comment=comment,
                                   commit=False)
            self.session.commit()
        except Exception:
            self._rollback_quietly()
            raise

    def undeprecate(self, obj):
        """
        Clears the deprecation of a directory, a type table or a variation

        :param obj: object to undeprecate
        :type obj: Directory or TypeTable or Variation
        """
        description = self._deprecation_subject(obj)

        # get user here to fail if no such user
        user = self.get_current_user()
        if user.name == 'anonymous':
            raise AnonymousUserForbiddenError

        try:
            obj.is_deprecated = False
            obj.deprecated_by_user_id = None
            obj.deprecated_time = None
            obj.deprecation_comment = None

            self.create_log_record(user=user,
                                   affected_ids=[obj.__tablename__ + str(obj.id)],
                                   action="update",
                                   description="Undeprecated {0}".format(description),
                                   comment="",
                                   commit=False)
            self.session.commit()
        except Exception:
            self._rollback_quietly()
            raise

    @staticmethod
    def _deprecation_subject(obj):
        if isinstance(obj, Directory):
            return "directory '{0}'".format(obj.path)
        if isinstance(obj, TypeTable):
            return "table '{0}'".format(obj.path)
        if isinstance(obj, Variation):
            return "variation '{0}'".format(obj.name)
        raise TypeError("Only a directory, a type table or a variation can be deprecated, got {0}".format(
            type(obj).__name__))

    # ----------------------------------------------------------------------------------------
    #   P R O P E R T I E S
    # ----------------------------------------------------------------------------------------
    PROPERTY_OWNER_TYPES = ("instance", "directory", "table", "variation", "column")

    # log records name an object by its table name and id
    _PROPERTY_OWNER_TABLES = {"directory": Directory.__tablename__, "table": TypeTable.__tablename__,
                              "variation": Variation.__tablename__, "column": TypeTableColumn.__tablename__}

    def _property_query(self, owner_type, owner_id, name=None):
        if owner_type not in self.PROPERTY_OWNER_TYPES:
            raise ValueError("Property owner type '{0}' is not one of: {1}"
                             .format(owner_type, ", ".join(self.PROPERTY_OWNER_TYPES)))
        query = self.session.query(Property).filter(Property.owner_type == owner_type,
                                                    Property.owner_id == owner_id)
        if name is not None:
            query = query.filter(Property.name == name)
        return query

    def _delete_properties_of(self, owner_type, owner_ids):
        """
        Deletes the properties of objects that are being deleted, inside the caller's transaction: the caller
        commits, or rolls back, them together with the objects

        :param owner_ids: ids of the owners, all of owner_type
        :return: the number of deleted properties
        """
        if not owner_ids:
            return 0
        return self.session.query(Property) \
            .filter(Property.owner_type == owner_type, Property.owner_id.in_(list(owner_ids))) \
            .delete(synchronize_session="fetch")

    @staticmethod
    def _with_properties_note(description, properties_count):
        """The description of an object's delete log record, naming the properties deleted with it"""
        if properties_count:
            description += " with {0} {1}".format(properties_count,
                                                  "property" if properties_count == 1 else "properties")
        return description[:255]

    @staticmethod
    def _property_log_ids(prop):
        # the owner is in the ids too, so a search by an object's id finds the changes of its properties
        ids = [Property.__tablename__ + str(prop.id)]
        if prop.owner_type in AlchemyProvider._PROPERTY_OWNER_TABLES:
            ids.append(AlchemyProvider._PROPERTY_OWNER_TABLES[prop.owner_type] + str(prop.owner_id))
        return ids

    def get_property(self, owner_type, owner_id, name):
        """
        Gets one property of the instance (owner_type 'instance', owner_id 0) or of an object

        :return: Property or None if there is no property with that name
        :rtype: Property
        """
        return self._property_query(owner_type, owner_id, name).first()

    def get_properties(self, owner_type, owner_id):
        """
        Gets the properties of the instance (owner_type 'instance', owner_id 0) or of an object, sorted by name

        :rtype: list[Property]
        """
        return self._property_query(owner_type, owner_id).order_by(Property.name).all()

    def set_property(self, owner_type, owner_id, name, value):
        """
        Sets a property: creates it, or updates the value when the owner already has a property with that name

        :return: the Property
        :rtype: Property
        """
        # get user here to fail if no such user
        user = self.get_current_user()
        if user.name == 'anonymous':
            raise AnonymousUserForbiddenError

        if owner_type == "directory" and owner_id == 0:
            raise ValueError("The root directory can not have properties")
        if not name or len(name) > 64:
            raise ValueError("Property name should be 1 to 64 characters long, got '{0}'".format(name))
        if value is None:
            raise ValueError("Property value can not be None. Use delete_property to remove it")

        prop = self._property_query(owner_type, owner_id, name).first()
        action = "update" if prop else "create"
        try:
            if not prop:
                prop = Property(owner_type=owner_type, owner_id=owner_id, name=name)
                self.session.add(prop)
            prop.value = value
            prop.author_id = user.id
            # the server default fills 'modified' only on insert
            prop.modified = datetime.now()
            self.session.flush()

            description = "{0} property '{1}' of {2} {3}".format("Created" if action == "create" else "Updated",
                                                                 name, owner_type, owner_id)
            self.create_log_record(user=user,
                                   affected_ids=self._property_log_ids(prop),
                                   action=action,
                                   description=description[:255],
                                   comment=value,
                                   commit=False)
            self.session.commit()
        except Exception:
            self._rollback_quietly()
            raise
        return prop

    def delete_property(self, owner_type, owner_id, name):
        """
        Deletes a property of the instance or of an object

        :raises ObjectIsNotFoundInDbError: if the owner has no property with that name
        """
        # get user here to fail if no such user
        user = self.get_current_user()
        if user.name == 'anonymous':
            raise AnonymousUserForbiddenError

        prop = self._property_query(owner_type, owner_id, name).first()
        if not prop:
            raise ObjectIsNotFoundInDbError(Property, "{0} {1} has no property '{2}'".format(owner_type, owner_id, name))

        affected_ids = self._property_log_ids(prop)
        value = prop.value
        try:
            self.session.delete(prop)
            self.session.flush()

            description = "Deleted property '{0}' of {1} {2}".format(name, owner_type, owner_id)
            self.create_log_record(user=user,
                                   affected_ids=affected_ids,
                                   action="delete",
                                   description=description[:255],
                                   comment=value,
                                   commit=False)
            self.session.commit()
        except Exception:
            self._rollback_quietly()
            raise

    # ----------------------------------------------------------------------------------------
    #   T A G S
    # ----------------------------------------------------------------------------------------
    def get_tag(self, name):
        """
        Get tag by name

        :param name: Tag name
        :return: Tag object
        :rtype: Tag
        """
        try:
            return self.session.query(Tag).filter(Tag.name == name).one()
        except NoResultFound:
            message = "No tag found with name: '{0}'".format(name)
            raise ObjectIsNotFoundInDbError(Tag, message)

    def get_tags(self):
        """
        :return: all tags sorted by name
        :rtype: list[Tag]
        """
        return self.session.query(Tag).order_by(Tag.name).all()

    def create_tag(self, name, variation="default", snapshot_time=None, comment=""):
        """
        Creates a tag: a name for the state of a variation at one moment

        :param name: tag name: ASCII letters, digits and '_', at most 100 characters
        :param variation: variation name or Variation object
        :param snapshot_time: the moment as a UTC instant: a naive datetime in UTC, or an aware datetime.
                              None means now. A future moment is refused: the data of the future is unknown yet,
                              so such a tag would change what it resolves to
        :param comment: comment of the tag
        :return: new created tag
        :rtype: Tag
        """
        user = self.get_current_user()
        if user.name == 'anonymous':
            raise AnonymousUserForbiddenError

        if not path_utils.validate_tag_name(name) or len(name) > 100:
            raise ValueError("Tag name '{0}' is invalid. It should consist of A-Z, a-z, 0-9, _ "
                             "and be at most 100 characters long".format(name))

        if isinstance(variation, Variation):
            variation_obj = variation
        else:
            variation_obj = self.get_variation(variation)

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        if snapshot_time is None:
            snapshot_time = now
        else:
            if snapshot_time.tzinfo is not None:
                snapshot_time = snapshot_time.astimezone(timezone.utc).replace(tzinfo=None)
            if snapshot_time > now:
                raise ValueError("Cannot create tag '{0}' at {1} UTC: the time is in the future"
                                 .format(name, snapshot_time))

        if self.session.query(Tag).filter(Tag.name == name).count() > 0:
            raise ValueError("Cannot create a new tag with name {0}. "
                             "Tag with that name already exists".format(name))

        tag = Tag()
        tag.name = name
        tag.variation_id = variation_obj.id
        tag.snapshot_time = snapshot_time
        tag.comment = comment
        tag.author_id = user.id
        try:
            self.session.add(tag)
            # flush to get tag.id for the log record
            self.session.flush()

            self.create_log_record(user=user,
                                   affected_ids=[tag.__tablename__ + str(tag.id)],
                                   action="create",
                                   description="Created tag '{0}' of variation '{1}' at {2} UTC".format(
                                       tag.name, variation_obj.name, tag.snapshot_time),
                                   comment=comment,
                                   commit=False)
            self.session.commit()
        except Exception:
            self._rollback_quietly()
            raise
        return tag

    def delete_tag(self, tag_or_name):
        """
        Deletes a tag. Assignments are not touched

        :param tag_or_name: Tag object or tag name
        """
        user = self.get_current_user()
        if user.name == 'anonymous':
            raise AnonymousUserForbiddenError

        tag = self.get_tag(tag_or_name) if isinstance(tag_or_name, str) else tag_or_name
        assert isinstance(tag, Tag)
        tag_id, name, comment = tag.id, tag.name, tag.comment

        try:
            self.session.delete(tag)
            self.session.flush()
            self.create_log_record(user=user,
                                   affected_ids=[Tag.__tablename__ + str(tag_id)],
                                   action="delete",
                                   description="Deleted tag '{0}'".format(name),
                                   comment=comment,
                                   commit=False)
            self.session.commit()
        except Exception:
            self._rollback_quietly()
            raise

    def get_tag_variation(self, tag):
        """
        :return: the variation the tag names
        :rtype: Variation
        """
        variation = self.session.get(Variation, tag.variation_id)
        if variation is None:
            raise ObjectIsNotFoundInDbError(Variation, "The variation with id '{0}' of tag '{1}' is not found"
                                            .format(tag.variation_id, tag.name))
        return variation

    def _created_at_or_before(self, utc_instant):
        """
        SQL condition: the assignment was created at or before the UTC instant

        assignments.created holds a naive local time, so the instant is brought to it per provider.
        MySQL and MariaDB: UNIX_TIMESTAMP reads created in the session time zone, the zone that wrote it.
        SQLite has no time zones: created holds the writing client's local time, compared to the instant in the
        reader's local time, as a request time is compared.
        """
        aware = utc_instant.replace(tzinfo=timezone.utc)
        if self.engine is not None and self.engine.dialect.name == "sqlite":
            return Assignment.created <= aware.astimezone().replace(tzinfo=None)
        return func.unix_timestamp(Assignment.created) <= aware.timestamp()

    def get_pinning_tags(self, assignment):
        """
        Tags that may resolve to the assignment: the tag variation is, or inherits from, the assignment variation,
        and the tag time is at or after the assignment creation

        :param assignment: Assignment object
        :return: list of tags
        :rtype: list[Tag]
        """
        assignment_id = assignment.id
        variation_id = assignment.variation_id
        result = []
        for tag in self.get_tags():
            if not self._variation_inherits_from(tag.variation_id, variation_id):
                continue
            pinned = self.session.query(Assignment.id) \
                .filter(Assignment.id == assignment_id) \
                .filter(self._created_at_or_before(tag.snapshot_time)).count()
            if pinned:
                result.append(tag)
        return result

    def _variation_inherits_from(self, variation_id, ancestor_id):
        """True when the variation is the ancestor or one of its descendants"""
        seen = set()
        current_id = variation_id
        while current_id is not None and current_id not in seen:
            if current_id == ancestor_id:
                return True
            seen.add(current_id)
            variation = self.session.get(Variation, current_id)
            if variation is None:
                return False
            current_id = variation.parent_id
        return False

    def get_variation_tree_up(self, variation):
        """
        The variation and its parents up to 'default': the variations a request for this variation resolves in,
        in the order the resolution tries them (see _get_assignment)

        :param variation: Variation object
        :rtype: list[Variation]
        """
        assert isinstance(variation, Variation)
        result = []
        seen = set()
        while variation is not None and variation.id not in seen:
            result.append(variation)
            seen.add(variation.id)
            if variation.name == "default":
                break
            variation = variation.parent
        return result

    # ----------------------------------------------------------------------------------------
    #   A S S I G N M E N T S
    # ----------------------------------------------------------------------------------------
    # ------------------------------------------------
    # Get last Assignment that matches parameters
    # ------------------------------------------------
    def get_assignment(self, path_or_table, run, variation, date_and_time=None, use_variation_tree=True, tag=None):
        """
        Gets the latest assignment that matches the parameters

        @param run: run number
        @param path_or_table: string with name path of table or Table object
        @param variation: name of the variation or variation object
        @param date_and_time: Constants should be of this or later date
        @param use_variation_tree:
        @param tag: Tag object or tag name. The tag gives the variation and the time limit: the latest assignment
                    created at or before the tag time. variation and date_and_time must then be empty

        @return: latest assignment that matches the parameters
        @rtype: Assignment

        @attention (!) the function doesn't accept requests like /some/path:23:mc

        """

        if isinstance(path_or_table, str):
            table = self.get_type_table(path_or_table)
        else:
            assert isinstance(path_or_table, TypeTable)
            table = path_or_table

        if tag is not None:
            if variation or date_and_time:
                raise ValueError("A request with a tag can have neither a variation nor a time")
            if isinstance(tag, str):
                tag = self.get_tag(tag)
            assert isinstance(tag, Tag)
            created_condition = self._created_at_or_before(tag.snapshot_time)
            return self._get_assignment(table, run, self.get_tag_variation(tag), created_condition,
                                        use_variation_tree)

        # filter by date and time
        created_condition = None
        if date_and_time:
            if isinstance(date_and_time, str):
                date_and_time = path_utils.parse_time(date_and_time)

            assert isinstance(date_and_time, datetime)
            created_condition = Assignment.created <= date_and_time

        return self._get_assignment(table, run, variation, created_condition, use_variation_tree)

    def _get_assignment(self, table, run, variation, created_condition, use_variation_tree):
        """ get_assignment with the time filter as an SQL condition (None: no time filter) """
        if isinstance(variation, str):
            variation_name = variation
        else:
            assert isinstance(variation, Variation)
            variation_name = variation.name

        query = self.session.query(Assignment) \
            .join(ConstantSet).join(TypeTable).join(RunRange).join(Variation) \
            .filter(Variation.name == variation_name) \
            .filter(TypeTable.id == table.id) \
            .filter(RunRange.min <= run).filter(RunRange.max >= run)

        if created_condition is not None:
            query = query.filter(created_condition)

        query = query.order_by(desc(Assignment.id))

        try:
            return query.limit(1).one()
        except NoResultFound:

            # Check if should try the same with parent variation
            if not use_variation_tree or variation_name == "default":
                raise

            # get parent variation
            if isinstance(variation, Variation):
                parent_variation = variation.parent
            else:
                parent_variation = self.get_variation(variation_name).parent

            # try do it with parent variation
            return self._get_assignment(table, run, parent_variation, created_condition, use_variation_tree)

    # ------------------------------------------------
    # get list of assignments
    # ------------------------------------------------
    def get_assignment_by_id(self, assignment_id):
        """

        :param assignment_id: database id of the assignment
        :return: Assignment by database Id
        :rtype: Assignment
        """

        try:
            assignment = self.session.query(Assignment).filter(Assignment.id == assignment_id).one()
        except NoResultFound:
            raise ObjectIsNotFoundInDbError(
                Assignment, "Assignment with id='{}' is not found in the DB".format(assignment_id))

        # A directory knows its full path only inside the directory cache (see _load_dirs); the table reached
        # through assignment.constant_set.type_table is loaded plain, with a path-less directory, and
        # assignment.request would then start with the bare table name. Point the table at the cached directory,
        # as the committed value: a read must record no change that the session would count as pending.
        table = assignment.constant_set.type_table
        set_committed_value(table, "parent_dir", self.get_directory_by_id(table.parent_dir_id))
        return assignment

    # ------------------------------------------------
    # get list of assignments
    # ------------------------------------------------
    def get_assignments(self, path_or_table, run=-1, variation="", date_and_time=None, limit=0, offset=0,
                        defer_vault=False, tag=None):
        """
        returns list of assignments

        Variation: if variation is not empty string the assignments for specified variation will be returned
        otherwise all variations will be accepted

        Date: if date is not None, assignments which are earlier than this date will be returned
        otherwise returned assignments will be not filtered by date

        Paging: paging could be done with  @see take ans @see startWith
        take=0, startWith=0 means select all records;

        :param run: specified run. If run <0, filter does not apply
        :param path_or_table: path to table or table
        :param variation: specified variation. If "", filter is not applied
        :param date_and_time:
        :param limit:
        :param offset:
        :param defer_vault: True leaves the data text of the sets out of the query, for listings that show no data
                            (`vers`); assignment.constant_set.vault then loads on first access
        :param tag: Tag object or tag name: the assignments created at or before the tag time in the tag variation
                    and in its parents up to 'default', the variations where a request with the tag resolves
                    (see get_variation_tree_up). variation and date_and_time must then be empty
        :return:
        """
        created_condition = None
        tag_variation_ids = None
        if tag is not None:
            if variation or date_and_time is not None:
                raise ValueError("A request with a tag can have neither a variation nor a time")
            if isinstance(tag, str):
                tag = self.get_tag(tag)
            tag_variation_ids = [v.id for v in self.get_variation_tree_up(self.get_tag_variation(tag))]
            created_condition = self._created_at_or_before(tag.snapshot_time)

        isstring = isinstance(path_or_table, ("".__class__, u"".__class__))

        if isstring:
            table = self.get_type_table(path_or_table)
        else:
            assert isinstance(path_or_table, TypeTable)
            table = path_or_table

        # build query; the joined rows also populate the relationships, so reading
        # assignment.run_range, .variation or .request afterwards runs no further queries
        eager_set = contains_eager(Assignment.constant_set)
        if defer_vault:
            eager_set = eager_set.defer(ConstantSet._vault)    # a vault can be megabytes; a listing shows none
        query = self.session.query(Assignment) \
            .join(ConstantSet).join(TypeTable).join(RunRange).join(Variation) \
            .options(eager_set.contains_eager(ConstantSet.type_table),
                     contains_eager(Assignment.run_range),
                     contains_eager(Assignment.variation)) \
            .filter(TypeTable.id == table.id)

        # filter variation
        if tag_variation_ids is not None:
            query = query.filter(Variation.id.in_(tag_variation_ids))
        elif isinstance(variation, str):
            if variation != "":
                query = query.filter(Variation.name == variation)
        else:
            assert isinstance(variation, Variation)
            query = query.filter(Variation.name == variation.name)

        # filter by run
        if run >= 0:
            query = query.filter(RunRange.min <= run).filter(RunRange.max >= run)
        log.debug(date_and_time)
        if isinstance(date_and_time, str):
            date_and_time = path_utils.parse_time(date_and_time)
        # filter by date and time
        if date_and_time is not None:
            assert isinstance(date_and_time, datetime)
            query = query.filter(Assignment.created <= date_and_time)
        if created_condition is not None:
            query = query.filter(created_condition)

        # sort query
        query = query.order_by(desc(Assignment.id))

        # limits
        if limit != 0:
            query = query.limit(limit)
        if offset != 0:
            query = query.offset(offset)

        return query.all()

    def get_assignment_by_request(self, request,
                                  allow_defaults=False,
                                  default_run=0,
                                  default_variation='',
                                  default_time=None):
        if isinstance(request, str):  # request is a string parse it and make a request
            request = parse_request(request)
        assert isinstance(request, ParseRequestResult)
        if not allow_defaults and (default_variation or default_run or default_time):
            raise ValueError("allow_defaults is not set to true but other fields are")
        if allow_defaults and not (default_time or default_run or default_variation):
            raise ValueError("allow_defaults is true and default_time or default_run or default_variation is missing")

        if request.tag_is_parsed:
            return self._get_assignment_by_tag_request(request, allow_defaults, default_run)
        if default_variation == '' and request.variation == '':
            request.variation = "default"

        if not request.variation_is_parsed:
            if allow_defaults and default_variation:
                request.variation = default_variation
        if not request.run_is_parsed:
            if allow_defaults and default_run:
                request.run = default_run
        if not request.time_is_parsed:
            if allow_defaults and default_time:
                request.time = default_time
            else:
                request.time = None

        type_table = self.get_type_table(request.path)

        try:
            assignment = self.get_assignment(type_table, request.run, request.variation, request.time)
            return assignment
        except (ObjectIsNotFoundInDbError, NoResultFound) as ex:
            # get_assignment raises sqlalchemy NoResultFound; translate it to a
            # human readable ccdb error instead of "No row was found when one was required"
            message = "There is no data for table {}, run {}, variation '{}'".format(
                request.path, request.run, request.variation)
            if request.time_is_parsed:
                message += " on {}".format(request.time_str)
            message += ". Use 'vers {}' to list existing data".format(request.path)
            raise ObjectIsNotFoundInDbError(Assignment, message) from ex

    def _get_assignment_by_tag_request(self, request, allow_defaults, default_run):
        """ get_assignment_by_request for a request with a tag: the tag gives the variation and the time """
        if request.variation_is_parsed or request.time_is_parsed:
            raise ValueError("A request with a tag can have neither a variation nor a time: '{0}'"
                             .format(request.original_str or request.path))
        if not request.run_is_parsed and allow_defaults and default_run:
            request.run = default_run

        tag = self.get_tag(request.tag)
        type_table = self.get_type_table(request.path)
        try:
            return self.get_assignment(type_table, request.run, "", tag=tag)
        except (ObjectIsNotFoundInDbError, NoResultFound) as ex:
            message = "There is no data for table {}, run {}, tag '{}'. Use 'vers {}' to list existing data" \
                .format(request.path, request.run, request.tag, request.path)
            raise ObjectIsNotFoundInDbError(Assignment, message) from ex

    # ------------------------------------------------
    # Counts the assignments that share each constant set
    # ------------------------------------------------
    def get_constant_set_sharer_counts(self, path_or_table):
        """
        Number of assignments that use each constant set of a table, as {constant set id: count}

        Assignments of one table share a set when their data bytes are equal. One GROUP BY query counts them;
        it reads no data text and loads no assignment. Sets without assignments are not in the result.

        :param path_or_table: path of the table or TypeTable object
        :rtype: dict
        """
        if isinstance(path_or_table, str):
            table = self.get_type_table(path_or_table)
        else:
            assert isinstance(path_or_table, TypeTable)
            table = path_or_table

        # Counted over the sets of the table rather than over a list of set ids: a table can have tens of
        # thousands of assignments, more than SQLite accepts as parameters of one statement
        query = select(Assignment.constant_set_id, func.count(Assignment.id)) \
            .join(ConstantSet, ConstantSet.id == Assignment.constant_set_id) \
            .where(ConstantSet.type_table_id == table.id) \
            .group_by(Assignment.constant_set_id)
        return {set_id: count for set_id, count in self.session.execute(query)}

    # ------------------------------------------------
    # Creates Assignment using related object
    # ------------------------------------------------
    def create_assignment(self, data, path, min_run, max_run, variation_name, comment):
        """
            Creates an assignment of the data to a table, run range and variation

            Data equal byte for byte to a stored constant set of the same table reuses that set, so the
            assignments share it; other data gets a new set. All is written in one transaction: after any
            error nothing is written and the provider stays usable.

            Validation:
            If no such run range found, the new will be created (with no name)
            No assignment will be created:
            -- If no type table with such path exists
            -- If data is inconsistent with columns number and rows number (every row is checked)
            -- If a value does not fit the type of its column
            -- If no variation with such name found

            @param data: tabled data or TextFileDom
            @param path: table path
            @param min_run:
            @param max_run:
            @param variation_name:
            @param comment:
            @return: created assignment
            @rtype: Assignment
            @raise SessionHasPendingChangesError: the session holds uncommitted changes; commit or discard them first
            @raise DataCollisionError: stored sets of the table have the sha256 of the data but other bytes
            @raise ObjectIsNotFoundInDbError: no such table or variation, or the table was removed during the call
            """

        # Pending changes are refused before any read: a query would autoflush them, and the commit below would keep them
        self._refuse_pending_changes()

        # maybe it is a dom?
        if isinstance(data, TextFileDOM):
            rows = data.rows
        else:
            # it should be list than...
            assert isinstance(data, list)
            rows = data

        # get objects
        table = self.get_type_table(path)  # TODO create path_or_table variable

        variation = self.get_variation(
            variation_name)  # TODO create variation_name_or_obj instead of variation_name

        # validate data.. a little =)
        if len(rows) == 0:
            raise ValueError(
                "Try to create variation with data length = 0. Fill data prior inserting into database")
        if not isinstance(rows[0], list):
            # the data is plain list, like [1,2,3,4,5,6]
            # rows_count = len(data) / table._columns_count
            raise NotImplementedError()  # TODO check and implement this branch

        # validate that the data rows and cols correspond to table rows and cols. Every row is checked:
        # a short row further down would be stored and could not be read back
        data_rows_count = len(rows)
        bad_rows = [row_index for row_index, row in enumerate(rows) if len(row) != table.columns_count]
        if data_rows_count != table.rows_count or bad_rows:
            data_cols_count = len(rows[bad_rows[0]]) if bad_rows else len(rows[0])
            message = "Data rows or columns count is inconsistent with table declared rows or columns count. " \
                      "Data rows='{0}', columns='{1}'. Table declared rows='{2}', columns='{3}'" \
                      "".format(data_rows_count, data_cols_count, table.rows_count, table.columns_count)
            if bad_rows:
                message += ". Row {0} has {1} columns".format(bad_rows[0], data_cols_count)
            raise ValueError(message)

        # check for type
        for row_index, row in enumerate(rows):
            for column_index, cell in enumerate(row):
                column = table.columns[column_index]
                self.validate_data_value(cell, column, column_index, row_index)

        # Get user
        user = self.get_current_user()

        if user.name == 'anonymous':
            # anonymous user can't create assignments
            raise AnonymousUserForbiddenError

        # The data text as it will be stored, and its identity
        vault = list_to_blob(list(gen_flatten_data(rows)))
        sha256, _ = vault_digest(vault)

        # The transaction starts by ending the read transaction, which expires every loaded object; these are taken now
        table_id, table_path, variation_id, user_id = table.id, table.path, variation.id, user.id

        def attempt():
            # One write transaction, restarted on a deadlock. The table's row is locked FOR SHARE first, so the table
            # stays while this call runs: rm -t locks the same row FOR UPDATE
            self._begin_write_transaction()
            self._lock_type_table(table_id, table_path, for_update=False)

            # The run range is made inside this transaction, so a failure below takes a new run range back too
            run_range = self.get_or_create_run_range(min_run, max_run, commit=False)

            # A stored set of the table with equal bytes, or a new set
            constant_set, is_reused = self._find_or_store_constant_set(table_id, table_path, vault, sha256)

            assignment = Assignment()
            assignment.constant_set = constant_set
            assignment.run_range = run_range
            assignment.variation_id = variation_id
            assignment.comment = comment
            assignment.author_id = user_id
            self.session.add(assignment)
            self.session.flush()

            # The log record names the set and marks reuse. It is flushed here, so its failure comes before the commit
            suffix = " (shared data)" if is_reused else ""
            self.create_log_record(user=user,
                                   affected_ids=[Assignment.__tablename__ + str(assignment.id),
                                                 ConstantSet.__tablename__ + str(constant_set.id)],
                                   action="create",
                                   description=self._log_description("Created assignment '{0}'", assignment.request, suffix),
                                   comment=assignment.comment,
                                   commit=False)

            # One commit for the run range, the set, the assignment and the log record
            self.session.commit()
            return assignment

        return self._run_write_transaction(attempt)

    def _find_or_store_constant_set(self, table_id, table_path, vault, sha256):
        """
        The stored set of the table with exactly these data bytes, to be reused by create_assignment; or, when
        there is none, a new set.

        Runs inside create_assignment's transaction, which holds the share lock of the table's row.

        :return: (constant set, True when a stored set is reused)
        :raises DataCollisionError: sets of the table have this sha256 but other bytes
        """
        # Candidates by hash, oldest first. Unused sets count too: the unique index covers every row, so a new set
        # with their bytes would be refused; and the oldest set is the one `ccdb db dedup` keeps
        candidates = self._constant_set_candidates(table_id, sha256, lock=False)
        if candidates:
            # Bytes are compared in Python: the column collation in SQL ignores case and trailing spaces
            equal_sets = [candidate for candidate in candidates if candidate.vault == vault]
            if not equal_sets:
                raise self._data_collision(table_path, sha256, candidates)

            # The oldest equal set, re-read as a locking read. rm -a, rm -t and db dedup delete sets, and a plain read
            # could pick one that is deleted before this transaction commits; the share lock keeps the set until then
            match = equal_sets[0]
            locked = self.session.execute(
                select(ConstantSet.id).where(ConstantSet.id == match.id).with_for_update(read=True)).first()
            if locked is not None:
                return match, True
            # The set was deleted since the plain read: the data is stored anew. Before `ccdb db dedup` a table can
            # hold more equal sets; they are not tried, and the next dedup merges the new set with them

        # A new set, in a SAVEPOINT. A writer that stored the same bytes after this transaction's snapshot was taken
        # wins the unique index; then only this insert is undone
        constant_set = ConstantSet(vault=vault)
        constant_set.type_table_id = table_id
        try:
            with self.session.begin_nested():
                self.session.add(constant_set)
                self.session.flush()
        except IntegrityError:
            # Under REPEATABLE READ a plain SELECT keeps returning this transaction's first snapshot, without the
            # winner's row; a locking read returns committed rows. The error text differs by server and version,
            # so the re-query tells the race from other errors
            candidates = self._constant_set_candidates(table_id, sha256, lock=True)
            if not candidates:
                raise       # not the race on the unique index
            for candidate in candidates:
                if candidate.vault == vault:
                    return candidate, True
            raise self._data_collision(table_path, sha256, candidates)
        return constant_set, False

    def _constant_set_candidates(self, table_id, sha256, lock):
        """Sets of the table with this sha256, by id; with lock, read as a locking read (FOR SHARE)"""
        query = self.session.query(ConstantSet) \
            .filter(ConstantSet.type_table_id == table_id, ConstantSet.sha256 == sha256) \
            .order_by(ConstantSet.id)
        if lock:
            query = query.with_for_update(read=True)
        return query.all()

    @staticmethod
    def _data_collision(table_path, sha256, candidates):
        """The DataCollisionError of create_assignment, also logged as an error line: it means corrupt data or a broken hash"""
        error = DataCollisionError(table_path, sha256, [candidate.id for candidate in candidates])
        log.error(str(error))
        return error

    def _lock_type_table(self, table_id, table_path, for_update):
        """
        Locks the table's typeTables row until the transaction ends: FOR SHARE for writers that add data to the
        table, FOR UPDATE for rm -t, which deletes it. On SQLite the clause is left out; BEGIN IMMEDIATE serializes writers.

        :raises ObjectIsNotFoundInDbError: the table is gone
        """
        statement = select(TypeTable.id).where(TypeTable.id == table_id).with_for_update(read=not for_update)
        if self.session.execute(statement).first() is None:
            raise ObjectIsNotFoundInDbError(TypeTable, "The type table '{0}' was removed from the DB".format(table_path))

    def copy_assignment(self, source_assignment, new_run_range=None, new_variation=None, comment=''):
        """
        Creates an assignment with the data of the source assignment, for another run range or variation.
        The copy shares the source's constant set: no data is copied.

        Validation:
        If no such run range found, the new will be created (with no name)
        No assignment will be created (and NULL will be returned):
        -- If no type table with such path exists
        -- If data is inconsistent with columns number and rows number
        -- If no variation with such name found
        -- If no assignment is given

        One transaction: the source's set is locked (FOR SHARE), then the source assignment, so neither rm -a nor
        db dedup deletes the set before the copy is committed. When db dedup moved the source to another set
        meanwhile, the transaction restarts on that set.

        @param new_run_range: run_range of assignment
        @param new_variation: variation of assignment
        @param comment: comment of assignment
        @param source_assignment: where the new assignment is being copied
        @return: created assignment
        @rtype: Assignment
        @raise ObjectIsNotFoundInDbError: no such variation, or the source assignment was deleted
        """

        user = self.get_current_user()

        # you get some variation
        if new_variation is None:
            new_variation = source_assignment.variation
        elif isinstance(new_variation, str):
            new_variation = self.get_variation(new_variation)
        assert isinstance(new_variation, Variation)
        if new_run_range is None:
            new_run_range = source_assignment.run_range
        source_id, user_id = source_assignment.id, user.id

        def attempt():
            self._begin_write_transaction()

            # The set is locked before the assignment: every writer locks constantSets rows before assignments rows.
            # No row is no error here; the re-check below tells what happened
            set_id = self.session.execute(
                select(Assignment.constant_set_id).where(Assignment.id == source_id)).scalar()
            if set_id is None:
                raise self._assignment_is_gone(source_id)
            self.session.execute(select(ConstantSet.id).where(ConstantSet.id == set_id).with_for_update(read=True)).all()

            # The re-check selects the column, never an Assignment entity: a locking query of an entity returns the
            # object already in the session, with its old constant_set_id
            locked_set_id = self.session.execute(
                select(Assignment.constant_set_id).where(Assignment.id == source_id).with_for_update(read=True)).scalar()
            if locked_set_id is None:
                raise self._assignment_is_gone(source_id)        # rm -a deleted it
            if locked_set_id != set_id:
                raise _ConstantSetIdChanged()                     # db dedup moved it to the oldest equal set

            # construct assignment
            dest_assignment = Assignment()
            dest_assignment.constant_set_id = locked_set_id
            dest_assignment.run_range = new_run_range
            dest_assignment.variation = new_variation
            dest_assignment.comment = comment
            dest_assignment.author_id = user_id
            self.session.add(dest_assignment)
            self.session.flush()

            # a copy is a new assignment that reuses a set: its record names the set and marks the sharing
            self.create_log_record(user=user,
                                   affected_ids=[Assignment.__tablename__ + str(dest_assignment.id),
                                                 ConstantSet.__tablename__ + str(locked_set_id)],
                                   action="create",
                                   description=self._log_description("Created assignment '{0}'",
                                                                     dest_assignment.request, " (shared data)"),
                                   comment=comment,
                                   commit=False)
            self.session.commit()
            return dest_assignment

        return self._run_write_transaction(attempt)

    # ------------------------------------------------
    # updates assignment comments
    # ------------------------------------------------
    def update_assignment(self, assignment):
        """
        Saves the changes of an assignment's comment, run range or variation

        :raises ValueError: the assignment was given another constant set. Data changes by a new assignment; and a set
                            attached here would not be locked, so a concurrent rm -a could delete it under the assignment
        """
        # Checked before any read: get_current_user() queries, and its autoflush would write the change
        if self._is_constant_set_changed(assignment):
            raise ValueError("An assignment cannot move to another constant set; nothing was written. "
                             "Data changes by a new assignment ('ccdb add' or create_assignment)")

        # get user here to fail if no such user
        user = self.get_current_user()

        self.session.commit()

        # Log
        self.create_log_record(user=user,
                               affected_ids=[assignment.__tablename__ + str(assignment.id)],
                               action="update",
                               description="Updated assignment '{0}'".format(assignment.request),
                               comment=assignment.comment)

    @staticmethod
    def _is_constant_set_changed(assignment):
        """
        True when the assignment points at another constant set than its stored one, through the constant_set
        relationship or the constant_set_id column. Reads only the session's change history, never the database.
        """
        attributes = sqlalchemy.inspect(assignment).attrs
        column_history = attributes.constant_set_id.history
        if column_history.added or column_history.deleted:
            return True
        relation_history = attributes.constant_set.history
        if not relation_history.has_changes():
            return False
        # The relationship moves the column only at the flush: the new set is compared with the stored column value
        new_set = relation_history.added[0] if relation_history.added else None
        new_identity = sqlalchemy.inspect(new_set).identity if new_set is not None else None
        stored_ids = list(column_history.unchanged)
        return not (new_identity and stored_ids and new_identity[0] == stored_ids[0])

    # ------------------------------------------------
    # Deletes assignment
    # ------------------------------------------------
    def delete_assignment(self, assignment, force=False):
        """
        Deletes assignment, and its constant set when no other assignment uses the set

        One transaction: the set is locked (FOR UPDATE), then the assignment. A writer that attaches an assignment
        to the set holds a share lock on it until it commits; this call then waits, sees that assignment and keeps
        the set. When this call locks the set first, that writer finds the set gone and stores its data anew.

        :param assignment: assignment object to delete. Must have valid ID
        :param force: True deletes the assignment even when a tag may resolve to it
        :raises SessionHasPendingChangesError: the session holds uncommitted changes; commit or discard them first
        :raises ObjectIsNotFoundInDbError: the assignment was deleted already
        :raises ValueError: a tag may resolve to the assignment and force is False
        """
        # Pending changes are refused before any read: a query would autoflush them, and the commit below would keep them
        self._refuse_pending_changes()

        # A tag promises the same data later; deleting an assignment it may resolve to breaks that promise
        if not force:
            try:
                pinning_tags = self.get_pinning_tags(assignment)
            except ObjectDeletedError as ex:
                raise ObjectIsNotFoundInDbError(Assignment, "The assignment is not found in the DB") from ex
            if pinning_tags:
                raise ValueError("Assignment {0} may be the data of tag(s) {1}. Use force to delete it anyway"
                                 .format(assignment.id, ", ".join("'" + t.name + "'" for t in pinning_tags)))

        # save assignment parameters now: once the set is gone, assignment.request cannot reach the table
        user = self.get_current_user()
        try:
            assignment_id = assignment.id
            description = self._log_description("Deleted assignment '{0}'", assignment.request)
            comment = assignment.comment
        except ObjectDeletedError as ex:
            raise ObjectIsNotFoundInDbError(Assignment, "The assignment is not found in the DB") from ex

        def attempt():
            self._begin_write_transaction()

            # The id reads select the column, never an Assignment entity: a locking query of an entity returns the
            # object already in the session, with its old constant_set_id
            set_id = self.session.execute(
                select(Assignment.constant_set_id).where(Assignment.id == assignment_id)).scalar()
            if set_id is None:
                raise self._assignment_is_gone(assignment_id)

            # Lock the set before the assignment, the order every writer keeps. No row is no error: the locking
            # re-read of the assignment below tells what happened
            self.session.execute(select(ConstantSet.id).where(ConstantSet.id == set_id).with_for_update()).all()

            # Lock the assignment and re-check its set id: gone means another rm -a won, another id means db dedup moved it
            locked_set_id = self.session.execute(
                select(Assignment.constant_set_id).where(Assignment.id == assignment_id).with_for_update()).scalar()
            if locked_set_id is None:
                raise self._assignment_is_gone(assignment_id)    # another rm -a got there first
            if locked_set_id != set_id:
                raise _ConstantSetIdChanged()                     # db dedup moved it to the oldest equal set

            # The delete goes through the ORM, so the caller's object ends detached with its loaded columns, as it always did.
            # Assignment.constant_set has no cascade: this touches no set
            self.session.delete(assignment)
            self.session.flush()

            # Is the set used by another assignment? A locking read: under REPEATABLE READ a plain one would return
            # this transaction's first snapshot and miss an assignment another writer attached while the set lock waited
            other_sharer = self.session.execute(
                select(Assignment.id).where(Assignment.constant_set_id == set_id).limit(1).with_for_update(read=True)).first()
            if other_sharer is None:
                sets_table = ConstantSet.__table__
                self.session.execute(sets_table.delete().where(sets_table.c.id == set_id))
                self._forget_constant_set(set_id)

            # The record names the assignment only, whether or not its set went with it
            self.create_log_record(user=user,
                                   affected_ids=[Assignment.__tablename__ + str(assignment_id)],
                                   action="delete",
                                   description=description,
                                   comment=comment,
                                   commit=False)
            self.session.commit()

        self._run_write_transaction(attempt)

    def _forget_constant_set(self, set_id):
        """
        Takes a set that an SQL statement deleted out of the session, so the session does not try to reload it.
        The commit that opened the write transaction expired the set's columns, and nothing reloads them: a caller
        that still holds the set gets DetachedInstanceError when it reads it (left in the session, it would get
        ObjectDeletedError).
        """
        deleted_set = self.session.identity_map.get(identity_key(ConstantSet, set_id))
        if deleted_set is not None:
            self.session.expunge(deleted_set)

    @staticmethod
    def _assignment_is_gone(assignment_id):
        return ObjectIsNotFoundInDbError(Assignment, "Assignment with id='{0}' is not found in the DB; "
                                                     "it was deleted".format(assignment_id))

    @staticmethod
    def _log_description(template, request, suffix=""):
        """
        template.format(request) + suffix, within the 255 characters of logs.description.
        The request part is shortened when needed; the suffix stays whole.
        """
        description = template.format(request) + suffix
        overflow = len(description) - LOG_DESCRIPTION_LENGTH
        if overflow > 0:
            description = template.format(request[:len(request) - overflow - 3] + "...") + suffix
        return description

    # ----------------------------------------------------------------------------------------
    #   W R I T E   T R A N S A C T I O N S
    # ----------------------------------------------------------------------------------------
    def _refuse_pending_changes(self):
        """
        Raises SessionHasPendingChangesError when the session holds changes that are not written yet.

        create_assignment and delete_assignment commit their own transaction, which would commit the caller's
        changes with it, and their first query would autoflush them; so this runs before any read. Only net changes
        count: new and deleted objects, and loaded objects whose columns or relationships differ from the stored ones.
        """
        session = self.session
        if session.new or session.deleted or any(session.is_modified(obj) for obj in session.dirty):
            raise SessionHasPendingChangesError()

    def _begin_write_transaction(self):
        """
        Starts the transaction of a write method.

        The reads before it left a transaction open, and on MySQL its REPEATABLE READ snapshot would hide what other
        writers committed since; so it is ended first. Methods that refuse pending changes have nothing to commit
        here; copy_assignment and delete_type_table commit what the caller left pending, as they always did.

        SQLite: pysqlite sends no BEGIN before a SELECT, so a SAVEPOINT would open the transaction and its RELEASE
        commit it. BEGIN IMMEDIATE makes the call one transaction, and a second writer waits here for the first.
        """
        self.session.commit()
        if self.engine.dialect.name == "sqlite":
            self.session.connection().exec_driver_sql("BEGIN IMMEDIATE")

    def _run_write_transaction(self, attempt):
        """
        Runs attempt(), a function that does one write transaction and commits it, with the restart rule.

        On a MySQL deadlock (1213), a lock wait timeout (1205) or a constant set id that changed under a re-check,
        the transaction is rolled back and attempt() runs again, at most MAX_TRANSACTION_RESTARTS times. On any other
        error it is rolled back and the error is raised: nothing is written and the session stays usable.
        attempt() builds its objects anew on every run, since the rollback expunged those of the failed run.
        """
        restarts = 0
        while True:
            try:
                return attempt()
            except BaseException as error:
                self._rollback_quietly()
                cause = self._restartable_cause(error)
                if restarts < MAX_TRANSACTION_RESTARTS and cause is not None:
                    restarts += 1
                    # the reason only: the error text would carry the statement and its data parameters
                    reason = "constant set changed" if isinstance(cause, _ConstantSetIdChanged) \
                        else "MySQL error {0}".format(cause.orig.args[0])
                    log.info("Write transaction rolled back and restarted ({0} of {1}): {2}".format(
                        restarts, MAX_TRANSACTION_RESTARTS, reason))
                    continue
                if isinstance(error, _ConstantSetIdChanged):
                    raise RuntimeError("The constant set of the assignment changed under this call {0} times "
                                       "(is 'ccdb db dedup' running?). Nothing was written; try again"
                                       .format(restarts + 1)) from error
                raise

    @staticmethod
    def _restartable_cause(error):
        """
        The error, or the error it was raised from or while handling, after which a write transaction runs again
        (see RESTARTABLE_MYSQL_ERRORS); None when there is none.

        The chain is followed because a deadlock inside a SAVEPOINT does not surface itself: MySQL rolls back the
        whole transaction, savepoint included, so SQLAlchemy's ROLLBACK TO SAVEPOINT fails with error 1305, and that
        error replaces the deadlock, which stays only as its __context__.
        """
        seen = set()
        while error is not None and id(error) not in seen:
            seen.add(id(error))
            if isinstance(error, _ConstantSetIdChanged):
                return error
            if isinstance(error, DBAPIError) and error.orig is not None and error.orig.args \
                    and error.orig.args[0] in RESTARTABLE_MYSQL_ERRORS:
                return error
            error = error.__cause__ or error.__context__
        return None

    def _rollback_quietly(self):
        """Rolls back after a failed write. A failing rollback is only logged: the write's error is what the caller needs"""
        try:
            self.session.rollback()
        except Exception as rollback_error:
            log.warning("Rollback after a failed write raised: %r", rollback_error)

    # ------------------------------------------------
    # validate value
    # ------------------------------------------------
    def validate_data_value(self, value, column, column_index=0, row_index=0):
        col_type = column.type
        failure = False

        if col_type == 'int':
            try:
                value = int(value)
            except ValueError:
                failure = True

        elif col_type == 'uint':
            try:
                value = int(value)
                if value < 0:
                    raise ValueError()
            except ValueError:
                failure = True

        elif col_type == 'long':
            try:
                value = int(value)
            except ValueError:
                failure = True

        elif col_type == 'ulong':
            try:
                value = int(value)
                if value < 0:
                    raise ValueError()
            except ValueError:
                failure = True

        elif col_type == 'double':
            try:
                value = float(value)
            except ValueError:
                failure = True

        elif col_type == 'bool':
            try:
                if value.lower() in ("yes", "true", "t", "1"):
                    return True
                elif value.lower() in ("no", "false", "f", "0"):
                    return False
                else:
                    value = bool(int(value))
            except ValueError:
                failure = True

        else:
            # 'string'
            pass

        if failure:
            message = self.error_parse_value_message.format(column.name, column_index,
                                                            row_index, column.type, value)
            raise ValueError(message)

        return value

    # ------------------------------------------------
    # fill_assignment
    # ------------------------------------------------
    def fill_assignment(self, assignment):
        """
         @brief Fill assignment with data if it has proper ID

         The function actually gets assignment by ID
        :param assignment:
        :return:
        """
        # TODO decide is it useless or not
        raise NotImplementedError()

    # ----------------------------------------------------------------------------------------
    #   U S E R S
    # ----------------------------------------------------------------------------------------
    # ------------------------------------------------
    # get user by username
    # ------------------------------------------------
    def get_user(self, username):
        """
        Find user in the database by user name

        :param username: username to find
        :type username: str

        :return: User db object
        :rtype: User
        """
        query = self.session.query(User).filter(User.name == username)
        try:
            return query.one()
        except NoResultFound:
            message = "No user with name '{0}' is found in database. " \
                      "Set the user name by CCDB_USER environment variable. " \
                      "See 'ccdb user' command to create a user.".format(username)
            raise UserNotFoundError(message, username)

    # ------------------------------------------------
    # get all users in DB
    # ------------------------------------------------
    def get_users(self, filter_deleted=True):
        """
        @param filter_deleted: Return only non-deleted users
        @type filter_deleted: bool
        @return:
        """
        query = self.session.query(User)
        if filter_deleted:
            query = query.filter(User.is_deleted == 0)
        return query.all()

    # ------------------------------------------------
    # get all users in DB
    # ------------------------------------------------
    def create_user(self, name, pwd="", roles=[], user_info=""):
        """
            Creates a user with defined user name
        """
        try:
            user = self.get_user(name)
            if user.is_deleted:
                user.is_deleted = False
            else:
                raise UserExistsError("The user with name '" + name + "' exists in the database", name)
        except UserNotFoundError:
            user = User()
            user.last_action_time = datetime.now()
            user.name = name
            self.session.add(user)

        user.password = pwd
        user.roles = roles
        user.info = user_info
        self.session.commit()
        return user

    # ------------------------------------------------
    # deletes user by name
    # ------------------------------------------------
    def delete_user(self, name):
        """
        Deletes user with specified name
        @param name: Name(login) of the user to delete
        @type name: str
        @raise UserNo

        The function doesn't physically delete user record from DB, but flag user as deleted
        """

        user = self.get_user(name)
        user.is_deleted = True
        self.session.commit()

    # ------------------------------------------------
    # deletes user by name
    # ------------------------------------------------
    def get_current_user(self):
        """
        Gets current user. The current user is the user, whose name appears in log

        @return: User db object
        @rtype: User
        """
        return self.get_user(self._auth.current_user_name)

    @property
    def authentication(self):
        """
        returns Authentication object
        :return: current Authentication object
        :rtype: authentication.Authentication
        """
        return self._auth

    @authentication.setter
    def authentication(self, auth):
        self._auth = auth

    # ----------------------------------------------------------------------------------------
    #   E R R O R   H A N D L I N G
    # ----------------------------------------------------------------------------------------

    # ----------------------------------------------------------------------------------------
    #   O T H E R   F U N C T I O N S
    # ----------------------------------------------------------------------------------------
    @staticmethod
    def validate_name(name):
        """Validates name for constant type table or directory or column"""
        return path_utils.validate_name(name)

    # ----------------------------------------------------------------------------------------
    #   L O G G I N G
    # ----------------------------------------------------------------------------------------
    def create_log_record(self, user, affected_ids, action, description, comment, commit=True):
        """
        Writes a log record when logging is enabled

        :param commit: False only flushes the record, inside the caller's transaction: the record and the change
                       it describes are then committed together, and a failing record surfaces before that commit
        :return: the LogRecord, or None when logging is disabled
        """
        if not self.logging_enabled:
            return None

        assert isinstance(user, User)
        assert isinstance(affected_ids, list)

        record = LogRecord()
        record.author_id = user.id
        record.author = user
        record.affected_ids = "|" + "|".join(affected_ids) + "|"
        record.action = action
        record.description = description
        record.comment = comment
        user.last_action_time = datetime.now()

        self.session.add(record)
        if commit:
            self.session.commit()
        else:
            self.session.flush()
        return record

    def get_log_records(self, limit=20, offset=0):

        """
        Get log records sorted from now to the past

        :param limit:
        :type limit: int

        :param offset:
        :type offset: int

        :return:List of log records
        :rtype: []
        """

        if limit < 0:
            limit = 0

        # initial query
        query = self.session.query(LogRecord).order_by(desc(LogRecord.id))

        # add limits to query
        if limit != 0:
            query = query.limit(limit)
        if offset != 0:
            query = query.offset(offset)

        # execute and return
        return query.all()


def _not_deprecated(model_class):
    """SQL condition for rows that are not deprecated; NULL counts as not deprecated, as before the column"""
    return or_(model_class.is_deprecated == False, model_class.is_deprecated.is_(None))  # noqa: E712
