#include <iostream>
#include <sstream>

#include <stdlib.h>
#include <time.h>
#include <string.h>
#include <limits.h>

#include <fmt/format.h>

#include "CCDB/Globals.h"
#include "CCDB/Helpers/StringUtils.h"
#include "CCDB/Helpers/PathUtils.h"
#include "CCDB/Helpers/SQLite.h"
#include "CCDB/Providers/SQLiteDataProvider.h"
#include "CCDB/Model/ConstantsTypeTable.h"
#include "CCDB/Model/RunRange.h"


using namespace ccdb;

ccdb::SQLiteDataProvider::SQLiteDataProvider()
{
	mIsConnected = false;
	mDatabase=nullptr;
	mRootDir = new Directory();
	mDirsAreLoaded = false;
}


ccdb::SQLiteDataProvider::~SQLiteDataProvider()
{
	if(IsConnected()) {
		Disconnect();
	}
}


void ccdb::SQLiteDataProvider::Connect(const std::string& connectionString )
{
	//check for uri type
	std::string thisFuncName = "ccdb::SQLiteDataProvider::Connect";
	int typePos = connectionString.find("sqlite://");
	if(typePos==string::npos)
	{
	    throw std::runtime_error(thisFuncName + "=>Error parse SQLite string. The string is not started with sqlite://");
	}
	
	//check if we are connected
	if(IsConnected())
	{
	    if(connectionString != mConnectionString) {
            throw std::runtime_error(thisFuncName + "Connection already opened with different connection string");
	    }

	    // We already connected with this connection string
		return;
	}

    mConnectionString = connectionString;   // save connection string as "the last one" before changing...

    std::string filePath (connectionString);
    filePath.erase(0,9);            // ok we dont need sqlite:// in the beginning.

	//Try to open sqlite database
	int result = sqlite3_open_v2(filePath.c_str(), &mDatabase, SQLITE_OPEN_READONLY|SQLITE_OPEN_FULLMUTEX|SQLITE_OPEN_SHAREDCACHE, nullptr); // NOLINT(hicpp-signed-bitwise)

	if (result != SQLITE_OK) 
	{
		string errStr(sqlite3_errmsg(mDatabase));
		mDatabase=nullptr;		//some compilers dont set NULL after delete
		mConnectionString = "";
        throw std::runtime_error(thisFuncName + "=> SQLite open error:" + errStr);
	}

    sqlite3_exec(mDatabase, "PRAGMA journal_mode = OFF;", nullptr, nullptr, nullptr);
	
	mIsConnected = true;
}


bool ccdb::SQLiteDataProvider::IsConnected()
{
	return mIsConnected;
}


void ccdb::SQLiteDataProvider::Disconnect()
{
	if(IsConnected())
	{
		sqlite3_close(mDatabase);
		mDatabase = nullptr;
		mIsConnected = false;
	}
}


void ccdb::SQLiteDataProvider::LoadDirectories()
{

    string thisFunc("SQliteDataProvider::LoadDirectories");
    //
    if (!IsConnected()) {
        throw std::runtime_error(thisFunc + " => Not connected to SQLite database ");
    }
    // prepare the SQL statement from the command line

    SQLiteStatement query(mDatabase, "SELECT `id`, `name`, `parentId`, `comment` FROM `directories`");


    //clear diretory arrays
    mDirectories.clear();
    mDirectoriesById.clear();

    Directory *dir = nullptr;

    query.Execute([&dir, &query, this](uint64_t rowIndex) {
        dir = new Directory();
        dir->SetId(query.ReadUInt64(0));              // `id`,
        dir->SetName(query.ReadString(1));            // `name`,
        dir->SetParentId(query.ReadInt32(2));         // `parentId`,
        dir->SetComment(query.ReadString(3));         // `comment`

        mDirectories.push_back(dir);
        mDirectoriesById[dir->GetId()] = dir;
    });

    //clear root directory (delete all directory structure objects)
    mRootDir->DisposeSubdirectories();

    BuildDirectoryDependencies();

    mDirsAreLoaded = true;

}


