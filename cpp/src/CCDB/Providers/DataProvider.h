#ifndef _DDataProvider_
#define _DDataProvider_

#include <string>
#include <vector>
#include <map>

#include "CCDB/Providers/IAuthentication.h"
#include "CCDB/Model/ObjectsOwner.h"
#include "CCDB/Model/Assignment.h"
#include "CCDB/Model/ConstantsTypeTable.h"
#include "CCDB/Model/Directory.h"
#include "CCDB/Model/RunRange.h"
#include "CCDB/Model/Variation.h"
#include "CCDB/CCDBError.h"



/* @class DataProvider
 * This is the main base interface to the Providers class family. 
 * Each derived <Something>Provider, provides access to data from a specified data source
 * I.e. MySQLDataProvider works with MySQL database, SQLiteDataProvider works with SQLite
 *
 *==============================================
 *Low Level API
 *
 *                    ^ ^ ^  
 *                    | | |                            
 *  +------------------------------------------+
 *  | Data Model:  Assignment,  TypeTable, ... |    -   Data model is returned to user
 *  +------------------------------------------+        
 *                       ^                              
 *                       |                              
 *                       |                              
 *  +------------------------------------------+        
 *  |    DataProvider - Interface to database  |    -   User calls DataProvider functions to get data user needs
 *  +------------------------------------------+        
 *                       |                              
 *             +---------------------+                  
 *            /                       \                 
 *  +----------------+        +----------------+        
 *  |  MySQLProvider |        |  SQLiteProvider|    -   Classes inherited from DataProvider do actual queries to data sources
 *  +----------------+        +----------------+        
 *          |                          |                
 *  <================>        <================>        
 *  | MySQL Database |        |     SQLite     |    -   Data storages 
 *  <________________>        <________________>
 *
 *
 *
 *
 */
namespace ccdb
{

class DataProvider: public ObjectsOwner
{
public:

    DataProvider(void);
    virtual ~DataProvider(void);
    
    //----------------------------------------------------------------------------------------
    //  C O N N E C T I O N
    //----------------------------------------------------------------------------------------

    /**
     * @brief Connects to database using connection string
     * 
     * Connects to database using connection string
     * connection string might be in form: 
     * mysql://<username>:<password>@<mysql.address>:<port> <database>
     * 
     * @param connectionString "mysql://<username>:<password>@<mysql.address>:<port> <database>"
     * @return true if connected
     */
    virtual bool Connect(std::string connectionString) = 0;

    /**
     * @brief closes connection to data
     */
    virtual void Disconnect()= 0;

    /**
     * @brief indicates ether the connection is open or not
     * 
     * @return true if  connection is open
     */
    virtual bool IsConnected()=0;
    
    /** @brief Connection string that was used on last successful connect.
     *
     * Connection string that was used on last successful connect.
     * If no any successfull connects were done string::empty will be returned
     *
     * @return  Last connection string or string::empty() if no successfull connection was done
     */
    virtual std::string GetConnectionString();

    //----------------------------------------------------------------------------------------
    //  D I R E C T O R Y   M A N G E M E N T
    //----------------------------------------------------------------------------------------
#ifndef __GNUC__
    #pragma region Directory managemend
#endif
    /** @brief Gets directory by its full path
    *
    * @param   Full path of the directory
    * @return DDirectory object if directory exists, NULL otherwise
    */
    virtual Directory* GetDirectory(const string& path)=0;

    /** @brief return reference to root directory
     * 
     * Root directory contains all other directories. It is not stored in any database
     *
     * @warning User should not delete this object 
     *
     * @return   DDirectory object pointer
     */
    virtual Directory * const GetRootDirectory();

