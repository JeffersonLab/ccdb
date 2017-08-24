"""@package AlchemyProvider
Documentation for this module.

More details.
"""

import re
import os
import logging
from .model import CcdbSchemaVersion
from . import path_utils
from datetime import datetime

import sqlalchemy
from sqlalchemy.exc import OperationalError
import sqlalchemy.orm
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql.expression import desc
from .model import Directory, TypeTable, TypeTableColumn, ConstantSet, Assignment, RunRange, Variation, User, LogRecord
from .errors import DirectoryNotFound, TypeTableNotFound, RunRangeNotFound, AnonymousUserForbiddenError, DatabaseStructureError, \
    UserNotFoundError, UserExistsError, \
    VariationNotFound

from .table_file import TextFileDOM
from .authentication import Authentication

import posixpath

log = logging.getLogger("ccdb.provider")


class AlchemyProvider(object):
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
        self.path_name_regex = re.compile('^[\w\-_]+$', re.IGNORECASE)
        self._connection_string = ""
        self._auth = Authentication(self)
        self._auth.current_user_name = "anonymous"
        self.logging_enabled = True
        self._no_structure_message = "No database structure found. Possibly you are trying to connect " + \
                                     "to wrong SQLite file or to MySQL database without schema. " + \
                                     "Original SqlAlchemy error is: " + os.linesep + os.linesep + "{0}"


    # ----------------------------------------------------------------------------------------
    #   C O N N E C T I O N
    # ----------------------------------------------------------------------------------------

    # ------------------------------------------------
    #  Connects to database using connection string
    # ------------------------------------------------
    def connect(self, connection_string=""):
        """
        Connects to database using connection string

        connection string might be in form:
        mysql://<username>:<password>@<mysql.address>:<port> <database>
        sqlite:///path/to/file.sqlite

        :param connection_string: connection string
        :type connection_string: str
        """
        try:
            self.engine = sqlalchemy.create_engine(connection_string)
        except ImportError as err:
            #sql alchemy uses MySQLdb by default. But it might not be installed in the system
            #in such case we fallback to mysqlconnector which is included in CCDB
            if connection_string.startswith("mysql://") and "No module named MySQLdb" in repr(err):
                connection_string = connection_string.replace("mysql://", "mysql+mysqlconnector://")
                self.engine = sqlalchemy.create_engine(connection_string)
            else:
                raise

        #
        session_type = sqlalchemy.orm.sessionmaker(bind=self.engine)
        self.session = session_type()
        self._is_connected = True
        self._connection_string = connection_string

        #since it is a new connection we need to rebuild directories
        self._are_dirs_loaded = False

        #check data schema version
        try:
            vers_rec = self.session.query(CcdbSchemaVersion).first()
            if vers_rec.version < 4:
                message = "Version mismatch. The database schema version is '{0}'. " \
                          "This CCDB version works with schema version 4 (or maybe 4+)".format(vers_rec.version)
                raise DatabaseStructureError(message)
        except OperationalError as err:
            if "no such table" in err.message:
                raise DatabaseStructureError(self._no_structure_message.format(err))
            else:
                raise


    # ------------------------------------------------
    # Closes connection to data
    # ------------------------------------------------
    def disconnect(self):
        """Closes connection to database"""
        #TODO close pool logic???
        self._is_connected = False
        self.session.close()


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

        #we don't have this directory
        if not path in self.dirs_by_path.keys():
            raise DirectoryNotFound("Can't find the directory with path '{0}'".format(path))

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
    # Searches directories that matches the pattern
    # ------------------------------------------------
    def search_directories(self, searchPattern, parentPath="", limit=0, offset=0):
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

        :return: Directories to find
        :rtype: [] of Directory
        """

        self._ensure_dirs_loaded()

        searchPattern = searchPattern.replace("_", "\\_").replace("*", "%").replace("?", "_")

        query = self.session.query(Directory).filter(Directory.name.like(searchPattern, escape="\\"))

        if parentPath != "":
            parent_dir = self.dirs_by_path[parentPath]
            query = query.filter(Directory.parent_id == parent_dir.id)

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

        #get parent directory
        if isinstance(parent_dir_or_path, str):
            parent_dir = self.dirs_by_path[parent_dir_or_path]
        else:
            assert (isinstance(parent_dir_or_path, Directory))
            parent_dir = parent_dir_or_path

        #check if no such directory exists
        new_full_path = posixpath.join(parent_dir.path, new_dir_name)
        if new_full_path in self.dirs_by_path.keys():
            raise ValueError("The directory with path '{0}' already exist".format(new_full_path))

        #Get user
        user = self.get_current_user()

        if user.name == 'anonymous': # anonymous user can't create directories

            raise AnonymousUserForbiddenError
        else:

            #create the directory
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

            #add to database
            self.session.add(directory)
            self.session.commit()

            #add log
            self.create_log_record(user=user,
                                   affected_ids=[directory.__tablename__ + str(directory.id)],
                                   action="create",
                                   description="Created directory '{0}'".format(new_full_path),
                                   comment=directory.comment)

            #refresh directory structure
            self._load_dirs()

            return directory

    ## @brief Updates directory
    #
    # @warning in current realization, if operation succeeded
    # the directories structure will be rebuilt. This mean that
    # (!) all previous pointers to DDirectory objects except Root Directory
    # will become deleted => unusable
    #
    # @param [in] ccdb.Directory object - Directory to update
    # @return bool True if success
    #/
    def update_directory(self, directory):
        """Updates directory"""
        self._ensure_dirs_loaded()

        #get user or get user error if there is no user
        user = self.get_current_user()

        self.session.commit()

        #Log
        self.create_log_record(user,
                               affected_ids=[directory.__tablename__ + directory(directory.id)],
                               action="update",
                               description="Updated directory '{0}'".format(directory.path),
                               comment=directory.comment)

        #refresh directory structure
        self._load_dirs()

    # ------------------------------------------------
    # Deletes directory using path or Directory obj
    # ------------------------------------------------
    def delete_directory(self, dir_or_path):
        """
        Deletes directory using parent path or Directory object

        :param dir_or_path:parent path or Directory object
        :type dir_or_path: str or Directory
        :return: None
        """

        self._ensure_dirs_loaded()

        #get user here to fail if no such user
        user = self.get_current_user()

        #check the type
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

        self.session.delete(directory)
        self.session.commit()

        # refresh directory structure
        self._load_dirs()

        #Log
        self.create_log_record(user,
                               affected_ids=[directory.__tablename__ + str(directory.id)],
                               action="delete",
                               description="Deleted directory '{0}'".format(directory.path),
                               comment=directory.comment)


    # ------------------------------------------------
    # Load all directories
    # ------------------------------------------------
    def _load_dirs(self):
        try:
            self.dirs_by_id = self._get_dirs_by_id_dic(self.session.query(Directory).all())
        except OperationalError as err:
            if 'no such table' in err.message:
                import os

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

        #clear the full path dictionary
        dirs_by_full_path = {self.root_dir.path: self.root_dir}

        #clear subdirectories to append them from the beginning in the next step
        for directory in directories.values():
            directory.sub_dirs = []

        # root dir is artificial (not from database).
        # have to clear it
        self.root_dir.sub_dirs = []

        #begin loop through the directories
        for directory in directories.values():
            assert (isinstance(directory, Directory))

            parent_dir = self.root_dir

            # and check if it have parent directory
            if directory.parent_id > 0:
                #this directory must have a parent! so now search it
                parent_dir = directories[directory.parent_id]

            parent_dir.sub_dirs.append(directory)
            directory.path = posixpath.join(parent_dir.path, directory.name)
            directory.parent_dir = parent_dir
            dirs_by_full_path[directory.path] = directory

        return dirs_by_full_path

    #end of structure_dirs()

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

        parent_dir_path = posixpath.dirname(exact_path)
        table_name = posixpath.basename(exact_path)
        parent_dir = self.get_directory(parent_dir_path)

        query = self.session.query(TypeTable).filter(TypeTable.name == table_name,
                                                     TypeTable.parent_dir_id == parent_dir.id)

        try:
            table = query.one()
        except sqlalchemy.orm.exc.NoResultFound as ex:
            message = "No type table found by exact path: '{0}'".format(exact_path)
            raise TypeTableNotFound(message)

        return table


    # ------------------------------------------------
    # Get all tables in the directory
    # ------------------------------------------------
    def get_type_tables(self, dir_obj_or_path):
        """
        Get all tables in the directory

        :param dir_obj_or_path: directory or path to directory where to look
        :type dir_obj_or_path: str or Directory
        :return: [] of TypeTables for the directory
        :rtype: [] of TypeTable
        """
        self._ensure_dirs_loaded()

        if isinstance(dir_obj_or_path, str):
            parent_dir = self.get_directory(dir_obj_or_path)
        else:
            assert isinstance(dir_obj_or_path, Directory)
            parent_dir = dir_obj_or_path

        return self.session.query(TypeTable).filter(TypeTable.parent_dir_id == parent_dir.id).all()


    # ------------------------------------------------
    # Searches for type tables that matches the patten
    # ------------------------------------------------
    def search_type_tables(self, pattern, dir_obj_or_path=None, limit=0, offset=0):
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

        :return: found TypeTables
        :rtype: []
        """

        self._ensure_dirs_loaded()

        #prepare search pattern for SQL
        pattern = pattern.replace("_", "\\_").replace("*", "%").replace("?", "_")

        #initial query
        query = self.session.query(TypeTable).filter(TypeTable.name.like(pattern, escape="\\"))

        #does parent directory specified?
        parent_dir = None
        if dir_obj_or_path is not None:
            self._ensure_dirs_loaded()

            if isinstance(dir_obj_or_path, str) and dir_obj_or_path != "":
                parent_dir = self.get_directory(dir_obj_or_path)
            else:
                assert isinstance(dir_obj_or_path, Directory)
                parent_dir = dir_obj_or_path

        #add parent directory to query
        if parent_dir is not None:
            query = query.filter(TypeTable.parent_dir_id == parent_dir.id)

        #add limits to query
        if limit != 0: query = query.limit(limit)
        if offset != 0: query = query.offset(offset)

        #execute and return
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

             The map "columns" should contains [("name1", "type"), ("name2", "type"),...] string pairs where:
              -- "name" is the name of the column.
                  Should have the same naming conventions
                  as names of directories and type tables  @see ValidateName()
              -- "type" is the type of the column
                 might be: int, uint, long, ulong, double, bool, string
                 other values will lead to "double" type to be used.
                 @see ccdb::ConstantsTypeColumn::StringToType
                 Thus <"px", "">, <"py", ""> will create two double typed columns

             @param [in] name:              name of the new constants type table
             @param [in] dir_obj_or_path:   parent directory path or ccdb.model.Directory
             @param [in] rows_num:          Number of rows
             @param [in] columns:           a map fo "name", "type" pairs [("name1", "type"), ("name2", "type"),...]
             @param [in] comment:           description for this type table
             @return: NULL if failed, pointer to created object otherwise
        """


        assert len(columns) > 0
        assert rows_num > 0

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

        if user.name == 'anonymous': # anonymous user can't create table types

            raise AnonymousUserForbiddenError
        else:
            table = TypeTable()
            table.name = name
            table.comment = comment
            table.rows_count = rows_num
            table.parent_dir = parent_dir
            table.parent_dir_id = parent_dir.id
            table.author_id = user.id

            for i, (name, col_type) in enumerate(columns):
                column = TypeTableColumn()
                column.name = name
                column.order = i
                col_type = col_type or 'double'
                column.type = col_type
                table.columns.append(column)

            table._columns_count = len(columns)

            self.session.add(table)
            self.session.commit()

            #add log
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

        #Log
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

        :param type_table:   table table info
        :type type_table: TypeTable
        """
        assert isinstance(type_table, TypeTable)

        # get user here to fail if no such user
        user = self.get_current_user()

        data_count = self.session.query(ConstantSet).filter(ConstantSet.type_table_id == type_table.id).count()
        if data_count > 0:
            message = ("Can't delete type table that has data assigned to it."
                       + "The type table '{0}' with id '{1}'. It has {2} data sets which reference it."
                       + "Please, delete the data first").format(type_table.path, type_table.id, data_count)
            raise ValueError(message)

        self.session.delete(type_table)
        self.session.commit()

        # Log
        self.create_log_record(user=user,
                               affected_ids=[type_table.__tablename__ + str(type_table.id)],
                               action="delete",
                               description="Deleted table with path '{0}'".format(type_table.path),
                               comment=type_table.comment)

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
            raise RunRangeNotFound("Run range '{0}-{1}' is not found".format(min_run, max_run))

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
            raise RunRangeNotFound("Run range with name '{0}' is not found".format(name))

    # ------------------------------------------------
    # Gets run range from DB Or Creates RunRange in DB
    # ------------------------------------------------
    # noinspection PyBroadException
    def get_or_create_run_range(self, min_run, max_run, name="", comment=""):
        """
        Gets run range from DB Or Creates RunRange in DB

        :param min_run: min run
        :param max_run: max run
        :param name: name
        :param comment: comment in case we will have to create a new run range
        :return: RunRange object
        :rtype: RunRange
        """

        try:
            run_range = self.get_run_range(min_run, max_run, name)
            return run_range
        except:
            pass

        # if we here we was unable to find a run range
        run_range = RunRange()
        run_range.min = min_run
        run_range.max = max_run
        run_range.name = name
        run_range.comment = comment

        self.session.add(run_range)
        self.session.commit()
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
                       "The run range with id '{0}', name '{2}' [{3} - {4}] has {5} data sets which reference it."
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
            raise VariationNotFound(message)

    # -------------------------------------------------------
    # Searches all variations associated with this type table
    # -------------------------------------------------------
    #noinspection PyUnresolvedReferences
    def get_variations(self, pattern=""):
        """
        Returns all variations associated with this type table

        :return: list of variations
        :rtype: [Variation]
        """

        # initial query
        query = self.session.query(Variation)

        if len(pattern):
            # prepare search pattern for SQL
            pattern = pattern.replace("_", "\\_").replace("*", "%").replace("?", "_")
            query = query.filter(Variation.name.like(pattern, escape="\\"))

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

        if user.name == 'anonymous': # anonymous user can't create variations

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

    ## @brief Update variation
    #
    # Function updates:
    # variation comments
    # variation name if there is no variations with this name
    #
    # @param   [in]  variation to update
    # @return true if success
    #
    # ------------------------------------------------
    # ------------------------------------------------
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

        self.session.delete(variation)
        self.session.commit()
        #Log
        self.create_log_record(user=user,
                               affected_ids=[variation.__tablename__ + str(variation.id)],
                               action="delete",
                               description="Deleted variation '{0}'".format(variation.name),
                               comment=variation.comment)

    # ----------------------------------------------------------------------------------------
    #   A S S I G N M E N T S
    # ----------------------------------------------------------------------------------------
    # ------------------------------------------------
    # Get last Assignment that matches parameters
    # ------------------------------------------------
    def get_assignment(self, path_or_table, run, variation, date_and_time=None, use_variation_tree=True):
        """
        Gets the latest assignment that matches the parameters

        @param run: run number
        @param path_or_table: string with name path of table or Table object
        @param variation: name of the variation or variation object
        @param date_and_time: Constants should be of this or later date
        @param use_variation_tree:

        @return: latest assignment that matches the parameters
        @rtype: Assignment

        @attention (!) the function doesn't accept requests like /some/path:23:mc

        """

        if isinstance(path_or_table, str):
            table = self.get_type_table(path_or_table)
        else:
            assert isinstance(path_or_table, TypeTable)
            table = path_or_table

        if isinstance(variation, str):
            variation_name = variation
        else:
            assert isinstance(variation, Variation)
            variation_name = variation.name

        query = self.session.query(Assignment) \
            .join(ConstantSet).join(TypeTable).join(RunRange).join(Variation) \
            .filter(Variation.name == variation_name) \
            .filter(TypeTable.id == table.id)\
            .filter(RunRange.min <= run).filter(RunRange.max >= run)

        # filter by date and time
        if date_and_time is not None:
            assert isinstance(date_and_time, datetime)
            query = query.filter(Assignment.created <= date_and_time)

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
            return self.get_assignment(path_or_table, run, parent_variation, date_and_time, use_variation_tree)

    # ------------------------------------------------
    # get list of assignments
    # ------------------------------------------------
    def get_assignment_by_id(self, assignment_id):
        """

        :param assignment_id: database id of the assignment
        :return: Assignment by database Id
        :rtype: Assignment
        """
        return self.session.query(Assignment).filter(Assignment.id == assignment_id).one()

    # ------------------------------------------------
    # get list of assignments
    # ------------------------------------------------
    def get_assignments(self, path_or_table, run=-1, variation="", date_and_time=None, limit=0, offset=0):
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
        :return:
        """

        # TODO do for named run
        try:
            isstring = isinstance(path_or_table, basestring)
        except NameError:
            isstring = isinstance(path_or_table, str)

        if isstring:
            table = self.get_type_table(path_or_table)
        else:
            assert isinstance(path_or_table, TypeTable)
            table = path_or_table

        # build query
        query = self.session.query(Assignment) \
            .join(ConstantSet).join(TypeTable).join(RunRange).join(Variation) \
            .filter(TypeTable.id == table.id)

        # filter variation
        if isinstance(variation, str):
            if variation != "":
                query = query.filter(Variation.name == variation)
        else:
            assert isinstance(variation, Variation)
            query = query.filter(Variation.name == variation.name)

        # filter by run
        if run >= 0:
            query = query.filter(RunRange.min <= run).filter(RunRange.max >= run)

        # filter by date and time
        if date_and_time is not None:
            assert isinstance(date_and_time, datetime)
            query = query.filter(Assignment.created <= date_and_time)

        # sort query
        query = query.order_by(desc(Assignment.id))

        # limits
        if limit != 0: query = query.limit(limit)
        if offset != 0: query = query.offset(offset)

        return query.all()

    # ------------------------------------------------
    # Creates Assignment using related object
    # ------------------------------------------------
    def copy_assignment(self, assignment):
        raise NotImplementedError("copy_assignment is not implemented")

    # ------------------------------------------------
    # Creates Assignment
    # ------------------------------------------------
    def create_assignment(self, data, path, min_run, max_run, variation_name, comment):
        """
        Validation:
        If no such run range found, the new will be created (with no name)
        No assignment will be created (and NULL will be returned):
        -- If no type table with such path exists
        -- If data is inconsistent with columns number and rows number
        -- If no variation with such name found

        @param data: tabled data or TextFileDom
        @param path: table path
        @param min_run:
        @param max_run:
        @param variation_name:
        @param comment:
        @return: created assignment
        @rtype: Assignment
        """

        # maybe it is a dom?
        if isinstance(data, TextFileDOM):
            rows = data.rows
        else:
            # it should be list than...
            assert isinstance(data, list)
            rows = data

        # get objects
        table = self.get_type_table(path)  # TODO create path_or_table variable

        variation = self.get_variation(variation_name)  # TODO create variation_name_or_obj instead of variation_name
        run_range = self.get_or_create_run_range(min_run, max_run)

        # validate data.. a little =)
        if len(rows) == 0: raise ValueError(
            "Try to create variation with data length = 0. Fill data prior inserting into database")
        if not isinstance(rows[0], list):
            # the data is plain list, like [1,2,3,4,5,6]
            # rows_count = len(data) / table._columns_count
            raise NotImplementedError()  # TODO check and implement this branch

        # validate that the data rows and cols correspond to table rows and cols
        data_rows_count = len(rows)
        data_cols_count = len(rows[0])

        if data_rows_count != table.rows_count or data_cols_count != table._columns_count:
            message = "Data rows or columns count is inconsistent with table declared rows or columns count. " \
                      "Data rows='{0}', columns='{1}'. Table declared rows='{2}', columns='{3}'" \
                      "".format(data_rows_count, data_cols_count, table.rows_count, table._columns_count)
            raise ValueError(message)

        # check for type
        for row_index, row in enumerate(rows):
            for column_index, cell in enumerate(row):
                column = table.columns[column_index]
                self.validate_data_value(cell, column, column_index, row_index)

        # Get user
        user = self.get_current_user()

        if user.name == 'anonymous': # anonymous user can't create assignments

            raise AnonymousUserForbiddenError
        else:
             # construct assignment
            assignment = Assignment()
            assignment.constant_set = ConstantSet()
            assignment.constant_set.type_table_id = table.id
            assignment.constant_set.type_table = table
            assignment.run_range = run_range
            assignment.run_range_id = run_range.id
            assignment.variation = variation
            assignment.variation_id = variation.id
            assignment.constant_set.data_table = rows
            assignment.comment = comment
            assignment.author_id = user.id
            self.session.add(assignment)
            self.session.commit()

            # add log
            self.create_log_record(user=user,
                                       affected_ids=[assignment.__tablename__ + str(assignment.id)],
                                       action="create",
                                       description="Created assignment '{0}'".format(assignment.request),
                                       comment=assignment.comment)
            return assignment

    # ------------------------------------------------
    # updates assignment comments
    # ------------------------------------------------
    def update_assignment(self, assignment):

        # get user here to fail if no such user
        user = self.get_current_user()

        self.session.commit()

        # Log
        self.create_log_record(user=user,
                               affected_ids=[assignment.__tablename__ + str(assignment.id)],
                               action="update",
                               description="Updated assignment '{0}'".format(assignment.request),
                               comment=assignment.comment)

    # ------------------------------------------------
    # Deletes assignment
    # ------------------------------------------------
    def delete_assignment(self, assignment):
        """
         Deletes assignment

        :param assignment: assignment object to delete. Must have valid ID
        """

        # save assignment parameters
        user = self.get_current_user()
        affected_ids = [assignment.__tablename__ + str(assignment.id)]
        action = "delete"
        description = "Deleted assignment '{0}'".format(assignment.request)
        comment = assignment.comment

        # delete it
        self.session.delete(assignment)
        self.session.commit()

        # Log
        self.create_log_record(user, affected_ids, action, description, comment)

    # ------------------------------------------------
    # validate value
    # ------------------------------------------------
    def validate_data_value(self, value, column, column_index=0, row_index=0):
        col_type = column.type
        failure = False

        if col_type == 'int':
            try:
                value = int(value)
            except ValueError as e:
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
                value = long(value)
            except ValueError:
                failure = True

        elif col_type == 'ulong':
            try:
                value = long(value)
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
        :type username: basestring

        :return: User db object
        :rtype: User
        """
        query = self.session.query(User).filter(User.name == username)
        try:
            return query.one()
        except sqlalchemy.orm.exc.NoResultFound as ex:
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

    ## @brief Validates name for constant type table or directory or column
    #
    # @param     string name
    # @return   bool
    #/
    def validate_name(self, name):
        return path_utils.validate_name(name)

    # ----------------------------------------------------------------------------------------
    #   L O G G I N G
    # ----------------------------------------------------------------------------------------
    def create_log_record(self, user, affected_ids, action, description, comment):
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
        self.session.commit()
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
