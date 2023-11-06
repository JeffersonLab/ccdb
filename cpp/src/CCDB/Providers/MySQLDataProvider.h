#ifndef _MySQLDataProvider_
#define _MySQLDataProvider_

#ifdef WIN32
#include <winsock.h>
#endif
#include <mysql.h>
#include <vector>
#include <map>

#include "CCDB/Providers/DataProvider.h"
#include "CCDB/Providers/MySQLConnectionInfo.h"
#include "CCDB/Model/ConstantsTypeTable.h"

#define CCDB_DEFAULT_MYSQL_USERNAME  "ccdbuser"
#define CCDB_DEFAULT_MYSQL_PASSWORD  ""
#define CCDB_DEFAULT_MYSQL_URL 		 "localhost"
#define CCDB_DEFAULT_MYSQL_PORT 	 3306
#define CCDB_DEFAULT_MYSQL_DATABASE	 "ccdb"

///We making this define to be sure if we switch to other library nothing will change
#define MYSQL_ULONG my_ulonglong

namespace ccdb
{

    class MySQLDataProvider: public DataProvider
    {

    public:
        MySQLDataProvider();
        virtual ~MySQLDataProvider();


        //----------------------------------------------------------------------------------------
        //	C O N N E C T I O N
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
        void Connect(const std::string& connectionString) override;

        /**
         * @brief Connects to database using DMySQLConnectionInfo
         *
         * @param connection
         * @return true if connected
         */
        virtual void Connect(MySQLConnectionInfo connection);

        /**
         * @brief indicates ether the connection is open or not
         *
         * @return true if  connection is open
         */
        virtual bool IsConnected();

        /**
         * @brief closes connection to data
         */
        virtual void Disconnect();

        /** @brief Parse Connection String
         *
         * @param   [in]  conStr
         * @param   [out] DMySQLConnectionInfo & connection
         * @return   bool
         */
        static MySQLConnectionInfo ParseConnectionString(std::string conStr);


        //----------------------------------------------------------------------------------------
        //	D I R E C T O R Y   M A N G E M E N T
        //----------------------------------------------------------------------------------------



        /** @brief Reads all directories from DB
         *
         * Explicitly forces to load directories from DB and build directory structure
         * (!) At this implementation all existing directories references will be deleted,
         * thus  references to them will become broken
         * @return   bool
         */
        void LoadDirectories() override;



        /** @brief Gets ConstantsType information from the DB
         *
         * @param  [in] name nfme of ConstantsTypeTable
         * @param  [in] parentDir directory that contains type table
         * @return new object of ConstantsTypeTable
         */
        ConstantsTypeTable * GetConstantsTypeTable(const string& name, Directory *parentDir, bool loadColumns=false) override;


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
        std::vector<ConstantsTypeTable *> GetAllConstantsTypeTables(bool loadColumns = false) override;

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
         * @return bool
         */
        virtual bool SearchConstantsTypeTables(vector<ConstantsTypeTable *>& typeTables, const string& pattern, const string& parentPath = "", bool loadColumns=false, int take=0, int startWith=0 );

        /**
         * @brief This function counts number of type tables for a given directory
         * @param [in] directory to look tables in
         * @return number of tables to return
         */
        virtual int CountConstantsTypeTables(Directory *dir);


        /** @brief Loads columns for "table" type table
         *
         * @param [in out] table
         * @return true if no errors (even if no columns loaded)
         */
        virtual void LoadColumns(ConstantsTypeTable* table);

        #pragma endregion Constant type table

        //----------------------------------------------------------------------------------------
        //	R U N   R A N G E S
        //----------------------------------------------------------------------------------------
        #pragma region Run ranges

        /** @brief GetRun Range from db
         *
         * @param     int min
         * @param     int max
         * @param     const char * name
         * @return   DRunRange* return NULL if not found or failed
         */
        virtual RunRange* GetRunRange(int min, int max, const string& name = "");

        /** @brief GetRun Range from db
         *
         * @param     int min
         * @param     int max
         * @param     const char * name
         * @return   DRunRange* return NULL if not found or failed
         */
        virtual RunRange* GetRunRange(const string& name);

        /**
         * @brief Searches all run ranges associated with this type table
         *
         * @param [out] resultRunRanges result run ranges
         * @param [in]  table		table to search run ranges in
         * @param [in]  variation	variation to search, if not set all variations will be selected
         * @param [in]  take			how many records to take
         * @param [in]  startWith	start record to take
         * @return
         */
        virtual bool GetRunRanges(vector<RunRange *>& resultRunRanges, ConstantsTypeTable *table, const string& variation="", int take=0, int startWith=0 );