    /** @brief Searches for directory 
     *
     * Searches directories that matches the pattern 
     * inside parent directory with path @see parentPath 
     * or globally through all type tables if parentPath is empty
     * The pattern might contain
     * '*' - any character sequence 
     * '?' - any single character
     *
     * paging could be done with @see startWith  @see take
     * startWith=0 and take=0 means select all records;
     *
     * objects that are contained in vector<DDirectory *>& resultDirectories will be
     * 1) if this provider owned - deleted (@see ReleaseOwnership)
     * 2) if not owned - just leaved on user control
     *
     * @param  [out] resultDirectories  search result
     * @param  [in]  searchPattern      Pattern to search
     * @param  [in]  parentPath         Parent path. If NULL search through all directories
     * @param  [in]  startRecord        record number to start with
     * @param  [in]  selectRecords      number of records to select. 0 means select all records
     * @return bool true if there were error (even if 0 directories found) 
     */
    virtual bool SearchDirectories(vector<Directory *>& resultDirectories, const string& searchPattern, const string& parentPath="", int take=0, int startWith=0)=0;
    
    
    /** @brief SearchDirectories
     *
     * Searches directories that matches the pattern 
     * inside parent directory with path @see parentPath 
     * or globally through all type tables if parentPath is empty
     * The pattern might contain
     * '*' - any character sequence 
     * '?' - any single character
     *
     * paging could be done with @see startWith  @see take
     * startWith=0 and take=0 means select all records;
     *
     * objects that are contained in vector<DDirectory *>& resultDirectories will be
     * 1) if this provider owned - deleted (@see ReleaseOwnership)
     * 2) if not owned - just leaved on user control
     * @param  [in]  searchPattern      Pattern to search
     * @param  [in]  parentPath         Parent path. If NULL search through all directories
     * @param  [in]  startRecord        record number to start with
     * @param  [in]  selectRecords      number of records to select. 0 means select all records
     * @return list of 
     */
    virtual vector<Directory *> SearchDirectories(const string& searchPattern, const string& parentPath="", int take=0, int startWith=0);

    protected:
    
    /** @brief Reads all directories from DB
     * 
	 * Explicitly forces to load directories from DB and build directory structure
	 * (!) At this implementation all existing directories references will be deleted, 
	 * thus  references to them will become broken
	 * @return   bool
	 */
	virtual bool LoadDirectories() = 0;

    virtual void BuildDirectoryDependencies();  /// Builds directory relational structure. Used right at the end of RetriveDirectories().
    virtual bool CheckDirectoryListActual();    /// Checks if directory list is actual i.e. nobody changed directories in database
    virtual bool UpdateDirectoriesIfNeeded();   /// Update directories structure if this is required

#ifndef __GNUC__
    #pragma endregion Directory managemend
#endif
    //----------------------------------------------------------------------------------------
    //  C O N S T A N T   T Y P E   T A B L E
    //----------------------------------------------------------------------------------------
#ifndef __GNUC__
	#pragma region Type tables
#endif

    public:
    /** @brief Gets ConstantsType information from the DB
     *
     * @param  [in] path absolute path of the type table
     * @return new object of ConstantsTypeTable
     */
    virtual ConstantsTypeTable * GetConstantsTypeTable(const string& path, bool loadColumns=false);

    /** @brief Gets ConstantsType information from the DB
     *
     * @param  [in] name name of ConstantsTypeTable
     * @param  [in] parentDir directory that contains type table
     * @return new object of ConstantsTypeTable
     */
    virtual ConstantsTypeTable * GetConstantsTypeTable(const string& name, Directory *parentDir, bool loadColumns=false)=0;

    /** @brief Gets ConstantsType information from the DB
     *
     * @param  [in] name name of ConstantsTypeTable
     * @param  [in] parentDir directory that contains type table
     * @return new object of ConstantsTypeTable
     */
    virtual bool GetConstantsTypeTables(vector<ConstantsTypeTable *>& typeTables,const string& parentDirPath, bool loadColumns=false) =0;

    /** @brief Get all "constants" from current directory
     *
     * @param parentDir
     * @return vector of constants
     */
    virtual vector<ConstantsTypeTable *> GetConstantsTypeTables (Directory *parentDir, bool loadColumns=false)=0;

    /** @brief Get all "constants" from current directory
     *
     * @param parentDir
     * @return vector of constants
     */
    virtual bool GetConstantsTypeTables(vector<ConstantsTypeTable *>& typeTables, Directory *parentDir, bool loadColumns=false) =0;
    
