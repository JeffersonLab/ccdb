#include <stdio.h>
#include <stdlib.h>
#include <iostream>
#include <sstream>
#include <time.h>
#include <string.h>
#include <limits.h>

#include "CCDB/Globals.h"
#include "CCDB/Helpers/StringUtils.h"
#include "CCDB/Helpers/PathUtils.h"
#include "CCDB/Providers/MySQLDataProvider.h"
#include "CCDB/Model/ConstantsTypeTable.h"
#include "CCDB/Model/RunRange.h"

#ifdef __MACH__
#include <mach/clock.h>
#include <mach/mach.h>
#endif


static void Error(int errorCode, std::string funcName, std::string message) {
    /// TODO this needs to be replaced. This is a stub to replace old CCDB logging that was removed
    using namespace std;
    string errorStr = "Error: (" + to_string(errorCode) + ") in '" + funcName + "' : '" + message + "'";
    throw runtime_error(errorStr);
}


ccdb::MySQLDataProvider::MySQLDataProvider()
{
    mIsConnected = false;
    mMySQLHnd=nullptr;
    mResult=nullptr;
    mRootDir = new Directory();
    mDirsAreLoaded = false;
    mLastFullQuerry="";
    mLastShortQuerry="";
}


ccdb::MySQLDataProvider::~MySQLDataProvider(void)
{
    if(IsConnected())
    {
        Disconnect();
    }
}


void ccdb::MySQLDataProvider::Connect(const std::string& connectionString )
{
    //try to parse connection string
    auto connection = ParseConnectionString(connectionString);

    //try to connect
    Connect(connection);
    mConnectionString = connectionString;
}

void ccdb::MySQLDataProvider::Connect(MySQLConnectionInfo connection)
{
    //check if we are connected
    if(IsConnected())
    {
        Error(CCDB_ERROR_CONNECTION_ALREADY_OPENED, "MySQLDataProvider::Connect(MySQLConnectionInfo)", "Connection already opened");
    }

    //verbose...
    // TODO Logging?
    //    Log::Verbose("ccdb::MySQLDataProvider::Connect", StringUtils::Format("Connecting to database:\n UserName: %s \n Password: %i symbols \n HostName: %s Database: %s Port: %i",
    //                    connection.UserName.c_str(), connection.Password.length(), connection.HostName.c_str(), connection.Database.c_str(), connection.Port) );

    // init connection variable
    if(mMySQLHnd == nullptr) {
        mMySQLHnd = mysql_init(nullptr);
        if(mMySQLHnd == nullptr)
        {
            Error(CCDB_ERROR_CONNECTION_INITIALIZATION, "MySQLDataProvider::Connect(DMySQLConnectionInfo)", "mysql_init() returned nullptr, probably memory allocation problem");
        }
    }

    //Try to connect to server
    if(!mysql_real_connect (
        mMySQLHnd,                     //pointer to connection handler
        connection.HostName.c_str(),    //host to connect to
        connection.UserName.c_str(),    //user name
        connection.Password.c_str(),  //password
        connection.Database.c_str(),     //database to use
        connection.Port,                    //port
        nullptr,                   //socket (use default)
        0))                         //flags (none)
    {
        string errStr = ComposeMySQLError("mysql_real_connect()");
        Error(CCDB_ERROR_CONNECTION_EXTERNAL_ERROR,"bool MySQLDataProvider::Connect(MySQLConnectionInfo)",errStr.c_str());

        mMySQLHnd=nullptr;        //some compilers dont set nullptr after delete
    }
    mIsConnected = true;
}