        #pragma endregion Run ranges

        //----------------------------------------------------------------------------------------
        //	V A R I A T I O N
        //----------------------------------------------------------------------------------------
        #pragma region Variation

        /** @brief Load variation by name
         *
         * @param     const char * name
         * @return   DVariation*
         */
        virtual Variation* GetVariation(const string& name);


    private:
        /** @brief Load variation by name
        *
        * @param     const char * name
        * @return   DVariation*
        */
        virtual Variation* GetVariationById(int id);

        /**
         * Get variation by database request
         */
        virtual Variation* SelectVariation(const string& query);

        #pragma endregion Variation

        //----------------------------------------------------------------------------------------
        //	A S S I G N M E N T S
        //----------------------------------------------------------------------------------------
    public:
        #pragma region Assignments

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
        virtual Assignment* GetAssignmentShort(int run, const string& path, const string& variation="default", bool loadColumns=false);


         /** @brief Get specified by creation time version of Assignment with data blob only.
         *
         * The Time is a timestamp, data that is equal or earlier in time than that timestamp is returned
         *
         * @remarks this function is named so
         * @param [in] run - run number
         * @param [in] path - object path
         * @param [in] time - timestamp, data that is equal or earlier in time than that timestamp is returned
         * @param [in] variation - variation name
         * @param [in] loadColumns - optional, do we need to load table columns information (for column names and types) or not
         * @return new DAssignment object or
         */
        virtual Assignment* GetAssignmentShort(int run, const string& path, time_t time, const string& variation="default", bool loadColumns=false);



    protected:




        virtual bool QuerySelect(const char* query);	///Do "select" queries
        virtual bool QuerySelect(const string& query);	///Do "select" queries
        virtual bool QueryCustom(const string& query);	///Do any custom queries queries

        virtual void FreeMySQLResult();	///Frees my sql result manually

        /** @brief gets last error and description and composes it as a string
         * @return string with composed error
         */
        std::string ComposeMySQLError(std::string mySqlFunctionName="");

        /** @brief Fetches next Row
         *
         * @return true if row was read, false if no more rows
         */
        bool FetchRow();

        //read of row fields
        bool IsNullOrUnreadable(int fieldNum);		///Check if the field is NULL or is unreadable. If it is Unreadable
        int				ReadInt(int fieldNum);		///Reads int	from the last query row
        dbkey_t			ReadIndex(int fieldNum);	///Reads dbkey_t from the last query row
        unsigned int	ReadUInt(int fieldNum);		///Reads unsigned int from the last query row
        long			ReadLong(int fieldNum);		///Reads long from the last query row
        unsigned long	ReadULong(int fieldNum);	///Reads unsigned long from the last query row
        bool			ReadBool(int fieldNum);		///Reads bool from the last query row
        double			ReadDouble(int fieldNum);	///Reads double from the last query row
        string			ReadString(int fieldNum);	///Reads string from the last query row
        time_t			ReadUnixTime(int fieldNum); ///Reads string from the last query row

    private:


        MYSQL *mMySQLHnd;			//Handler to mysql object
        bool mIsStoredObjectOwner;
        Assignment* FetchAssignment(ConstantsTypeTable *table);
        virtual void FetchAssignment(Assignment* assignment, ConstantsTypeTable *table);


        bool mHaveUnfreeResults; 			//indicates that we have some unfree results from mysql, that must be freed
        MYSQL_RES *mResult;					//result from last queue
        MYSQL_ROW mRow;						//last fetched row
        MYSQL_ULONG mReturnedRowsNum;		//number of returned rows from last SELECT query
        MYSQL_ULONG mReturnedFieldsNum;		//number of returned fields from last SELECT query
        MYSQL_ULONG mReturnedAffectedRows;	//number of affected rows from last INSERT, DELETE, UPDATE queries
        MYSQL_ULONG mLastInsertedId;		//number of last id
        bool mIsConnected;					//indicates connection to db
        static bool mMySqlIsInitialized;	//flag that mysql is initialized

        string mLastFullQuerry;   //full text of last full get assignment query

        string mLastShortQuerry;  //full text of last short assignment query

        //VARIATIONs WORK
        Variation* mLastVariation;                     ///Last requested variation ID. Used for caching



    };
}

#endif //_MySQLDataProvider_