    /** @brief Searches for type tables that matches the patten
     *
     * Searches type table that matches the pattern 
     * inside parent directory with path @see parentPath 
     * or globally through all type tables if parentPath is empty
     * The pattern might contain
     * '*' - any character sequence 
     * '?' - any single character
     *
     * paging could be done with  @see take ans @see startWith 
     * take=0, startWith=0 means select all records;
     *
     * objects that are contained in vector<DDirectory *>& resultDirectories will be
     * 1) if this provider owned - deleted (@see ReleaseOwnership)
     * 2) if not owned - just leaved on user control
     * @param  pattern
     * @param  parentPath
     * @return bool
     */
    virtual bool SearchConstantsTypeTables(vector<ConstantsTypeTable *>& typeTables, const string& pattern, const string& parentPath = "", bool loadColumns=false, int take=0, int startWith=0 )=0;

    /** @brief Searches for type tables that matches the patten
     *
     * Searches type table that matches the pattern 
     * inside parent directory with path @see parentPath 
     * or globally through all type tables if parentPath is empty
     * The pattern might contain
     * '*' - any character sequence 
     * '?' - any single character
     *
     * paging could be done with @see startWith  @see take
     * startRecord=0 and selectRecords=0 means select all records;
     *
     * objects that are contained in vector<DDirectory *>& resultDirectories will be
     * 1) if this provider owned - deleted (@see ReleaseOwnership)
     * 2) if not owned - just leaved on user control
     * @param  pattern
     * @param  parentPath
     * @return vector<ConstantsTypeTable *>
     */
    virtual vector<ConstantsTypeTable *> SearchConstantsTypeTables(const string& pattern, const string& parentPath = "", bool loadColumns=false, int take=0, int startWith=0 )=0;
    
    /**
     * @brief This function counts number of type tables for a given directory 
     * @param [in] directory to look tables in
     * @return number of tables to return
     */
    virtual int CountConstantsTypeTables(Directory *dir)=0;
    
    /** @brief Loads columns for this table
     *
     * @param parentDir
     * @return vector of constants
     */
    virtual bool LoadColumns(ConstantsTypeTable* table) =0;

#ifndef __GNUC__
	#pragma endregion Type tables
#endif

    //----------------------------------------------------------------------------------------
    //  R U N   R A N G E S
    //----------------------------------------------------------------------------------------

    /** @brief GetRun Range from db
     *
     * @param     int min
     * @param     int max
     * @param     const char * name
     * @return   DRunRange* return NULL if not found or failed
     */
    virtual RunRange* GetRunRange(int min, int max, const string& name = "")=0;

    
    /**
     * @brief Searches all run ranges associated with this type table
     * 
     * @param [out] resultRunRanges result run ranges
     * @param [in]  table       table to search run ranges in
     * @param [in]  variation   variation to search, if not set all variations will be selected
     * @param [in]  take            how many records to take
     * @param [in]  startWith   start record to take
     * @return 
     */
    virtual bool GetRunRanges(vector<RunRange *>& resultRunRanges, ConstantsTypeTable *table, const string& variation="", int take=0, int startWith=0 )=0;
    
    /**
     * @brief Searches all run ranges associated with this type table
     * 
     * @param [out] resultRunRanges result run ranges
     * @param [in]  table       table to search run ranges in
     * @param [in]  variation   variation to search, if not set all variations will be selected
     * @param [in]  take            how many records to take
     * @param [in]  startWith   start record to take
     * @return 
     */
    virtual bool GetRunRanges(vector<RunRange *>& resultRunRanges, const string& typeTablePath, const string& variation="",int take=0, int startWith=0 );
    
    /** @brief GetRun Range from db
     *
     * @param     int min
     * @param     int max
     * @param     const char * name
     * @return   DRunRange* return NULL if not found or failed
     */
    virtual RunRange* GetRunRange(const string& name)=0;

    //----------------------------------------------------------------------------------------
    //  V A R I A T I O N
    //----------------------------------------------------------------------------------------
    /** @brief Get variation by name
     *
     * @param     const char * name
     * @return   DVariation*
     */
    virtual Variation* GetVariation(const string& name)=0;
     
