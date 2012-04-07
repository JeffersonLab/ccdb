"""@package ProviderBase
Documentation for this module.

More details.
"""
import sys
import os
import ccdb.ccdb_pyllapi
import logging

from PathUtils import PathObject, PathObjectType

log = logging.getLogger("ccdb.provider")

class ProviderBase(object):
    """
    Base and 'abstract' class for ccdb provider
    """
    #_provider = ccdb.ccdb_pyllapi.DataProvider()
    _provider = None


    def __init__(self):
        #self._provider = ccdb.ccdb_pyllapi.DataProvider()
        isinstance(_provider, ccdb.ccdb_pyllapi.DataProvider)
        raise NotImplementedError("ProviderBase is abstract use inherited classes")

#----------------------------------------------------------------------------------------
#	C O N N E C T I O N
#----------------------------------------------------------------------------------------

    ##
    # @brief Connects to database using connection string
    #
    # Connects to database using connection string
    # connection string might be in form:
    # mysql://<username>:<password>@<mysql.address>:<port> <database>
    #
    # @param connectionString "mysql://<username>:<password>@<mysql.address>:<port> <database>"
    # @return True if connected
    def connect(self, connection_string = ""):
        if connection_string == "":
            if "CCDB_CONNECTION" in os.environ:
                connection_string = os.environ["CCDB_CONNECTION"]
            else:
                print "No CCDB_CONNECTION environment variable is set. No connection string to connect"
                return False
        return self._provider.Connect(connection_string)


    ##
    # @brief indicates ether the connection is open or not
    #
    # @return True if connection is open
    #/
    @property
    def is_connected(self):
        "indicates ether the connection is open or not"
        return self._provider.IsConnected()


    ## Closes connection to data
    def disconnect(self):
        "Closes connection to data"
        self._provider.Disconnect()