ConstantsTypeTable * ccdb::SQLiteDataProvider::GetConstantsTypeTable( const string& name, Directory *parentDir,bool loadColumns/*=false*/ )
{	
	std::string thisFunc("ccdb::SQLiteDataProvider::GetConstantsTypeTable");

	if(!IsConnected()) { throw std::runtime_error(thisFunc + " => SQLiteDataProvider is not connected to DB");}

	UpdateDirectoriesIfNeeded();

	//check the directory is ok
	if(parentDir == nullptr || (parentDir->GetFullPath()!=string("/") && parentDir->GetId()<=0)) {
        throw std::runtime_error(thisFunc + " => Parent directory is null or have invalid ID");
	}

	SQLiteStatement query(mDatabase);
	query.Prepare("SELECT `id`, `name`, `directoryId`, `nRows`, `nColumns`, `comment` "
                  "FROM `typeTables` WHERE `name` = ?1 AND `directoryId` = ?2");
	query.BindString(1, name);
	query.BindInt64(2, parentDir->GetId());

	// execute the statement
	ConstantsTypeTable *table = nullptr;
    query.Execute([&table, &query, parentDir, this](uint64_t rowIndex) {
        //ok lets read the data...
        table = new ConstantsTypeTable();
        table->SetId(query.ReadUInt64(0));
        table->SetName(query.ReadString(1));
        table->SetDirectoryId(query.ReadUInt64(2));
        table->SetNRows(query.ReadUInt32(3));
        table->SetNColumnsFromDB(query.ReadUInt32(4));
        table->SetComment(query.ReadString(5));
        table->SetDirectory(parentDir);

        //Ok set a full path for this constant...
        table->SetFullPath(PathUtils::CombinePath(parentDir->GetFullPath(), table->GetName()));
    });

	//load columns if needed
	if(loadColumns && table) LoadColumns(table);

	//return result;
	return table;
}


std::vector<ConstantsTypeTable *> ccdb::SQLiteDataProvider::GetAllConstantsTypeTables(bool loadColumns)
{
    //In this case we will need mDirectoriesById
    //maybe we need to update our directories?
    UpdateDirectoriesIfNeeded();

	//combine query
    SQLiteStatement query(mDatabase);
    query.Prepare("SELECT `id`, `name`, `directoryId`, `nRows`, `nColumns`, `comment` FROM typeTables");

    // execute the statement
    std::vector<ConstantsTypeTable *> tables;
    ConstantsTypeTable *table = nullptr;
    query.Execute([&table, &query, &tables, this](uint64_t rowIndex) {
        //ok lets read the data...
        table = new ConstantsTypeTable();
        table->SetId(query.ReadUInt64(0));
        table->SetName(query.ReadString(1));
        table->SetDirectoryId(query.ReadUInt64(2));
        table->SetNRows(query.ReadUInt32(3));
        table->SetNColumnsFromDB(query.ReadUInt32(4));
        table->SetComment(query.ReadString(5));
        table->SetDirectory(mDirectoriesById[table->GetDirectoryId()]);
        tables.push_back(table);
    });


    //Load COLUMNS if needed...
	if(loadColumns)
    {
        for (auto & tableForColumns : tables)
        {
            LoadColumns(tableForColumns);
        }
    }
 	return tables;
}


void ccdb::SQLiteDataProvider::LoadColumns( ConstantsTypeTable* table )
{
    SQLiteStatement query(mDatabase);
    query.Prepare("SELECT `id`, `name`, `columnType` FROM `columns` WHERE `typeId` = ?1 ORDER BY `order`");
	query.BindInt32(1, table->GetId());

    // execute the statement
    ConstantsTypeColumn *column;
    query.Execute([&table, &query, &column, this](uint64_t rowIndex) {

        column = new ConstantsTypeColumn();
        column->SetId(query.ReadUInt64(0));
        column->SetName(query.ReadString(1));
        column->SetType(query.ReadString(2));
        column->SetDBTypeTableId(table->GetId());
        table->AddColumn(column);
    });
}


Variation* ccdb::SQLiteDataProvider::GetVariation( const string& name )
{
    //check that maybe we have this variation id by the last request?
    if(mVariationsByName.find(name) != mVariationsByName.end()) return mVariationsByName[name];
    SQLiteStatement query(mDatabase);
    query.Prepare("SELECT `id`, `parentId`, `name` FROM `variations` WHERE `name`= ?1");
    query.BindString(1, name);
    return SelectVariation(query);
}