    /**
     * @brief Searches all variations associated with this type table
     * @param  [out] resultVariations result variations
     * @param  [in]  table table to search run ranges in
     * @param  [in]  run   specified run to search for, if 0 searches for all run ranges
     * @param  [in]  take how many records to take
     * @param  [in]  startWith start record to take
     * @return 
     */
    virtual bool GetVariations(vector<Variation *>& resultVariations, ConstantsTypeTable *table, int run=0, int take=0, int startWith=0 )=0;

    /**
     * @brief Searches all variations associated with this type table
     * @param  [out] resultVariations result variations
     * @param  [in]  table table to search run ranges in
     * @param  [in]  run   specified run to search for, if 0 searches for all run ranges
     * @param  [in]  take how many records to take
     * @param  [in]  startWith start record to take
     * @return 
     */
    virtual vector<Variation *> GetVariations(ConstantsTypeTable *table, int run=0, int take=0, int startWith=0 )=0;
    
    /**
     * @brief Searches all variations associated with this type table
     * @param  [out] resultVariations result variations
     * @param  [in]  path path to table to search run ranges in
     * @param  [in]  run   specified run to search for, if 0 searches for all run ranges
     * @param  [in]  take how many records to take
     * @param  [in]  startWith start record to take
     * @return 
     */
    virtual bool GetVariations(vector<Variation *>& resultVariations, const string& path, int run=0, int take=0, int startWith=0 );
    
    
    //----------------------------------------------------------------------------------------
    //  A S S I G N M E N T S
    //----------------------------------------------------------------------------------------
#ifndef __GNUC__
	#pragma region Assignments
#endif

    /** @brief Get Assignment with data blob only
     *
     * This function is optimized for fast data retrieving and is assumed to be performance critical;
     * This function doesn't return any specified information like variation object or run-range object
     * @see GetAssignmentFull
     * @param [in] run - run number
     * @param [in] path - object path
     * @param [in] variation - variation name
     * @param [in] loadColumns - optional, do we need to load table columns information (for column names and types) or not
     * @return DAssignment object or NULL if no assignment is found or error
     */
    virtual Assignment* GetAssignmentShort(int run, const string& path, const string& variation="default", bool loadColumns=false)=0;
    
    
    /** @brief Get specified by creation time version of Assignment with data blob only.
     *
     * This function is optimized for fast data retrieving and is assumed to be performance critical;
     * This function doesn't return any specified information like variation object or run-range object
     * The Time is a timestamp, data that is equal or earlier in time than that timestamp is returned
     *
     * @remarks this function is named so
     * @param [in] run - run number
     * @param [in] path - object path
     * @param [in] time - timestamp, data that is equal or earlier in time than that timestamp is returned
     * @param [in] variation - variation name
     * @param [in] loadColumns - optional, do we need to load table columns information (for column names and types) or not
     * @return DAssignment object or NULL if no assignment is found or error
     */
    virtual Assignment* GetAssignmentShort(int run, const string& path, time_t time, const string& variation="default", bool loadColumns=false)=0;
       

    /** @brief Get last Assignment with all related objects
     *
     * @param     int run
     * @param     path to constant path
     * @return NULL if no assignment is found or error
     */
    virtual Assignment* GetAssignmentFull(int run, const string& path, const string& variation="default")=0;
    
    
    /** @brief  Get specified version of Assignment with all related objects
     *
     * @param     int run
     * @param     const char * path
     * @param     const char * variation
     * @param     int version
     * @return   DAssignment*
     */
    virtual Assignment* GetAssignmentFull(int run, const string& path, int version, const string& variation="default")=0;
    