#----------------------------------------------------------------------------------------
#	D I R E C T O R Y   M A N G E M E N T
#----------------------------------------------------------------------------------------

    ## @brief Gets directory by its full path
    #
    # @param   Full path of the directory
    # @return DDirectory object if directory exists, NULL otherwise
    def get_directory(self, path):
        "Gets directory by its full path"
        return self._provider.GetDirectory(path)


    ## @brief return reference to root directory
    #
    # @warning User should not delete this object
    #
    # @return   DDirectory object pointer
    #/
    def get_root_directory(self):
        "return reference to root directory"
        return self._provider.GetRootDirectory()


    ## @brief SearchDirectories
    #
    # Searches directories that matches the pattern
    # inside parent directory with path @see parentPath
    # or globally through all type tables if parentPath is empty
    # The pattern might contain
    # '*' - any character sequence
    # '?' - any single character
    #
    # paging could be done with @see startWith  @see take
    # startWith=0 and take=0 means select all records;
    #
    # objects that are contained in vector<DDirectory *>& resultDirectories will be
    # 1) if this provider owned - deleted (@see ReleaseOwnership)
    # 2) if not owned - just leaved on user control
    # @param  [in]  searchPattern		Pattern to search
    # @param  [in]  parentPath			Parent path. If NULL search through all directories
    # @param  [in]  startRecord		record number to start with
    # @param  [in]  selectRecords		number of records to select. 0 means select all records
    # @return list of
    def search_directories(self, searchPattern, parentPath="", take=0, startWith=0):
        "Searches directories that matches the pattern "
        return [directory for directory in self._provider.SearchDirectories(searchPattern, parentPath, take, startWith)]


    ## @brief Creates directory using parent parentDirFullPath
    #
    # @warning in current realization, if operation succeeded
    # the directories structure will be rebuilded. This mean that
    # (!) all previous pointers to DDirectories except Root Directory
    # will become deleted => unusable
    #
    # @param newDirName Name of the directory. Contains A-Z, a-z,0-9, _, -,
    # @param parentDirFullPath Path of the parent directory.
    # @param comment comment on this dir. Might be NULL
    # @return True if creation was succeeded
    #/
    def create_directory(self, new_dir_name, parent_full_path, comment=""):
        return self._provider.MakeDirectory(new_dir_name, parent_full_path, comment)


    ## @brief Updates directory
    #
    # @warning in current realization, if operation succeeded
    # the directories structure will be rebuilded. This mean that
    # (!) all previous pointers to DDirectory objects except Root Directory
    # will become deleted => unusable
    #
    # @param [in] ccdb.Directory object - Directory to update
    # @return bool True if success
    #/
    def update_directory(self, directory):
        "Updates directory"
        assert isinstance(directory, ccdb.Directory)
        return self._provider.UpdateDirectory(directory)


    ##
    # @brief Deletes directory using parent path or ccdb.Directory object
    #
    #	"/" - root directory can't be deleted
    #
    # @warning in current realization, if operation succeeded
    # the directories structure will be rebuilded. This mean that
    # (!) all previous pointers to DDirectories except Root Directory
    # will become deleted => unusable
    #
    # @param  [in] path Path of the directory or ccdb.Directory object
    # @return true if no errors
    #/
    def delete_directory(self, directory_or_path):
        "Deletes directory using parent path or ccdb.Directory object"
        assert (isinstance(directory_or_path, ccdb.Directory) or isinstance(directory_or_path, str))
        return self._provider.DeleteDirectory(directory_or_path)


    #----------------------------------------------------------------------------------------
    #	C O N S T A N T   T Y P E   T A B L E
    #----------------------------------------------------------------------------------------


    ## @brief Gets ConstantsType information from the DB
    #
    # @param  [in] path absolute path of the type table
    # @return new object of ConstantsTypeTable
    #/
    def get_type_table(self, exact_path, load_columns = True):
        return self._provider.GetConstantsTypeTable(exact_path, load_columns)


    ## @brief Get all "constants" from current directory
    #
    # @param parentDir
    # @return vector of constants
    #/
    def get_type_tables(self, diectory, loadColumns=True):
        return [table for table in self._provider.GetConstantsTypeTables(diectory)]


    ## @brief Searches for type tables that matches the patten
    #
    # Searches type table that matches the pattern
    # inside parent directory with path @see parentPath
    # or globally through all type tables if parentPath is empty
    # The pattern might contain
    # '*' - any character sequence
    # '?' - any single character
    #
    # paging could be done with @see startWith  @see take
    # startRecord=0 and selectRecords=0 means select all records;
    #
    # objects that are contained in vector<DDirectory *>& resultDirectories will be
    # 1) if this provider owned - deleted (@see ReleaseOwnership)
    # 2) if not owned - just leaved on user control
    # @param  pattern
    # @param  parentPath
    # @return vector<ConstantsTypeTable *>
    #/
    def search_type_tables(self, pattern, parentPath = "", loadColumns=True, take=0, startWith=0):
        "@brief Searches for type tables that matches the patten"
        assert isinstance(self._provider, ccdb.ccdb_pyllapi.DataProvider)
        tables = self._provider.SearchConstantsTypeTables(pattern, parentPath, loadColumns, take, startWith)

        return [table for table in tables]


    ##
    # @brief Counts number of type tables for a given directory
    # @param [in] directory to look tables in
    # @return number of tables to return
    #/
    def count_type_tables(self, directory_obj):
        "Counts number of type tables for a given directory "
        return self._provider.CountConstantsTypeTables(directory_obj)


    ## @brief Loads columns for this table
    #
    # @param parentDir
    # @return True if success
    #/
    def load_colums(self, type_table):
        return self._provider.LoadColumns(type_table)


    ## @brief Creates constant table in database
    #
    # Creates  constants type table in database and returns reference to
    # created table if operation is succeeded (NULL otherwise)
    #
    # The map "columns" should contains <"name", "type"> string pairs where:
    #  -- "name" is the name of the column.
    #      Should have the same naming convetions
    #      as names of directories and type tables  @see ValidateName()
    #  -- "type" is the type of the column
    #     might be: int, uint, long, ulong, double, bool, string
    #     other values will lead to "double" type to be used.
    #     @see ccdb::ConstantsTypeColumn::StringToType
    #     Thus <"px", "">, <"py", ""> will create two double typed columns
    #
    # @param [in] name			name of the new constants type table
    # @param [in] parentPath   parent directory path
    # @param [in] rowsNumber  Number of rows
    # @param [in] columns     a map fo "name", "type" pairs
    # @param [in] comments		description for this type table
    # @return NULL if failed, pointer to created object otherwise
    #/
    def create_type_table(self, name, parentPath, rowsNumber, columns, comments =""):
        "Creates constant table in database"
        #return self._provider.CreateConstantsTypeTable(name, parentPath, rowsNumber, columns, comments)
        directory = self.get_directory(parentPath);
        if not directory:
            log.error("Can't open directory " + repr(parentPath))
            return None

        table = ccdb.ccdb_pyllapi.ConstantsTypeTable()
        table.name = name;
        table.comment = comments
        table.nrows = rowsNumber
        table.parent_dir = directory
        for (colname, coltype) in columns:
            table.add_column(colname, coltype)

        return self._provider.CreateConstantsTypeTable(table)


    ## @brief Uptades constant table in database
    #
    # Thes function updates only:
    # - name
    # - parent directory
    # - commens
    # The function doesnt change any columns and rows number
    # It assumed, that a user should delete the TypeTable and recreate it
    # to perform such changes because it will break all data already stored
    # @param   [in] table with updated info
    # @return bool
    #/
    def update_type_table(self, type_table):
        return self._provider.UpdateConstantsTypeTable(type_table)


    ## @brief Deletes constant type table
    #
    # Deletes constant type table.
    # The type table will not be deleted if any assignment for this table exists
    # Used should delete assignments first and only than delete the type table.
    #
    # @param   table table info
    # @return bool true if success
    #/
    def delete_type_table(self, type_table):
        """
            @brief Deletes constant type table

            Deletes constant type table.
            The type table will not be deleted if any assignment for this table exists
            Used should delete assignments first and only than delete the type table.

            @param   table table info
            @return bool true if success
        """
        return self._provider.DeleteConstantsTypeTable(type_table)

