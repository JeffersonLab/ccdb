#ifndef _DDataProvider_
#define _DDataProvider_

#include <string>
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
        * @param [in] time - timestamp, data that is equal or earlier in time than that timestamp is returned
        * @param [in] variation - variation name
        * @param [in] loadColumns - optional, do we need to load table columns information (for column names and types) or not
        * @return DAssignment object or NULL if no assignment is found or error
        */
        virtual Assignment* GetAssignmentShort(int run, const std::string& path, time_t time, const std::string& variation, bool loadColumns)=0;




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


    protected:

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