    /**
     * @brief Complex and universal function to retrieve assignments
     * 
     * @warning this function is too complex for users. 
     *          Use overloaded GetAssignments instead of it.
     *          And only use this function if others are inapropriate
     * 
     * This function is universal assignments getter. 
     * Provided fields allows to select assignments (arrays and single assignments) 
     * for most cases. Other GetAssignments(...) and GetAssignmentFull(...) 
     * functions relie on this function.  
     *
     * 
     * runMin, runMax:
     *       applied if one !=0. Thus runMin=runMax=0 will select all run ranges
     *       If one needs particular run, runMin=runMax=<NEEDED RUN NUMBER> should be used
     * 
     * runRangeName:
     *       will be ignored if equals to ""
     * 
     * variation:
     *       if "", all variations will be get
     * 
     * date: 
     *       unix timestamp that indicates the latest time to select assignments from
     *       if 0 - time will be ignored
     * sortby:
     *       0 - `assignments`.`created` DESC
     *       1 - `assignments`.`created` ASC
     * 
     * take, startWith
     *       paging parameters
     * 
     * @param [out] assingments result assignment list
     * @param [in] path       path of type table
     * @param [in] run        specified range. If not set all ranges
     * @param [in] variation  variation, if not set, all variations
     * @param [in] date       nearest date
     * @param [in] sortBy     sortby order
     * @param [in] startWith  record to start with
     * @param [in] take       records to select
     * @return true if no errors (even if no assignments was selected)
     */
    virtual bool GetAssignments(vector<Assignment *> &assingments,const string& path, int runMin, int runMax, const string& runRangeName, const string& variation, time_t beginTime, time_t endTime, int sortBy=0, int take=0, int startWith=0)=0;
    
    
    /**
     * @brief Get assigments for particular run
     * 
     * returns vector of assignments
     * Variation: if variation is not empty string the assignments for specified variation will be returned
     *            otherwise all variations will be accepted
     * 
     * Date: if date is not 0, assignments which are earlier than this date will be returned
     *       otherwise returned assignments will be not filtered by date
     * 
     * Paging: paging could be done with  @see take ans @see startWith 
     *         take=0, startWith=0 means select all records;
     * 
     * 
     * @param [out] assingments
     * @param [in]  path
     * @param [in]  run
     * @param [in]  variation
     * @param [in]  date
     * @param [in]  take
     * @param [in]  startWith
     * @return 
     */
    virtual bool GetAssignments(vector<Assignment *> &assingments,const string& path, int run, const string& variation="", time_t date=0, int take=0, int startWith=0)=0;

    /**
     * @brief Get assigments for particular run
     * 
     * returns vector of assignments
     * Variation: if variation is not empty string the assignments for specified variation will be returned
     *            otherwise all variations will be accepted
     * 
     * Date: if date is not 0, assignments which are earlier than this date will be returned
     *       otherwise returned assignments will be not filtered by date
     * 
     * Paging: paging could be done with  @see take ans @see startWith 
     *         take=0, startWith=0 means select all records;
     * 
     *
     * @param [in]  path
     * @param [in]  run
     * @param [in]  variation
     * @param [in]  date
     * @param [in]  take
     * @param [in]  startWith
     * @return assingments
     */
    virtual vector<Assignment *> GetAssignments(const string& path, int run, const string& variation="", time_t date=0, int take=0, int startWith=0)=0;

    /**
     * @brief Get assigments for particular run
     * 
     * returns vector of assignments
     * Variation: if variation is not emty string the assignments for specified variation will be returned
     *            otherwise all variations will be accepted
     * 
     * Date: if date is not 0, assignments wich are earlier than this date will be returned
     *       otherwise returned assignments will be not filtred by date
     * 
     * Paging: paging could be done with  @see take ans @see startWith 
     *         take=0, startWith=0 means select all records;
     * 
     * 
     * @param [out] assingments
     * @param [in]  path
     * @param [in]  run
     * @param [in]  variation
     * @param [in]  date
     * @param [in]  take
     * @param [in]  startWith
     * @return 
     */
    virtual bool GetAssignments(vector<Assignment *> &assingments,const string& path, const string& runName, const string& variation="", time_t date=0, int take=0, int startWith=0)=0;

