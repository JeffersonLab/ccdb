#ifndef _DDataProvider_
#define _DDataProvider_

#include <string>
#include <stdint.h>
#include <vector>
#include <map>

#include "CCDB/Model/Assignment.h"
#include "CCDB/Model/ConstantsTypeTable.h"
#include "CCDB/Model/Directory.h"
#include "CCDB/Model/RunRange.h"
#include "CCDB/Model/Variation.h"


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
    class DataProvider
    {
    public:

        DataProvider();
        virtual ~DataProvider();

        //----------------------------------------------------------------------------------------
        //  A B S T R A C T   I N T E R F A C E
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
        virtual void Connect(const std::string& connectionString) = 0;

        /**
         * @brief closes connection to data
         */
        virtual void Disconnect() = 0;

        /**
         * @brief indicates ether the connection is open or not
         *
         * @return true if  connection is open
         */
        virtual bool IsConnected() = 0;

        /** @brief Reads all directories from DB
         *
         * Explicitly forces to load directories from DB and build directory structure
         * (!) At this implementation all existing directories references will be deleted,
         * thus  references to them will become broken
         * @return   bool
         */
        virtual void LoadDirectories() = 0;

        /** @brief Gets ConstantsType information from the DB
         *
         * @param  [in] name name of ConstantsTypeTable
         * @param  [in] parentDir directory that contains type table
         * @return new object of ConstantsTypeTable
         */
        virtual ConstantsTypeTable * GetConstantsTypeTable(const std::string& name, Directory *parentDir, bool loadColumns)=0;


        /** @brief gets all type tables from DB
         * @return bool
         */
        virtual std::vector<ConstantsTypeTable *> GetAllConstantsTypeTables(bool loadColumns)=0;



        /** @brief Get variation by name*/
        virtual Variation* GetVariation(const string& name)=0;

        /** @brief Get specified by creation time version of Assignment with data blob only.
        *
        * This function is optimized for fast data retrieving and is assumed to be performance critical;
        * This function doesn't return any specified information like variation object or run-range object
        * The Time is a timestamp, data that is equal or earlier in time than that timestamp is returned
        *
        * @remarks this function is named so
        * @param [in] run - run number
        * @param [in] path - object path
        * @param [in] time - timestamp: the newest data created at or before the end of that second (T.999999);
        *                    0 means no time limit (docs/concepts/time.md)
        * @param [in] variation - variation name
        * @param [in] loadColumns - optional, do we need to load table columns information (for column names and types) or not
        * @return DAssignment object or NULL if no assignment is found or error
        */
        virtual Assignment* GetAssignmentShort(int run, const std::string& path, time_t time, const std::string& variation, bool loadColumns)=0;

        /** @brief GetAssignmentShort with the time limit in microseconds (CCDB 2.5)
        *
        * The SQLite and MySQL providers implement it and make GetAssignmentShort call it; this default, for a provider
        * written for 2.4 that implements only GetAssignmentShort, calls that with the whole second.
        *
        * @param [in] timeMicro - UTC microseconds since the epoch: the newest data created at or before that instant;
        *                         0 means no time limit. @see TimeUtils
        */
        virtual Assignment* GetAssignmentShortMicro(int run, const std::string& path, int64_t timeMicro, const std::string& variation, bool loadColumns);

        /** @brief Get the assignment that a tag gives (CCDB 2.5): the tag replaces variation and time
        *
        * The provider reads the tag's variation and snapshot time in one query and resolves the request
        * as GetAssignmentShortMicro does with that variation and that instant, to the microsecond: both
        * snapshotTime and assignments.created are UTC instants (docs/concepts/time.md).
        *
        * @param [in] run - run number
        * @param [in] path - object path
        * @param [in] tagName - tag name, without '@'
        * @param [in] loadColumns - do we need to load table columns information (for column names and types) or not
        * @return Assignment object or NULL if no assignment is found
        * @throw std::runtime_error if the tag name is invalid or there is no such tag
        */
        virtual Assignment* GetAssignmentShortByTag(int run, const std::string& path, const std::string& tagName, bool loadColumns)=0;

        /** @brief The variation and the snapshot time of a tag (CCDB 2.5)
        *
        * @param [in] tagName - tag name, without '@'
        * @param [out] variation - the tag's variation name
        * @param [out] snapshotMicro - the tag's time, UTC microseconds since the epoch
        * @return false when there is no such tag
        * @throw std::runtime_error if the name is invalid, or the provider has no tags (this default)
        */
        virtual bool GetTag(const std::string& tagName, std::string& variation, int64_t& snapshotMicro);

        /** @brief The assignment a request resolves to, with everything about it loaded (issue #94)
        *
        * Resolves as GetAssignmentShortMicro (the variation chain and the time limit included), then loads the
        * assignment's run range (GetRunRange: min, max, name), its variation (GetVariation: the one the data
        * came from, a parent when the requested variation has none), its comment, and its creation and
        * modification times (UTC seconds). The type table comes with its columns. The caller owns the object.
        *
        * @param [in] run - run number
        * @param [in] path - table path
        * @param [in] variation - variation name, "default" by default
        * @param [in] timeMicro - UTC microseconds since the epoch: the newest data created at or before that
        *                         instant; 0 (the default) means no time limit
        * @return Assignment object or NULL if no assignment is found
        */
        virtual Assignment* GetAssignmentFull(int run, const std::string& path, const std::string& variation="default", int64_t timeMicro=0);

        /** @brief GetAssignmentFull with the variation and time of a tag (CCDB 2.5)
        * @throw std::runtime_error if there is no such tag
        */
        virtual Assignment* GetAssignmentFullByTag(int run, const std::string& path, const std::string& tagName);





        //----------------------------------------------------------------------------------------
        //  E N D   O F   I N T E R F A C E
        //----------------------------------------------------------------------------------------

        /** @brief Connection string that was used on last successful connect.
         *
         * Connection string that was used on last successful connect.
         * If no any successfull connects were done string::empty will be returned
         *
         * @return  Last connection string or string::empty() if no successfull connection was done
         */
        virtual std::string GetConnectionString();


        /** @brief Gets directory by its full path
        *
        * @param   Full path of the directory
        * @return DDirectory object if directory exists, NULL otherwise
        */
        Directory* GetDirectory(const std::string& path);

        /** @brief return reference to root directory
         *
         * Root directory contains all other directories. It is not stored in any database
         *
         * @warning User should not delete this object
         *
         * @return   DDirectory object pointer
         */
        virtual Directory * const GetRootDirectory();


        void BuildDirectoryDependencies();  /// Builds directory relational structure.
        void UpdateDirectoriesIfNeeded();   /// Update directories structure if this is required


        //----------------------------------------------------------------------------------------
        //  C O N S T A N T   T Y P E   T A B L E
        //----------------------------------------------------------------------------------------


        /** @brief Gets ConstantsType information from the DB
         *
         * @param  [in] path absolute path of the type table
         * @return new object of ConstantsTypeTable
         */
        ConstantsTypeTable * GetConstantsTypeTable(const std::string& path, bool loadColumns);



        //----------------------------------------------------------------------------------------
        //  O T H E R   F U N C T I O N S
        //----------------------------------------------------------------------------------------

        /** @brief Validates name for constant type table or directory or column
         *
         * @param     string name
         * @return   bool
         */
        bool ValidateName(const std::string& name);

        //----------------------------------------------------------------------------------------
        //  T A G S   (CCDB 2.5)
        //----------------------------------------------------------------------------------------

        /** @brief Converts a UTC 'YYYY-MM-DD hh:mm:ss[.ffffff]' to unix time (timegm, not mktime)
         * @return unix time or -1 if the string can't be parsed */
        static time_t UtcDateTimeToUnixTime(const std::string& utcDateTime);

        /** @brief Throws if the tag name is not valid (@see PathUtils::IsValidTagName)
         *
         * Providers check the name themselves, since GetAssignmentShortByTag is public API
         * and is not only called with names that went through PathUtils::ParseRequest
         * @throw std::runtime_error if the name is empty or has symbols other than a-zA-Z0-9_
         */
        static void CheckTagName(const std::string& tagName);

        /** @brief Unix time of a tag's snapshotTime column
         * @throw std::runtime_error if the time can't be parsed */
        static time_t GetTagUnixTime(const std::string& tagName, const std::string& snapshotTime);

        /** @brief A tag's snapshotTime column as UTC microseconds since the epoch
         * @throw std::runtime_error if the time can't be parsed */
        static int64_t GetTagMicro(const std::string& tagName, const std::string& snapshotTime);


    protected:

        /** @brief Loads the run range, variation, comment and times of an assignment found by id (GetAssignmentFull)
        *
        * The SQLite and MySQL providers implement it; this default, for other providers, loads nothing and returns false.
        */
        virtual bool LoadAssignmentDetails(Assignment* assignment);

        std::vector<Directory *>  mDirectories;
        std::map<dbkey_t,Directory *> mDirectoriesById;
        std::map<std::string,Directory *>  mDirectoriesByFullPath;
        bool mDirsAreLoaded;                 //Directories are loaded from database
        Directory *mRootDir;                ///root directory. This directory contains all other directories. It is not stored in databases


        std::string mConnectionString;      ///Connection string that was used on last successfully connect.

        std::map<dbkey_t, Variation *> mVariationsById;
        std::map<std::string, Variation *> mVariationsByName;
    };
}
#endif // _DDataProvider_