ccdb::MySQLConnectionInfo ccdb::MySQLDataProvider::ParseConnectionString(std::string conStr)
{
    //Setting default connection
    MySQLConnectionInfo connection;
    connection.UserName.assign(CCDB_DEFAULT_MYSQL_USERNAME);
    connection.Password.assign(CCDB_DEFAULT_MYSQL_PASSWORD);
    connection.HostName.assign(CCDB_DEFAULT_MYSQL_URL);
    connection.Database.assign(CCDB_DEFAULT_MYSQL_DATABASE);
    connection.Port    = CCDB_DEFAULT_MYSQL_PORT;


    //first check for uri type
    int typePos = conStr.find("mysql://");
    if(typePos==string::npos)
    {
        throw std::runtime_error("MySQL connection string parse error! The string '" + conStr + "' should start with mysql://");
    }

    //ok we don't need mysql:// in the future. Moreover, it will mess up the separation logic
    conStr.erase(0,8);

    //then if there is '@' that separates login/password part of uri
    int atPos = conStr.find('@');
    if(atPos!=string::npos)
    {
        string logPassStr;

        //ok! we have it!
        //take it... but with caution
        if(atPos == conStr.length()-1)
        {
            //it is like 'login:pwd@' string
            logPassStr = conStr.substr(0, atPos);
            conStr=string("");
        }
        else if(atPos==0)
        {
            //it is like '@localhost' string
            conStr=conStr.substr(1);
            logPassStr = string("");
        }
        else
        {
            //a regular case
            logPassStr = conStr.substr(0,atPos);
            conStr=conStr.substr(atPos+1);
        }

        //is it only login or login&&password?
        int colonPos = logPassStr.find(':');
        if(colonPos!=string::npos)
        {
            connection.UserName = logPassStr.substr(0,colonPos);
            connection.Password = logPassStr.substr(colonPos+1);
        }
        else
        {
            connection.UserName = logPassStr;
        }
    }

    //ok, now we have only "address:port database" part of the string

    //1) deal with database;
    int whitePos=conStr.find('/');
    if(whitePos!=string::npos)
    {
        connection.Database = conStr.substr(whitePos+1);
        conStr.erase(whitePos);
    }

    //2) deal with port
    int colonPos = conStr.find(':');
    if(colonPos!=string::npos)
    {
        string portStr=conStr.substr(colonPos+1);
        conStr.erase(colonPos);

        connection.Port =atoi(portStr.c_str());
    }

    //3) everything that is last whould be address
    connection.HostName = conStr;

    return connection;
}


bool ccdb::MySQLDataProvider::IsConnected()
{
    return mIsConnected;
}


void ccdb::MySQLDataProvider::Disconnect()
{
    if(IsConnected())
    {
        FreeMySQLResult();    //it would free the result or do nothing

        mysql_close(mMySQLHnd);
        mMySQLHnd = nullptr;
        mIsConnected = false;
    }
}


void ccdb::MySQLDataProvider::LoadDirectories()
{
    //
    if(IsConnected())
    {
        if(!QuerySelect("SELECT `id`, `parentId`, `name`, `comment` FROM `directories`"))
        {
            throw std::runtime_error("ccdb::MySQLDataProvider::LoadDirectories() => Failed a query to select all directories ");
        }

        //clear diretory arrays
        mDirectories.clear();
        mDirectoriesById.clear();

        //clear root directory (delete all directory structure objects)
        mRootDir->DisposeSubdirectories();

        //Ok! We querryed our directories! Lets catch them!
        while(FetchRow())
        {
            auto dir = new Directory();
            dir->SetId(ReadIndex(0));                // `id`,
            dir->SetParentId(ReadInt(1));            // `parentId`,
            dir->SetName(ReadString(2));            // `name`,
            dir->SetComment(ReadString(3));            // `comment`

            mDirectories.push_back(dir);
            mDirectoriesById[dir->GetId()] = dir;
        }

        BuildDirectoryDependencies();
        mDirsAreLoaded=true;
    }
}