#----------------------------------------------------------------------------------------
#	R U N   R A N G E S
#----------------------------------------------------------------------------------------

    ## @brief GetRun Range from db
    #
    # @param     int min
    # @param     int max
    # @param     const char * name
    # @return   DRunRange* return NULL if not found or failed
    #/
    def get_run_range(self, min_run, max_run, name=""):
        return self._provider.GetRunRange(min_run, max_run, name)


    ## @brief GetRun Range from db
    #
    # @param     int min
    # @param     int max
    # @param     const char * name
    # @return   DRunRange* return NULL if not found or failed
    #/
    def get_named_run_range(self, name):
        return self._provider.GetRunRange(name)


    ## @brief Gets run range from DB Or Creates RunRange in DB
    #
    # @param min run ranges limits
    # @param max run ranges limits
    # @param name name of the run range
    # @return   DRunRange* return NULL if failed
    #/
    def get_or_create_run_range(self, min_run, max_run, name = "", comment = ""):
        return self._provider.GetOrCreateRunRange(min_run, max_run, name, comment)


    ## @brief Updates run range
    #
    # Function updates:
    # - start run number
    # - end run number
    # - comment
    # does not update run range name and id
    # @param [in] run runrange model with proper id and updated data
    # @return bool if no errors and data is changed
    #/
    def update_run_range(self, run_range_obj):
        assert isinstance(run_range_obj, ccdb.RunRange)
        return self._provider.UpdateRunRange(run_range_obj)


    ## @brief Deletes run range
    # @param [in] run model object to delete
    # @return true if no errors and run range deleted
    #/
    def delete_run_range(self, run_range_obj):
        assert isinstance(run_range_obj, ccdb.RunRange)
        return self._provider.DeleteRunRange(run_range_obj)


    ## @brief Conection string that was used on last successfull connect.
    #
    #   Conection string that was used on last successfull connect.
    #   If no any successfull connects were done string::empty will be returned
    #
    #@return  Last connection string or string::empty() if no successfull connection was done
    #/
    @property
    def connection_string(self):
        result = ""
        result = _provider.GetConnectionString()
        return result

#----------------------------------------------------------------------------------------
#	V A R I A T I O N S
#----------------------------------------------------------------------------------------

    ## @brief Get variation by name
    #
    # @param     const char * name
    # @return   DVariation*
    #/
    def get_variation(self, name):
        return self._provider.GetVariation(name)

    ##
    # @brief Searches all variations associated with this type table
    # @param  [out] resultVariations result variations
    # @param  [in]  table table to search run ranges in
    # @param  [in]  run   specified run to search for, if 0 searches for all run ranges
    # @param  [in]  take how many records to take
    # @param  [in]  startWith start record to take
    # @return
    #/
    def get_variations(self, table_or_path, run = 0, take = 0, startWith = 0):
        table = None
        if isinstance(table_or_path, str):
            table = self.get_type_table(table_or_path)
        else:
            table = table_or_path
        if not table: return []
        assert isinstance(table, ccdb.ConstantsTypeTable)
        variations = self._provider.GetVariations(table, run, take, startWith)

        return [variation for variation in variations]


    ## @brief Create variation
    #
    # @param  [in] DVariation * variation
    # @return true if success
    #/
    def create_variation(self, name, comment=""):
        variation = ccdb.Variation
        variation.comment = comment
        variation.name = name
        return self._provider.CreateVariation(variation)


    ## @brief Update variation
    #
    # Function updates:
    # variation comments
    # variation name if there is no variations with this name
    #
    # @param   [in]  variation to update
    # @return true if success
    #/
    def update_variation(self, variation):
        assert isinstance(variation, ccdb.Variation)
        self._provider.UpdateVariation(variation)


    ## @brief Delete variation
    #
    # Variation will be deleted only
    # if there is no assignments for this variation
    # @param    [in] variation to delete
    # @return   bool
    #/
    def delete_variation(self, variation):
        assert isinstance(variation, ccdb.Variation)
        self._provider.DeleteVariation(variation)

