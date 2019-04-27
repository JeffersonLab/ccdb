#ifndef _SQLiteDataProvider_
#define _SQLiteDataProvider_


#include <sqlite3.h>
#include <vector>
#include <map>

#include "CCDB/Providers/DataProvider.h"
#include "CCDB/Model/ConstantsTypeTable.h"
#include "CCDB/Helpers/SQLite.h"

///We making this define to be sure if we switch to other library nothing will change
//#define SQLITE_ULONG my_ulonglong

namespace ccdb
{

class SQLiteDataProvider: public DataProvider
{
	
public:
	SQLiteDataProvider();
	~SQLiteDataProvider() override;

    //----------------------------------------------------------------------------------------
    //  I M P L E M E N T   I N T E R F A C E
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
    void Connect(const std::string &connectionString) override;

    /**
     * @brief closes connection to data
     */
    void Disconnect() override;

    /**
     * @brief indicates ether the connection is open or not
     *
     * @return true if  connection is open
     */
    bool IsConnected() override;

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
     * @param  [in] name name of ConstantsTypeTable
     * @param  [in] parentDir directory that contains type table
     * @return new object of ConstantsTypeTable
     */
    ConstantsTypeTable * GetConstantsTypeTable(const string& name, Directory *parentDir, bool loadColumns) override;


    /** @brief gets all type tables from DB
     * @return bool
     */
    std::vector<ConstantsTypeTable *> GetAllConstantsTypeTables(bool loadColumns) override;



    /** @brief Get variation by name*/
    Variation* GetVariation(const string& name) override;

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
    Assignment* GetAssignmentShort(int run, const string& path, time_t time, const string& variation, bool loadColumns) override;


    //----------------------------------------------------------------------------------------
    //  E N D   I M P L E M E N T   I N T E R F A C E
    //----------------------------------------------------------------------------------------

	private:

    /** @brief Loads columns for "table" type table
	 *
	 * @param [in out] table
	 * @return true if no errors (even if no columns loaded)
	 */
    void LoadColumns(ConstantsTypeTable* table);

    /** @brief Load variation by DB id
	 * 
	 * @param     const char * name
	 * @return   DVariation*
	 */
    Variation* GetVariationById(dbkey_t id);

     /** @brief Executes statement and create Variation object. 
	 * 
     * mStatement should be prepared when calling the function. 
     * The assumed data order in prepared statement is:
     * `id`, `parentId`, `name` 
	 * @return   DVariation*
	 */
    Variation *SelectVariation(SQLiteStatement& statement);

private:

	//Assignment* FetchAssignment(ConstantsTypeTable *table);
	//virtual void FetchAssignment(Assignment* assignment, ConstantsTypeTable *table);


	sqlite3 *		mDatabase;			//Handler to sqlite object

	bool mIsConnected;					//indicates connection to db

};
}

#endif //_SQLiteDataProvider_