ccdb::ConstantsTypeTable * ccdb::MySQLDataProvider::GetConstantsTypeTable( const string& name, Directory *parentDir, bool loadColumns/*=false*/ )
{
    using namespace std;

    //check the directory is ok
    if(parentDir == nullptr || parentDir->GetId()<=0)
    {
        //error
        Error(CCDB_ERROR_NO_PARENT_DIRECTORY,"MySQLDataProvider::GetConstantsTypeTable", "Parent directory is null or have invalid ID");
        return nullptr;
    }

    //check connection
    if(!IsConnected())
    {
        //error !not connect
        Error(CCDB_ERROR_NOT_CONNECTED,"MySQLDataProvider::GetConstantsTypeTable", "Provider is not connected to MySQL.");
        return nullptr;
    }

    string query = "SELECT `id`, UNIX_TIMESTAMP(`created`) as `created`, UNIX_TIMESTAMP(`modified`) as `modified`, `name`, `directoryId`, `nRows`, `nColumns`, `comment` "
                   "FROM `typeTables` "
                   "WHERE `name` = '" + name + "' AND `directoryId` = '" + to_string(parentDir->GetId()) + "';";

    if(!QuerySelect(query))
    {
        //TODO: report error
        return nullptr;
    }


    //Ok! We querryed our directories! lets catch them!
    if(!FetchRow())
    {
        //TODO error not selected
        return nullptr;
    }

    //ok lets read the data...
    ConstantsTypeTable *result = new ConstantsTypeTable();
    result->SetId(ReadULong(0));
    result->SetCreatedTime(ReadUnixTime(1));
    result->SetModifiedTime(ReadUnixTime(2));
    result->SetName(ReadString(3));
    result->SetDirectoryId(ReadULong(4));
    result->SetNRows(ReadInt(5));
    result->SetNColumnsFromDB(ReadInt(6));
    result->SetComment(ReadString(7));

    result->SetDirectory(parentDir);

    //some validation of loaded record...
    if(result->GetName() == "")
    {
        //TODO error, name should be not null and not empty
        delete result;
        Error(CCDB_ERROR_TYPETABLE_HAS_NO_NAME,"MySQLDataProvider::GetConstantsTypeTable", "");
    }

    //Ok set a full path for this constant...
    result->SetFullPath(PathUtils::CombinePath(parentDir->GetFullPath(), result->GetName()));

    FreeMySQLResult();

    //load columns if needed
    if(loadColumns) LoadColumns(result);

    return result;
}


void ccdb::MySQLDataProvider::LoadColumns(ConstantsTypeTable* table)
{
    //check the directory is ok
    if(table->GetId()<=0)
    {
        Error(CCDB_ERROR_INVALID_ID,"MySQLDataProvider::LoadColumns", "Type table has wrong ID");
    }

    string query = "SELECT `id`, UNIX_TIMESTAMP(`created`) as `created`, UNIX_TIMESTAMP(`modified`) as `modified`, `name`, `columnType`, `comment` "
                   "FROM `columns` WHERE `typeId` = '" + to_string(table->GetId()) + "' ORDER BY `order`;";


    if(!QuerySelect(query))
    {
        throw std::runtime_error(std::string(__PRETTY_FUNCTION__ ) + " Error running SELECT query selecting columns");
    }

    //clear(); //we clear the consts. Considering that some one else should handle deletion

    //Ok! We querried our directories! lets catch them!
    while(FetchRow())
    {
        //ok lets read the data...
        ConstantsTypeColumn *result = new ConstantsTypeColumn();
        result->SetId(ReadULong(0));
        result->SetCreatedTime(ReadUnixTime(1));
        result->SetModifiedTime(ReadUnixTime(2));
        result->SetName(ReadString(3));
        result->SetType(ReadString(4));
        result->SetComment(ReadString(5));
        result->SetDBTypeTableId(table->GetId());
        table->AddColumn(result);
    }

    FreeMySQLResult();
}