#----------------------------------------------------------------------------------------
#	A S S I G N M E N T S
#----------------------------------------------------------------------------------------


    ## @brief Get Assignment with data blob only
    #
    # @see GetAssignmentFull
    # @param     int run
    # @param     path to constant path
    # @return    NULL if no assignment is found or error
    #/
    def get_short_assignment(self, run, path, variation):
        return self._provider.GetAssignmentShort(run, path, variation)


    ## @brief Get last Assignment with all related objects
    #
    # @param     int run
    # @param     path to constant path
    # @return NULL if no assignment is found or error
    #/
    def get_assignment(self, run, path, variation):
        return self._provider.GetAssignmentFull(run, path, variation)


    ## @brief Creates Assignment using related object
    #
    # @warning since composing a "NEW" DAssignment is complex operation
    #          it is suggested to use other reloads of this function for users
    #          for creating "new" assignments.
    #          This function is not set as "protected" only to provide easy "copy" operations
    #
    # This function assumes that all needed data is already contained in assignment
    # object. Including correct type table and data blob.
    #
    # The function is powerful to copy assignment. For example from one variation to another.
    #
    # The function changes DAssignment object by setting Id and DataVaultId by new values
    #
    # @param    DAssignment * assignment
    # @return   DAssignment* adjusted with Id-s of objects and etc
    #/
    def copy_assignment(self, asssignment):
        return self._provider.CreateAssignment(assignment)


    ## @brief Creates Assignment using related object
    #
    # Creates Assignment using related object.
    #
    # Validation:
    # If no such run range found, the new will be created (with no name)
    # No action will be done (and NULL will be returned):
    # -- If no type table with such path exists
    # -- If data is inconsistent with columns number and rows number
    # -- If no variation with such name found
    #
    # @brief
    # @param data  		by rows and columns
    # @param runMin		run range minimum
    # @param runMax     run range maximum
    # @param variationName	name of variation
    # @param comments   comments
    # @return NULL if failed, DAssignment reference if success
    #/
    def create_assignment(self, data, path, min_run, max_run, variation, comment):
        table = self.get_type_table(path);
        if not table:
            log.warning("Table : " + path + " - was not found. ")
            log.debug(self, data, path, min_run, max_run, variation, comment)
            return None

        assert isinstance(table, ccdb.ConstantsTypeTable)

        rows = None

        #maybe it is a dom?
        if isinstance(data, ccdb.TextFileDOM):
            rows = data.rows
        else:
            #it should be list than...
            rows = data

        #finally checking data type and that there is at least one row and column
        if (not isinstance(rows, list)) or\
           (not len(rows)) or\
           (not isinstance(rows[0], list)) or\
           (not len(rows[0])):
            log.warning("Data type is wrong in python function")
            return None

        #Create StringVectorVector for C++ wrapped function
        rows_vector = ccdb.StringVectorVector()
        for row in rows:
            cells_vector = ccdb.StringVector()
            for cell in row:
                if isinstance(cell, str):
                    cells_vector.push_back(cell)
                else:
                    cells_vector.push_back(repr(cell))
            rows_vector.push_back(cells_vector)
        print "rows " +repr(rows_vector.size())
        #do the job

        return self._provider.CreateAssignment(rows_vector, path, min_run, max_run, variation, comment)


    ## @brief Creates Assignment using related object
    #
    # Creates Assignment using related object.
    #
    # Validation:
    # If no such run range found, the new will be created (with no name)
    # No action will be done (and false will be returned):
    # -- If no type table with such path exists
    # -- If data is inconsistant with columns number and rows number
    # -- If no variation with such name found
    #
    # @brief
    # @param data  		by rows and columns
    # @param runRangeName
    # @param variation	name of vaiation
    # @param comments   comments
    # @return NULL if failed, DAssignment reference if success
    #/
    #virtual DAssignment* CreateAssignment(const vector<vector<string> > &data, const string& path, const string& runRangeName, const string& variationName, const string& comments);


    ##
    # @brief Get assigments for particular run
    #
    # returns vector of assignments
    # Variation: if variation is not empty string the assignments for specified variation will be returned
    #            otherwise all variations will be accepted
    #
    # Date: if date is not 0, assignments which are earlier than this date will be returned
    #       otherwise returned assignments will be not filtered by date
    #
    # Paging: paging could be done with  @see take ans @see startWith
    #         take=0, startWith=0 means select all records;
    #
    #
    # @param [in]  path
    # @param [in]  run
    # @param [in]  variation
    # @param [in]  date
    # @param [in]  take
    # @param [in]  startWith
    # @return assingments
    #/
    def get_assignments(self, path, run, variation = "default", unix_time_stamp =0, take=0, start_with=0):
        result = self._provider.GetAssignments(path, run, variation, unix_time_stamp, take, start_with)
        return [asg for asg in result]


    ##
    # @brief Get assigments for particular run
    #
    # returns vector of assignments
    # Variation: if variation is not emty string the assignments for specified variation will be returned
    #            otherwise all variations will be accepted
    #
    # Date: if date is not 0, assignments wich are earlier than this date will be returned
    #       otherwise returned assignments will be not filtred by date
    #
    # Paging: paging could be done with  @see take ans @see startWith
    #         take=0, startWith=0 means select all records;
    #
    #
    # @param [out] assingments
    # @param [in]  path
    # @param [in]  run
    # @param [in]  variation
    # @param [in]  date
    # @param [in]  take
    # @param [in]  startWith
    # @return
    #/
    #virtual vector<DAssignment *> GetAssignments(const string& path, const string& runName, const string& variation="", time_t date=0, int take=0, int startWith=0)=0;

    ##
    # @brief the function updates assignment comments
    # @param assignment
    # @return
    #/
    def update_assignment(self, assignment):
        return self._provider.UpdateAssignment(assignment)


    ##
    # @brief Deletes assignment
    # @param assignment object to delete. Must have valid ID
    # @return true if success
    #/
    def delete_assignment(self, assignment_obj):
        return self._provider.DeleteAssignment(assignment)


    ##
    # @brief Fill assignment with data if it has proper ID
    #
    # The function actually gets assignment by ID.
    #
    # A problem: is that for DB providers the id is assignment->GetId().
    #            For file provider the id is probably a type table full path
    # A solution:
    #    is to have this function that accepts DAssignment* assignment.
    #    DAssignment* assignment incapsulates the id (one way or another)
    #    And each provider could check if this DAssignment have valid Id,
    #    fill assignment with data and return true.
    #    Or just return "false" if something goes wrong;
    #
    # @param [in, out] assignment to fill
    # @return true if success and assignment was filled with data
    #/
    def fill_assignment(self, assignment):
        return self._provider.FillAssignment(assignment)

#----------------------------------------------------------------------------------------
#	E R R O R   H A N D L I N G
#----------------------------------------------------------------------------------------
    ##
    # @brief Get number of errors
    # @return
    #/
    def get_num_errors(self):
        return self._provider.GetNErrors();


    ##
    # @brief Get vector of last errors
    #/
    def get_errors(self):
        codes = self._provider.GetErrors()
        return [code for code in codes]


    ##
    # @brief Gets last of the last error
    # @return error code
    #/
    def get_last_error(self):
        return self._provider.GetLastError()


#----------------------------------------------------------------------------------------
#	O T H E R   F U N C T I O N S
#----------------------------------------------------------------------------------------

    ## @brief Validates name for constant type table or directory or column
    #
    # @param     string name
    # @return   bool
    #/
    def validate_name(self, name):
        return self._provider.ValidateName(name)

#----------------------------------------------------------------------------------------
#	L O G G I N G
#----------------------------------------------------------------------------------------
    @property
    def log_user_name(self):
        return elf._provider.GetLogUserName()

    @log_user_name.setter
    def log_user_name(self, user_name):
        self._provider.SetLogUserName(user_name)