    /**
     * @brief Get assigments for particular run
     * 
     * returns vector of assignments
     * Variation: if variation is not emty string the assignments for specified variation will be returned
     *            otherwise all variations will be accepted
     * 
     * Date: if date is not 0, assignments wich are earlier than this date will be returned
     *       otherwise returned assignments will be not filtred by date
     * 
     * Paging: paging could be done with  @see take ans @see startWith 
     *         take=0, startWith=0 means select all records;
     * 
     * 
     * @param [out] assingments
     * @param [in]  path
     * @param [in]  run
     * @param [in]  variation
     * @param [in]  date
     * @param [in]  take
     * @param [in]  startWith
     * @return 
     */
    virtual vector<Assignment *> GetAssignments(const string& path, const string& runName, const string& variation="", time_t date=0, int take=0, int startWith=0)=0;
    
    
    /**
     * @brief Fill assignment with data if it has proper ID
     * 
     * The function actually gets assignment by ID. 
     * 
     * A problem: is that for DB providers the id is assignment->GetId().
     *            For file provider the id is probably a type table full path
     * A solution: 
     *    is to have this function that accepts DAssignment* assignment.
     *    DAssignment* assignment incapsulates the id (one way or another)
     *    And each provider could check if this DAssignment have valid Id,
     *    fill assignment with data and return true. 
     *    Or just return "false" if something goes wrong;
     * 
     * @param [in, out] assignment to fill
     * @return true if success and assignment was filled with data
     */
    virtual bool FillAssignment(Assignment* assignment)=0;
    
#ifndef __GNUC__
	#pragma endregion Assignments
#endif

    //----------------------------------------------------------------------------------------
    //  E R R O R   H A N D L I N G 
    //----------------------------------------------------------------------------------------
    /**
     * @brief Get number of errors 
     * @return 
     */
    virtual int GetNErrors();
    
    /**
     * @brief Get vector of last errors 
     */
    virtual const std::vector<int>& GetErrorCodes();
    
    /** @brief return vector of errors.
     * @warning the error objects are deleted on next function that clears errors. 
     * (!) Copy this error objects before next provider function call. 
     * @return   std::vector<DCcdbError *>
     */
    virtual std::vector<CCDBError *> GetErrors();
    
    /**
     * @brief Gets last of the last error
     * @return error code
     */
    virtual int GetLastError();
    
    /** @brief Logs error 
    *
    * @param errorCode Error codes see DCCDBGlobals.h
    * @param module Caller should specify method name here
    * @param message    Message of the error
    * @return   void
    */
    virtual void Error(int errorCode, const std::string& module, const std::string& message);

    /** @brief Logs error 
    *
    * @param errorCode Error codes see DCCDBGlobals.h
    * @param module Caller should specify method name here
    * @param message    Message of the error
    * @return   void
    */
    virtual void Warning(int errorCode, const std::string& module, const std::string& message);

    /** @brief Clears Errors
     * function is called on start of each function that produce errors
     * @return   void
     */
    virtual void ClearErrors();
    
    //----------------------------------------------------------------------------------------
    //  O T H E R   F U N C T I O N S
    //----------------------------------------------------------------------------------------
    
    /** @brief Validates name for constant type table or directory or column
     *
     * @param     string name
     * @return   bool
     */
    bool ValidateName(const string& name);



    //----------------------------------------------------------------------------------------
    //  L O G G I N G
    //----------------------------------------------------------------------------------------
    std::string GetLogUserName() const { return mLogUserName; }      ///User name for logging
    void SetLogUserName(std::string val) { mLogUserName = val; }     ///User name for logging
	
    
    
protected:
    /** @brief Sets IsLoaded() and  resets IsChanged()Yt
     *
     * @param     obj
     * @return   void
     */
    void SetObjectLoaded(StoredObject* obj);
    
    /******* D I R E C T O R I E S   W O R K *******/ 
    vector<Directory *>  mDirectories;
    map<dbkey_t,Directory *> mDirectoriesById;
    map<string,Directory *>  mDirectoriesByFullPath;
    bool mDirsAreLoaded;                 //Directories are loaded from database
    bool mNeedCheckDirectoriesUpdate;    //Do we need to check each time iff directories are updated or not
    Directory *mRootDir;                ///root directory. This directory contains all other directories. It is not stored in databases

    
    /** 
        @brief Clear error state on start of each function that emits error
     */
    virtual void ClearErrorsOnFunctionStart();
    
    vector<int> mErrorCodes;            ///vector of last errors

    vector<CCDBError *> mErrors;        ///errors 
    
    int mLastError;                     ///last error
    
    const int mMaximumErrorsToHold;     ///=100 Maximum errors to hold in @see mLastErrors
    
    std::string mLogUserName;           ///User name

    std::string mConnectionString;      ///Connection string that was used on last successfully connect.

    IAuthentication * mAuthentication;

    map<dbkey_t, Variation *> mVariationsById;
};
}
#endif // _DDataProvider_