ccdb::RunRange* ccdb::MySQLDataProvider::GetRunRange( int min, int max, const string& name /*= ""*/ )
{
    //build query
    string query = "SELECT `id`, UNIX_TIMESTAMP(`created`) as `created`, UNIX_TIMESTAMP(`modified`) as `modified`, `name`, `runMin`, `runMax`,  `comment` "
                   "FROM `runRanges` "
                   "WHERE `runMin`='" + to_string(min) + "' AND `runMax`='" + to_string(max) + "' AND `name`=\"" + name + "\"";

    //query this
    if(!QuerySelect(query))
    {
        //NO report error
        return nullptr;
    }

    //Ok! We queried our run range! Lets catch it!
    if(!FetchRow())
    {
        //nothing was selected
        return nullptr;
    }

    //ok lets read the data...
    RunRange *result = new RunRange();
    result->SetId(ReadULong(0));
    result->SetCreatedTime(ReadUnixTime(1));
    result->SetModifiedTime(ReadUnixTime(2));
    result->SetName(ReadString(3));
    result->SetMin(ReadInt(4));
    result->SetMax(ReadInt(5));
    result->SetComment(ReadString(6));

    if(mReturnedRowsNum>1)
    {
        //TODO warning not uniq row
        Error(CCDB_ERROR,"MySQLDataProvider::GetRunRange", "Run range with such min, max and name is not alone in the DB");
    }

    FreeMySQLResult();
    return result;
}


ccdb::RunRange* ccdb::MySQLDataProvider::GetRunRange( const string& name )
{

    //build query
    string query = "SELECT `id`, UNIX_TIMESTAMP(`created`) as `created`, UNIX_TIMESTAMP(`modified`) as `modified`, `name`, `runMin`, `runMax`,  `comment`"
        " FROM `runRanges` WHERE `name`=\"" + name + "\"";

    //query this
    if(!QuerySelect(query))
    {
        //NO report error
        return nullptr;
    }

    //Ok! We querried our run range! lets catch it!
    if(!FetchRow())
    {
        //nothing was selected
        return nullptr;
    }

    //ok lets read the data...
    RunRange *result = new RunRange();
    result->SetId(ReadULong(0));
    result->SetCreatedTime(ReadUnixTime(1));
    result->SetModifiedTime(ReadUnixTime(2));
    result->SetName(ReadString(3));
    result->SetMin(ReadInt(4));
    result->SetMax(ReadInt(5));
    result->SetComment(ReadString(6));

    if(mReturnedRowsNum>1)
    {
        //warning not uniq row
        Error(CCDB_ERROR,"MySQLDataProvider::GetRunRange", "Run range with such name is not alone in the DB");
    }

    FreeMySQLResult();
    return result;
}




ccdb::Variation* ccdb::MySQLDataProvider::GetVariation( const string& name )
{

    if(mLastVariation!=nullptr && mLastVariation->GetName()==name) return mLastVariation;

    return SelectVariation("`name`= \"" + name + "\"");
}

/** @brief Load variation by name
* 
* @param     const char * name
* @return   DVariation*
*/
ccdb::Variation* ccdb::MySQLDataProvider::GetVariationById(int id)
{
    if(mVariationsById.find(id) != mVariationsById.end()) return mVariationsById[id];

    return SelectVariation("`id`= " + StringUtils::IntToString(id) + "");
}

/**
* Get variation by database request
*/
ccdb::Variation* ccdb::MySQLDataProvider::SelectVariation(const string& whereClause)
{
    //TODO: Implement method
    string query = "SELECT `id`, `name`, `comment`, `parentId`"
        " FROM `variations` WHERE "+whereClause+";";

    //query this
    if(!QuerySelect(query))
    {
        //TODO report error
        return nullptr;
    }

    //Ok! We queried our run range! lets catch it! 
    if(!FetchRow())
    {
        //nothing was selected
        return nullptr;
    }

    //ok lets read the data...
    Variation *result = new Variation();
    result->SetId(ReadULong(0));
    result->SetName(ReadString(3));
    result->SetComment(ReadString(5));
    result->SetParentDbId(ReadULong(6));

    if(mReturnedRowsNum>1)
    {
        //TODO warning not uniq row
    }

    mVariationsById[result->GetId()] = result;
    mLastVariation = result;
    FreeMySQLResult();

    //Get parent recursively
    if(result->GetParentDbId()!=0)
    {
        result->SetParent(GetVariationById(result->GetParentDbId()));
    }

    return result;
}