Variation* ccdb::SQLiteDataProvider::GetVariationById( dbkey_t id )
{
    //check that maybe we have this variation id by the last request?
    if(mVariationsById.find(id) != mVariationsById.end()) return mVariationsById[id];
    SQLiteStatement query(mDatabase);
    query.Prepare("SELECT `id`, `parentId`, `name` FROM `variations` WHERE `id`= ?1");
    query.BindInt64(1, id);
    return SelectVariation(query);
}


Variation* ccdb::SQLiteDataProvider::SelectVariation(SQLiteStatement& query)
{
    // execute the statement
    Variation *var = nullptr;
    query.Execute([&var, &query, this](uint64_t rowIndex) {
        var = new Variation();
        var->SetId(query.ReadUInt64(0));
        var->SetParentDbId(query.ReadUInt64(1));
        var->SetName(query.ReadString(2));
    });

    if(var) {
        //add to cache
        mVariationsById[var->GetId()] = var;
        mVariationsByName[var->GetName()] = var;

        //recursive call to get variation parent
        if(var->GetParentDbId() > 0) {
            var->SetParent(GetVariationById(var->GetParentDbId()));
        }
    }
    
	return var;
}


Assignment* ccdb::SQLiteDataProvider::GetAssignmentShort(int run, const string& path, time_t time, const string& variationName, bool loadColumns /*=false*/)
{
    //Get type table
    ConstantsTypeTable *table = DataProvider::GetConstantsTypeTable(path, loadColumns);
    if(!table) {
        string error("SQLiteDataProvider::GetAssignmentShort => Type table was not found: '"+path+"'" );
        throw std::runtime_error(error);
    }
    
    //get variation
    Variation* variation = GetVariation(variationName);
    if(!variation) {
        string error("SQLiteDataProvider::GetAssignmentShort => No variation '"+variationName+"' was found");
        throw std::runtime_error(error);
    }

	////ok now we must build our mighty query...
    SQLiteStatement query(mDatabase);
    query.Prepare(
        "SELECT `assignments`.`id` AS `asId`, "
        "`constantSets`.`vault` AS `blob` "
        "FROM  `assignments` "
        "INNER JOIN `runRanges` ON `assignments`.`runRangeId`= `runRanges`.`id` "
        "INNER JOIN `constantSets` ON `assignments`.`constantSetId` = `constantSets`.`id` "
        "INNER JOIN `typeTables` ON `constantSets`.`constantTypeId` = `typeTables`.`id` "
        "WHERE  `runRanges`.`runMin` <= ?1 "
        "AND `runRanges`.`runMax` >= ?1 "
        "AND `assignments`.`variationId`= ?2 "
        "AND  `constantSets`.`constantTypeId` =?3 " + 
        ((time>0)? string("AND  `assignments`.`created` <= datetime(?4, 'unixepoch', 'localtime') ") : string()) +
        "ORDER BY `assignments`.`id` DESC "
        "LIMIT 1 ");
	
    query.BindInt32(1, run);
	query.BindInt32(2, variation->GetId());	/*`variationId`*/
	query.BindInt32(3, table->GetId());	    /*``typeTables`.`directoryId``*/
    
    if(time>0) {
        query.BindInt64(4, time);	/*` `assignments`.`created``*/
    }

	// execute the statement
	Assignment *assignment = nullptr;
    auto selectedRows = query.Execute([&assignment, &query, run](uint64_t rowIndex) {
        assignment = new Assignment();
        assignment->SetId( query.ReadUInt64(0) );
        assignment->SetRawData(query.ReadString(1));
        assignment->SetRequestedRun(run);
    });


    //If We have not found data for this variation, getting data for parent variation
    if((assignment == nullptr && selectedRows==0) && variation->GetParentDbId()!=0)
    {
        return GetAssignmentShort(run, path, time, variation->GetParent()->GetName(), loadColumns);
    }
    
	if(assignment != nullptr)
	{
        assignment->SetTypeTable(table);
        assignment->SetVariation(variation);
	}

	return assignment;
}