//----------------------------------------------------------------------------------------
//    A S S I G N M E N T S
//----------------------------------------------------------------------------------------
ccdb::Assignment* ccdb::MySQLDataProvider::GetAssignmentShort(int run, const string& path, time_t time, const string& variationName, bool loadColumns /*=false*/)
{
    /** @brief Get specified by creation time version of Assignment with data blob only.
     *
     * The Time is a timestamp, data that is equal or earlier in time than that timestamp is returned
     *
     * @remarks this function is named so
     * @param [in] run - run number
     * @param [in] path - object path
     * @param [in] time - timestamp, data that is equal or earlier in time than that timestamp is returned
     * @param [in] variation - variation name
     * @return new DAssignment object or 
     */

    string thisFuncName("ccdb::MySQLDataProvider::GetAssignmentShort");

    if(!IsConnected()) {
        throw runtime_error(thisFuncName+" => Not connected to DB");
    }

    //Get directory. Directories should be cached. So this doesn't make a database request
    
    ConstantsTypeTable *table = ccdb::DataProvider::GetConstantsTypeTable(path, loadColumns);
    if(!table)
    {
        throw runtime_error(thisFuncName+" => Type table was not found: '"+path+"'");
    }

    //retrieve name of our constant table 
    string tableName = PathUtils::ExtractObjectname(path);

    //get variation
    Variation* variation = GetVariation(variationName);
    if(!variation)
    {
        throw runtime_error(thisFuncName+" => No variation '"+variationName+"' was found");
        return nullptr;
    }

    //run number to string
    string runStr = StringUtils::IntToString(run);

    //ok now we must build our mighty query...
    string query=
        "SELECT `assignments`.`id` AS `asId`, "
        "`constantSets`.`vault` AS `blob` "
        "FROM  `assignments` "
        "INNER JOIN `runRanges` ON `assignments`.`runRangeId`= `runRanges`.`id` "
        "INNER JOIN `constantSets` ON `assignments`.`constantSetId` = `constantSets`.`id` "
        "INNER JOIN `typeTables` ON `constantSets`.`constantTypeId` = `typeTables`.`id` "
        "WHERE  `runRanges`.`runMin` <= '"+runStr+"' "
        "AND `runRanges`.`runMax` >= '"+runStr+"' "
        "AND `assignments`.`variationId`= '"+StringUtils::IntToString(variation->GetId())+"' "
        "AND `constantSets`.`constantTypeId` ='"+StringUtils::IntToString(table->GetId())+"' ";
    
    //time in querY?
    if(time>0)
    {
        char timeBuf[32];
        sprintf(timeBuf,"%lu",time);
        query=query + "AND UNIX_TIMESTAMP(`assignments`.`created`) <= '"+string(timeBuf)+"' ";
    }

    //finish query 
    query = query + "ORDER BY `assignments`.`id` DESC LIMIT 1 ";

    //query this
    if(!QuerySelect(query))
    {
        return nullptr;
    }

    //If We have not found data for this variation, getting data for parent variation
    if(mReturnedRowsNum==0 && variation->GetParentDbId()!=0)
    {
        delete table;
        return GetAssignmentShort(run, path, time, variation->GetParent()->GetName(), loadColumns);
    }

    //Ok! We queried our run range! lets catch it!
    if(!FetchRow())
    {
        Error(CCDB_ERROR_NO_ASSIGMENT, "MySQLDataProvider::GetAssignmentShort(int, const string&, time_t, const string&)", "Error fetching assignment");
    }

    //ok lets read the data...
    Assignment *result = new Assignment();
    result->SetId( ReadIndex(0) );
    result->SetRawData( ReadString(1) );

    //additional fill
    result->SetRequestedRun(run);
    result->SetVariationId(variation->GetId());

    //type table
    result->SetTypeTable(table);


    if(mReturnedRowsNum>1)
    {
        //TODO warning not uniq row
    }

    FreeMySQLResult();
    return result;

}


ccdb::Assignment* ccdb::MySQLDataProvider::FetchAssignment(ConstantsTypeTable* table)
{
    Assignment * assignment = new Assignment(); //it is our victim

    FetchAssignment(assignment, table);

    //take it!
    return assignment;
}


void ccdb::MySQLDataProvider::FetchAssignment(Assignment* assignment, ConstantsTypeTable* table)
{
    //ok now we must fetch our mighty query...
    assignment->SetId(ReadIndex(0));                /*00  " `assignments`.`id` AS `asId`,    "*/
    assignment->SetCreatedTime(ReadUnixTime(1));    /*01  " UNIX_TIMESTAMP(`assignments`.`created`) as `asCreated`,"*/
    assignment->SetModifiedTime(ReadUnixTime(2));    /*02  " UNIX_TIMESTAMP(`assignments`.`modified`) as `asModified`,    "*/
    assignment->SetComment(ReadString(3));            /*03  " `assignments`.`comment) as `asComment`,    "                     */
    assignment->SetDataVaultId(ReadIndex(4));        /*04  " `constantSets`.`id` AS `constId`, "                             */
    assignment->SetRawData(ReadString(5));            /*05  " `constantSets`.`vault` AS `blob`, "                             */

    RunRange * runRange = new RunRange();
    runRange->SetId(ReadIndex(6));                    /*06  " `runRanges`.`id`   AS `rrId`, "    */
    runRange->SetCreatedTime(ReadUnixTime(7));        /*07  " UNIX_TIMESTAMP(`runRanges`.`created`) as `rrCreated`,"*/
    runRange->SetModifiedTime(ReadUnixTime(8));        /*08  " UNIX_TIMESTAMP(`runRanges`.`modified`) as `rrModified`,    "*/
    runRange->SetName(ReadString(9));                /*09  " `runRanges`.`name`   AS `rrName`, "        */
    runRange->SetMin(ReadInt(10));                    /*10  " `runRanges`.`runMin`   AS `rrMin`, "    */
    runRange->SetMax(ReadInt(11));                    /*11  " `runRanges`.`runMax`   AS `runMax`, "    */
    runRange->SetComment(ReadString(12));            /*12  " `runRanges`.`comment` as `rrComment`, "    */

    Variation * variation = new Variation();
    variation->SetId(ReadIndex(13));                /*13  " `variations`.`id`  AS `varId`, */
    //variation->SetCreatedTime(ReadUnixTime(14));    /*14  " UNIX_TIMESTAMP(`variations`.`created`) as `varCreated`,"     */
    //variation->SetModifiedTime(ReadUnixTime(15));    /*15  " UNIX_TIMESTAMP(`variations`.`modified`) as `varModified`,     */
    variation->SetName(ReadString(16));            /*16  " `variations`.`name` AS `varName` "*/
    variation->SetComment(StringUtils::Decode(ReadString(12)));        /*17  " `variations`.`comment`  AS `varComment` "*/

    //compose objects
    assignment->SetRunRange(runRange);
    assignment->SetVariation(variation);
    assignment->SetTypeTable(table);
}



bool ccdb::MySQLDataProvider::IsNullOrUnreadable( int fieldNum )
{
    // Checks if there is a value with this fieldNum index (reports error in such case)
    // and if it is not null (just returns false in this case)

    if(mReturnedFieldsNum<=fieldNum)
    {
        //Add error, we have less fields than fieldNum
        Error(CCDB_WARNING_DBRESULT_FIELD_INDEX,"MySQLDataProvider::IsNullOrUnreadable", "we have less fields than fieldNum");
        return true;
    }

    if(mRow[fieldNum]==nullptr)
    {
        return true;
    }
    //fine!
    return false;
}

int ccdb::MySQLDataProvider::ReadInt( int fieldNum )
{    
    if(IsNullOrUnreadable(fieldNum)) return 0;

    return atoi(mRow[fieldNum]); //ugly isn't it?
}

unsigned int ccdb::MySQLDataProvider::ReadUInt( int fieldNum )
{    
    if(IsNullOrUnreadable(fieldNum)) return 0;

    return static_cast<unsigned int>(atoi(mRow[fieldNum])); //ugly isn't it?
}

long ccdb::MySQLDataProvider::ReadLong( int fieldNum )
{
    if(IsNullOrUnreadable(fieldNum)) return 0;

    return atol(mRow[fieldNum]); //ugly isn't it?
}

unsigned long ccdb::MySQLDataProvider::ReadULong( int fieldNum )
{
    if(IsNullOrUnreadable(fieldNum)) return 0;

    return static_cast<unsigned long>(atol(mRow[fieldNum])); //ugly isn't it?
}

dbkey_t ccdb::MySQLDataProvider::ReadIndex( int fieldNum )
{
    if(IsNullOrUnreadable(fieldNum)) return 0;

    return static_cast<dbkey_t>(atol(mRow[fieldNum])); //ugly isn't it?
}

bool ccdb::MySQLDataProvider::ReadBool( int fieldNum )
{
    if(IsNullOrUnreadable(fieldNum)) return false;

    return static_cast<bool>(atoi(mRow[fieldNum])!=0); //ugly isn't it?

}

double ccdb::MySQLDataProvider::ReadDouble( int fieldNum )
{
    if(IsNullOrUnreadable(fieldNum)) return 0;

    return atof(mRow[fieldNum]); //ugly isn't it?
}

std::string ccdb::MySQLDataProvider::ReadString( int fieldNum )
{
    if(IsNullOrUnreadable(fieldNum)) return string("");
    return string(mRow[fieldNum]);
}


time_t ccdb::MySQLDataProvider::ReadUnixTime( int fieldNum )
{    
    return static_cast<time_t>(ReadULong(fieldNum));
}

#pragma endregion MySQL_Field_Operations


#pragma region Queries

bool ccdb::MySQLDataProvider::QuerySelect(const char* query)
{
    if(!IsConnected()) {
        throw std::runtime_error(std::string(__PRETTY_FUNCTION__ ) + " : Error. No connection to DB");
    }

    //do we have some results we need to free?
    if(mResult!=nullptr)
    {
        FreeMySQLResult();
    }

    //query
    if(mysql_query(mMySQLHnd, query))
    {
        string errStr = ComposeMySQLError("mysql_query()"); errStr.append("\n Query: "); errStr.append(query);
        Error(CCDB_ERROR_QUERY_SELECT,"ccdb::MySQLDataProvider::QuerySelect()",errStr.c_str());
        return false;
    }

    //get results
    mResult = mysql_store_result(mMySQLHnd);

    if(!mResult)
    {
        string errStr = ComposeMySQLError("mysql_query()"); errStr.append("\n Query: "); errStr.append(query);
        Error(CCDB_ERROR_QUERY_SELECT,"ccdb::MySQLDataProvider::QuerySelect()",errStr.c_str());

        mReturnedRowsNum = 0;
        mReturnedFieldsNum = 0;
        return false;
    }

    //a rows number?
    mReturnedRowsNum = mysql_num_rows(mResult);

    //a fields number?
    mReturnedFieldsNum = mysql_num_fields(mResult);

    return true;
}

bool ccdb::MySQLDataProvider::QuerySelect(const string& query )
{
    return QuerySelect(query.c_str());
}



#pragma endregion


#pragma region Fetch_free_and_other_MySQL_operations

bool ccdb::MySQLDataProvider::FetchRow()
{    
    
    if((mRow = mysql_fetch_row(mResult))) return true;
    return false;
}

void ccdb::MySQLDataProvider::FreeMySQLResult()
{
    mysql_free_result(mResult);
    mResult = nullptr;
}

std::string ccdb::MySQLDataProvider::ComposeMySQLError(std::string mySqlFunctionName)
{
    string mysqlErr = mySqlFunctionName + " failed:\n"
                      "mysql_errno " + std::to_string(mysql_errno(mMySQLHnd)) +
                      " (" + mysql_error(mMySQLHnd) + ")\n";
    return mysqlErr;
}



