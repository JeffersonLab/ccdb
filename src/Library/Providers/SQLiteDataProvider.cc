

#include <stdlib.h>
#include <iostream>
#include <sstream>
#include <time.h>
#include <string.h>
#include <limits.h>

#include "CCDB/Globals.h"
#include "CCDB/Log.h"
#include "CCDB/Helpers/StringUtils.h"
#include "CCDB/Helpers/PathUtils.h"
#include "CCDB/Providers/SQLiteDataProvider.h"
#include "CCDB/Model/ConstantsTypeTable.h"
#include "CCDB/Model/RunRange.h"


using namespace ccdb;

#pragma region constructors

ccdb::SQLiteDataProvider::SQLiteDataProvider(void)
{
	mIsConnected = false;
	mDatabase=NULL;
	mStatement=NULL;
    mLastVariation = NULL;
	mRootDir = new Directory(this, this);
	mDirsAreLoaded = false;
}


ccdb::SQLiteDataProvider::~SQLiteDataProvider(void)
{
	if(IsConnected())
	{
		Disconnect();
	}
}
#pragma endregion constructors

#pragma region Connection

bool ccdb::SQLiteDataProvider::Connect( std::string connectionString )
{
	ClearErrors(); //Clear error in function that can produce new ones
		
	//check for uri type
	int typePos = connectionString.find("sqlite://");
	if(typePos==string::npos)
	{		
		Error(CCDB_ERROR_PARSE_CONNECTION_STRING, "SQLiteDataProvider::Connect()", "Error parse SQLite string. The string is not started with sqlite://");
		return false;
	}

	mConnectionString = connectionString;

	//ok we dont need sqlite:// in the beginning.
	connectionString.erase(0,9);
	
	//check if we are connected
	if(IsConnected())
	{
		Error(CCDB_ERROR_CONNECTION_ALREADY_OPENED, "SQLiteDataProvider::Connect(SQLiteConnectionInfo)", "Connection already opened");
		return false;
	}

	//verbose...
	Log::Verbose("ccdb::SQLiteDataProvider::Connect", StringUtils::Format("Connecting to database:\n %s", connectionString.c_str()));
	
	//Try to open sqlite database
	int result = sqlite3_open(connectionString.c_str(), &mDatabase);

	if (result != SQLITE_OK) 
	{
		string errStr = ComposeSQLiteError("Connect()");
		Error(CCDB_ERROR_CONNECTION_EXTERNAL_ERROR,"bool SQLiteDataProvider::Connect(std::string connectionString)",errStr.c_str());
		mDatabase=NULL;		//some compilers dont set NULL after delete
		mConnectionString = "";
		return false;
	}
	
	mIsConnected = true;
	return true;
}
bool ccdb::SQLiteDataProvider::IsConnected()
{
	return mIsConnected;
}


void ccdb::SQLiteDataProvider::Disconnect()
{
	if(IsConnected())
	{
//		FreeSQLiteResult();	//it would free the result or do nothing
		
		sqlite3_close(mDatabase);
		mDatabase = NULL;
		mIsConnected = false;
	}
}


bool ccdb::SQLiteDataProvider::CheckConnection( const string& errorSource/*=""*/ )
{
	ClearErrors(); //Clear error in function that can produce new ones

	//check connection
	if(!IsConnected())
	{
		Error(CCDB_ERROR_NOT_CONNECTED,errorSource.c_str(), "Provider is not connected to SQLite.");
		return false;
	}
	return true;
}
#pragma endregion Connection

#pragma region Directories


Directory* ccdb::SQLiteDataProvider::GetDirectory( const string& path )
{
	return DataProvider::GetDirectory(path);
}



bool ccdb::SQLiteDataProvider::LoadDirectories()
{
	//
	if(IsConnected())
	{
		// prepare the SQL statement from the command line
		int result = sqlite3_prepare_v2(mDatabase,"SELECT `id`, `name`, `parentId`,  strftime('%s', modified , 'localtime') as `updateTime`, `comment` FROM `directories`", -1, &mStatement, 0);
		if( result )
		{
			ComposeSQLiteError("SQLiteDataProvider::LoadDirectories");
			sqlite3_finalize(mStatement);
			return false;
		}
		
		mQueryColumns = sqlite3_column_count(mStatement);
		
		//clear diretory arrays
		mDirectories.clear();
		mDirectoriesById.clear();
		
		// execute the statement
		do
		{
			result = sqlite3_step(mStatement);
			Directory *dir = NULL;
			switch( result )
			{
				case SQLITE_DONE:
					break;
				case SQLITE_ROW:
					dir = new Directory(this, this);
					dir->SetId(ReadIndex(0));				// `id`, 
					dir->SetName(ReadString(1));			// `name`, 
					dir->SetParentId(ReadInt(2));			// `parentId`, 
					dir->SetModifiedTime(ReadUnixTime(3));	// UNIX_TIMESTAMP(`directories`.`updateTime`) as `updateTime`, 
					dir->SetComment(ReadString(4));			// `comment`

					mDirectories.push_back(dir);
					mDirectoriesById[dir->GetId()] = dir;

					// print results for this row
					//for(int col=0; col<mQueryColumns; col++)
					//{
						//sqlite3_column_double();
						//const char *txt = (const char*)sqlite3_column_text(mStatement,	col);
						//printf("%s = %s\n", sqlite3_column_name(mStatement, col), txt	? txt : "NULL");
					//}
					break;
				default:
					fprintf(stderr, "Error: %d : %s\n",  result, sqlite3_errmsg(mDatabase));
					break;
				}
		}
		while(result==SQLITE_ROW );

		// finalize the statement to release resources
		sqlite3_finalize(mStatement);
		
		//clear root directory (delete all directory structure objects)
		mRootDir->DisposeSubdirectories(); 
		mRootDir->SetFullPath("/");

		BuildDirectoryDependencies(); 

		mDirsAreLoaded=true;
	}
	return true;
}

bool ccdb::SQLiteDataProvider::SearchDirectories( vector<Directory *>& resultDirectories, const string& searchPattern, const string& parentPath/*=""*/,  int take/*=0*/, int startWith/*=0*/ )
{	
	//UpdateDirectoriesIfNeeded(); //do we need to update directories?

	//resultDirectories.clear();

	//// in SQLite compared to wildcards % is * and _ is 
	//// convert it. 
	//string likePattern = WilcardsToLike(searchPattern);
	//
	////do we need to search only in specific directory?
	//string parentAddon(""); //this is addon to query indicates this
	//if(parentPath!="")
	//{	//we should care about parent path
	//	
	//	//If parent directory is "/" this should work too, because it have an id=0
	//	//and tabeles in db wich doesnt have parents should have parentId=0
	//	
	//	Directory *parentDir;
	//	if(parentDir = GetDirectory(parentPath.c_str()))
	//	{
	//		parentAddon = StringUtils::Format(" AND `parentId` = '%i'", parentDir->GetId());
	//	}
	//	else
	//	{
	//		//request was made for directory that doestn exits
	//		//TODO place warning or not?
	//		return false;
	//	}
	//}

	//string limitAddon = PrepareLimitInsertion(take, startWith);

	////combine query
	//string query = StringUtils::Format("SELECT `id` FROM `directories` WHERE name LIKE \"%s\" %s %s;",
	//	likePattern.c_str(), parentAddon.c_str(), limitAddon.c_str());
	//
	////do query!
	//if(!QuerySelect(query))
	//{
	//	return false;
	//}
	//
	////Ok! We queried our directories! lets catch them! 
	//while(FetchRow())
	//{
	//	dbkey_t id = ReadIndex(0); //read db index key

	//	//search for such index
	//	map<dbkey_t,Directory *>::iterator dirIter = mDirectoriesById.find(id);
	//	if(dirIter != mDirectoriesById.end())
	//	{
	//		resultDirectories.push_back(dirIter->second);
	//	}
	//	else
	//	{
	//		//TODO it is some error situation! It cant happend!
	//	}
	//}

	//FreeSQLiteResult();

	//return true;
	return false;
}

vector<Directory *> ccdb::SQLiteDataProvider::SearchDirectories( const string& searchPattern, const string& parentPath/*=""*/, int startWith/*=0*/, int select/*=0*/ )
{
	vector<Directory *> result;
	SearchDirectories(result, searchPattern, parentPath, startWith, select);
	return result;
}

#pragma endregion Directories



bool ccdb::SQLiteDataProvider::IsStoredObjectsOwner()
{
	return mIsStoredObjectOwner;
}


void ccdb::SQLiteDataProvider::IsStoredObjectsOwner(bool flag)
{
	mIsStoredObjectOwner = flag;
}


#pragma region Type Tables

ConstantsTypeTable * ccdb::SQLiteDataProvider::GetConstantsTypeTable( const string& name, Directory *parentDir,bool loadColumns/*=false*/ )
{	
	ClearErrors();
	if(!CheckConnection("ConstantsTypeTable * ccdb::SQLiteDataProvider::GetConstantsTypeTable")) return NULL;

	//check the directory is ok
	if(parentDir == NULL || (parentDir->GetFullPath()!=string("/") && parentDir->GetId()<=0))
	{
		Error(CCDB_ERROR_NO_PARENT_DIRECTORY,"SQLiteDataProvider::GetConstantsTypeTable", "Parent directory is null or have invalid ID");
		return NULL;
	}
	
	// prepare the SQL statement from the command line
	//sqlite3_finalize(mStatement);
	//int result = sqlite3_prepare_v2(mDatabase,"SELECT `id`, strftime('%s', created , 'localtime') as `created`, strftime('%s', modified , 'localtime') as `modified`, `name`, `directoryId`, `nRows`, `nColumns`, `comments` FROM `typeTables` WHERE `name` = '?1' AND `directoryId` = ?2", -1, &mStatement, 0);
	int result = sqlite3_prepare_v2(mDatabase,"SELECT `id`, strftime('%s', created , 'localtime') as `created`, strftime('%s', modified , 'localtime') as `modified`, `name`, `directoryId`, `nRows`, `nColumns`, `comment` FROM `typeTables`WHERE `name` = ?1 AND `directoryId` = ?2", -1, &mStatement, 0);
	if( result )
	{
		ComposeSQLiteError("SQLiteDataProvider::GetConstantsTypeTable");
		sqlite3_finalize(mStatement);
		return NULL;
	}

	result = sqlite3_bind_text(mStatement, 1, name.c_str(), -1, SQLITE_TRANSIENT); /*`name`*/
	if( result )
	{
		ComposeSQLiteError("SQLiteDataProvider::GetConstantsTypeTable");
		sqlite3_finalize(mStatement);
		return NULL;
	}
	sqlite3_bind_int(mStatement, 2, parentDir->GetId()); /*`directoryId`*/
	if( result )
	{
		ComposeSQLiteError("SQLiteDataProvider::GetConstantsTypeTable");
		sqlite3_finalize(mStatement);
		return NULL;
	}

	mQueryColumns = sqlite3_column_count(mStatement);

	// execute the statement
	ConstantsTypeTable *table = NULL;
	do
	{
		result = sqlite3_step(mStatement);
		switch( result )
		{
		case SQLITE_DONE:
			break;
		case SQLITE_ROW:
			//ok lets read the data...
			table = new ConstantsTypeTable(this, this);
			table->SetId(ReadULong(0));
			table->SetCreatedTime(ReadUnixTime(1));
			table->SetModifiedTime(ReadUnixTime(2));
			table->SetName(ReadString(3));
			table->SetDirectoryId(ReadULong(4));
			table->SetNRows(ReadInt(5));
			table->SetNColumnsFromDB(ReadInt(6));
			table->SetComment(ReadString(7));
				
			SetObjectLoaded(table); //set object flags that it was just loaded from DB
				
			table->SetDirectory(parentDir);

			//some validation of loaded record...
			if(table->GetName() == "")
			{
				//TODO error, name should be not null and not empty
				Error(CCDB_ERROR_TYPETABLE_HAS_NO_NAME,"SQLiteDataProvider::GetConstantsTypeTable", "");
				delete table;
				sqlite3_finalize(mStatement);
				return NULL;
			}
				
			//Ok set a full path for this constant...
			table->SetFullPath(PathUtils::CombinePath(parentDir->GetFullPath(), table->GetName()));

			// print results for this row
			//for(int col=0; col<mQueryColumns; col++)
			//{
			//sqlite3_column_double();
			//const char *txt = (const char*)sqlite3_column_text(mStatement,	col);
			//printf("%s = %s\n", sqlite3_column_name(mStatement, col), txt	? txt : "NULL");
			//}
			break;
		default:
			fprintf(stderr, "Error: %d : %s\n",  result, sqlite3_errmsg(mDatabase));
			break;
		}
	}
	while(result==SQLITE_ROW );

	// finalize the statement to release resources
	sqlite3_finalize(mStatement);

	//load columns if needed
	if(loadColumns && table) LoadColumns(table);
    
    
	
	//return result;
	return table;
}


ConstantsTypeTable * ccdb::SQLiteDataProvider::GetConstantsTypeTable(const string& path, bool loadColumns/*=false*/ )
{
	return DataProvider::GetConstantsTypeTable(path, loadColumns);
}


bool ccdb::SQLiteDataProvider::GetConstantsTypeTables( vector<ConstantsTypeTable *>& resultTypeTables, const string&  parentDirPath, bool loadColumns/*=false*/ )
{
	////and directory
	//Directory *dir = GetDirectory(parentDirPath);

	////probably one may wish to check dir to be !=NULL,
	////but such check is in GetConstantsTypeHeaders( DDirectory *parentDir, vector<ConstantsTypeTable *>& consts );
	//return GetConstantsTypeTables(resultTypeTables, dir);
	return false;
}


bool ccdb::SQLiteDataProvider::GetConstantsTypeTables(  vector<ConstantsTypeTable *>& resultTypeTables, Directory *parentDir, bool loadColumns/*=false*/)
{
	//ClearErrors(); //Clear error in function that can produce new ones

	////check the directory is ok
	//if((parentDir == NULL || parentDir->GetId()<=0) && (parentDir!=mRootDir))
	//{
	//	//TODO error
	//	Error(CCDB_ERROR_NO_PARENT_DIRECTORY,"SQLiteDataProvider::GetConstantsTypeTables", "Parent directory is null or has invald ID");
	//	return NULL;
	//}
	//
	////Ok, lets cleanup result list
	//	resultTypeTables.clear(); //we clear the consts. Considering that some one else should handle deletion

	//string query = StringUtils::Format("SELECT `id`, UNIX_TIMESTAMP(`created`) as `created`, UNIX_TIMESTAMP(`modified`) as `modified`, `name`, `directoryId`, `nRows`, `nColumns`, `comments` FROM `typeTables` WHERE `directoryId` = '%i';",
	//	/*`directoryId`*/ parentDir->GetId());

	//if(!QuerySelect(query))
	//{
	//	//no report error
	//	return NULL;
	//}

	////Ok! We querryed our directories! lets catch them! 
	//while(FetchRow())
	//{
	//	//ok lets read the data...
	//	ConstantsTypeTable *result = new ConstantsTypeTable(this, this);
	//	result->SetId(ReadIndex(0));
	//	result->SetCreatedTime(ReadUnixTime(1));
	//	result->SetModifiedTime(ReadUnixTime(2));
	//	result->SetName(ReadString(3));
	//	result->SetDirectoryId(ReadULong(4));
	//	result->SetNRows(ReadInt(5));
	//	result->SetNColumnsFromDB(ReadInt(6));
	//	result->SetComment(ReadString(7));
	//	
	//	if(loadColumns) LoadColumns(result);
	//	result->SetDirectory(parentDir);
	//	
	//	SetObjectLoaded(result); //set object flags that it was just loaded from DB
	//	resultTypeTables.push_back(result);
	//}

	//FreeSQLiteResult();

	return false;
}


vector<ConstantsTypeTable *> ccdb::SQLiteDataProvider::GetConstantsTypeTables( const string& parentDirPath, bool loadColumns/*=false*/ )
{
	vector<ConstantsTypeTable *> tables;
	GetConstantsTypeTables(tables, parentDirPath, loadColumns);
	return tables;
}


vector<ConstantsTypeTable *> ccdb::SQLiteDataProvider::GetConstantsTypeTables( Directory *parentDir, bool loadColumns/*=false*/ )
{
	
		vector<ConstantsTypeTable *> tables;
		GetConstantsTypeTables(tables, parentDir, loadColumns);
		return tables;
	
}




bool ccdb::SQLiteDataProvider::SearchConstantsTypeTables( vector<ConstantsTypeTable *>& typeTables, const string& pattern, const string& parentPath /*= ""*/, bool loadColumns/*=false*/, int take/*=0*/, int startWith/*=0 */ )
{
	char funcName[] = "bool ccdb::SQLiteDataProvider::SearchConstantsTypeTables( vector<ConstantsTypeTable *>& typeTables, const string& pattern, const string& parentPath /*= ""*/, bool loadColumns/*=false*/, int take/*=0*/, int startWith/*=0 */ )";

	ClearErrors(); //Clear error in function that can produce new ones

	// in SQLite compared to wildcards % is * and _ is convert it.
	string likePattern = WilcardsToLike(pattern);

	//do we need to search only in specific directory?
	string parentAddon(""); 		//this is addon to query indicates this
	Directory *parentDir = NULL; //will need it anyway later
	if(parentPath!="")
	{	//we should care about parent path!
		if( (parentDir = GetDirectory(parentPath.c_str())) )
		{
			parentAddon = StringUtils::Format(" AND `directoryId` = '%i'", parentDir->GetId());
		}
		else
		{
			Error(CCDB_ERROR_DIRECTORY_NOT_FOUND, funcName, "Path to search is not found");
			return false;
		}
	}
    else
    {
        //In this case we will need mDirectoriesById
        //maybe we need to update our directories?
        UpdateDirectoriesIfNeeded();
    }
    
	//Ok, lets cleanup result list
	if(typeTables.size()>0)
	{
		vector<ConstantsTypeTable *>::iterator iter = typeTables.begin();
		while(iter != typeTables.end())
		{
			ConstantsTypeTable *obj = *iter;
			if(IsOwner(obj) ) delete obj;		//delete objects if this provider is owner
			iter++;	
		}
	}
	typeTables.clear(); //we clear the consts. Considering that some one else  should handle deletion

	string limitAddon = PrepareLimitInsertion(take, startWith);
	
	//combine query
	string query = StringUtils::Format("SELECT `id`, strftime('%%s', `created`, 'localtime')  as `created`, strftime('%%s', `modified`, 'localtime') as `modified`, `name`, `directoryId`, `nRows`, `nColumns`, `comment` FROM typeTables WHERE name LIKE '%s' ESCAPE '\\' %s ORDER BY `name` %s;",
		likePattern.c_str(), parentAddon.c_str(), limitAddon.c_str());
       
	// prepare the SQL statement from the command line
	int result = sqlite3_prepare_v2(mDatabase, query.c_str(), -1, &mStatement, 0);
	if( result ) 
    { 
        Error(CCDB_ERROR_QUERY_PREPARE, funcName,ComposeSQLiteError(funcName)); 
        sqlite3_finalize(mStatement); 
        return false; 
    }

	mQueryColumns = sqlite3_column_count(mStatement);

	// execute the statement
	ConstantsTypeTable *table = NULL;
	do
	{
		result = sqlite3_step(mStatement);

		switch( result )
		{
		case SQLITE_DONE:
			break;
		case SQLITE_ROW:
			table = new ConstantsTypeTable(this, this);
			table->SetId(ReadULong(0));
			table->SetCreatedTime(ReadUnixTime(1));
			table->SetModifiedTime(ReadUnixTime(2));
			table->SetName(ReadString(3));
			table->SetDirectoryId(ReadULong(4));
			table->SetNRows(ReadInt(5));
			table->SetNColumnsFromDB(ReadInt(6));
			table->SetComment(ReadString(7));

			if(parentDir) //we already may have parrent directory
			{
			    table->SetDirectory(parentDir);
			}
			else //Or we should find it...
			{
				table->SetDirectory(mDirectoriesById[table->GetDirectoryId()]);
			}

			SetObjectLoaded(table); //set object flags that it was just loaded from DB
			
			typeTables.push_back(table);
			break;
		default:
			fprintf(stderr, "Error: %d : %s\n",  result, sqlite3_errmsg(mDatabase));
			break;
		}
	}
	while(result==SQLITE_ROW);

	// finalize the statement to release resources
	sqlite3_finalize(mStatement);

    //Load COLUMNS if needed...
	if(loadColumns)
    {
        for (int i=0; i< typeTables.size(); i++)
        {
            LoadColumns(typeTables[i]);
        }   
    }
 	return true;
}


std::vector<ConstantsTypeTable *> ccdb::SQLiteDataProvider::SearchConstantsTypeTables( const string& pattern, const string& parentPath /*= ""*/, bool loadColumns/*=false*/, int take/*=0*/, int startWith/*=0 */ )
{
	std::vector<ConstantsTypeTable *> tables;
	SearchConstantsTypeTables(tables, pattern, parentPath,loadColumns, take, startWith);
	return tables;
}

bool ccdb::SQLiteDataProvider::LoadColumns( ConstantsTypeTable* table )
{
	ClearErrors(); //Clear error in function that can produce new ones
	if(!CheckConnection("ccdb::SQLiteDataProvider::LoadColumns( ConstantsTypeTable* table )")) return false;
	
	//check the directory is ok
	if(table->GetId()<=0)
	{
		Error(CCDB_ERROR_INVALID_ID,"SQLiteDataProvider::LoadColumns", "Type table has wrong ID");
		return false;
	}

	// prepare the SQL statement from the command line
	int result = sqlite3_prepare_v2(mDatabase, "SELECT `id`, strftime('%s', created , 'localtime') as `created`, strftime('%s', modified , 'localtime') as `modified`, `name`, `columnType`, `comment` FROM `columns` WHERE `typeId` = ?1 ORDER BY `order`;", -1, &mStatement, 0);
	if( result )
	{
		ComposeSQLiteError("ccdb::SQLiteDataProvider::LoadColumns");
		sqlite3_finalize(mStatement);
		return false;
	}

	result = sqlite3_bind_int(mStatement, 1, table->GetId());	/*`directoryId`*/
	if( result )
	{
		ComposeSQLiteError("ccdb::SQLiteDataProvider::LoadColumns");
		sqlite3_finalize(mStatement);
		return false;
	}

	mQueryColumns = sqlite3_column_count(mStatement);

	

	// execute the statement
	do
	{
		result = sqlite3_step(mStatement);
		ConstantsTypeColumn *column = NULL;
		switch( result )
		{
		case SQLITE_DONE:
			break;
		case SQLITE_ROW:
			column = new ConstantsTypeColumn(table, this);
			column->SetId(ReadULong(0));				
			column->SetCreatedTime(ReadUnixTime(1));
			column->SetModifiedTime(ReadUnixTime(2));
			column->SetName(ReadString(3));
			column->SetType(ReadString(4));
			column->SetComment(ReadString(5));
			column->SetDBTypeTableId(table->GetId());
			SetObjectLoaded(column); //set object flags that it was just loaded from DB
			table->AddColumn(column);

			break;
		default:
			fprintf(stderr, "Error: %d : %s\n",  result, sqlite3_errmsg(mDatabase));
			break;
		}
	}
	while(result==SQLITE_ROW );

	// finalize the statement to release resources
	sqlite3_finalize(mStatement);
	return true;
}

#pragma endregion Type Tables
//----------------------------------------------------------------------------------------
//	R U N   R A N G E S
//----------------------------------------------------------------------------------------
#pragma region Run ranges

RunRange* ccdb::SQLiteDataProvider::GetRunRange( int min, int max, const string& name /*= ""*/ )
{
	////build query
	//string query = "SELECT `id`, UNIX_TIMESTAMP(`created`) as `created`, UNIX_TIMESTAMP(`modified`) as `modified`, `name`, `runMin`, `runMax`,  `comment`"
	//               " FROM `runRanges` WHERE `runMin`='%i' AND `runMax`='%i' AND `name`=\"%s\"";
	//query = StringUtils::Format(query.c_str(), min, max, name.c_str());
	//
	////query this
	//if(!QuerySelect(query))
	//{
	//	//NO report error
	//	return NULL;
	//}
	//
	////Ok! We querryed our run range! lets catch it! 
	//
	//if(!FetchRow())
	//{
	//	//nothing was selected
	//	return NULL;
	//}

	////ok lets read the data...
	//RunRange *result = new RunRange(this, this);
	//result->SetId(ReadULong(0));
	//result->SetCreatedTime(ReadUnixTime(1));
	//result->SetModifiedTime(ReadUnixTime(2));
	//result->SetName(ReadString(3));
	//result->SetMin(ReadInt(4));
	//result->SetMax(ReadInt(5));
	//result->SetComment(ReadString(6));
	//
	//if(mReturnedRowsNum>1)
	//{
	//	//TODO warning not uniq row
	//	Error(CCDB_ERROR,"SQLiteDataProvider::GetRunRange", "Run range with such min, max and name is not alone in the DB");
	//}

	//FreeSQLiteResult();
	//return result;
	return NULL;
}


RunRange* ccdb::SQLiteDataProvider::GetRunRange( const string& name )
{
	/*
	ClearErrors(); //Clear error in function that can produce new ones

	//build query
	string query = "SELECT `id`, UNIX_TIMESTAMP(`created`) as `created`, UNIX_TIMESTAMP(`modified`) as `modified`, `name`, `runMin`, `runMax`,  `comment`"
		" FROM `runRanges` WHERE `name`=\"%s\"";
	query = StringUtils::Format(query.c_str(), name.c_str());

	//query this
	if(!QuerySelect(query))
	{
		//NO report error
		return NULL;
	}

	//Ok! We querried our run range! lets catch it! 
	if(!FetchRow())
	{
		//nothing was selected
		return NULL;
	}

	//ok lets read the data...
	RunRange *result = new RunRange(this, this);
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
		Error(CCDB_ERROR,"SQLiteDataProvider::GetRunRange", "Run range with such name is not alone in the DB");
	}

	FreeSQLiteResult();
	return result;*/
	return NULL;
}


bool ccdb::SQLiteDataProvider::GetRunRanges(vector<RunRange*>& resultRunRanges, ConstantsTypeTable* table, const string& variation/*=""*/, int take/*=0*/, int startWith/*=0*/)
{
	/*ClearErrors(); //Clear error in function that can produce new ones

	if(!CheckConnection("SQLiteDataProvider::GetRunRanges(vector<DRunRange*>& resultRunRanges, ConstantsTypeTable* table, int take, int startWith)")) return false;
	
	//validate table
	if(!table || !table->GetId())
	{
		//TODO report error
		Error(CCDB_ERROR_NO_TYPETABLE,"SQLiteDataProvider::GetRunRanges", "Type table is null or have invalid id");
		return false;
	}
	//variation handle
	string variationWhere("");
	if(variation != "")
	{
		variationWhere.assign(StringUtils::Format(" AND `variations`.`name`=\"%s\" ", variation.c_str()));
	}

	//limits handle 
	string limitInsertion = PrepareLimitInsertion(take, startWith);
	
	//Ok, lets cleanup result list
	if(resultRunRanges.size()>0)
	{
		vector<RunRange *>::iterator iter = resultRunRanges.begin();
		while(iter != resultRunRanges.end())
		{
			RunRange *obj = *iter;
			if(IsOwner(obj)) delete obj;		//delete objects if this provider is owner
			iter++;
		}
	}
	resultRunRanges.clear(); //we clear the consts. Considering that some one else should handle deletion


	//ok now we must build our mighty query...
	string query= 
		" SELECT "
		" DISTINCT `runRanges`.`id` as `id`, "
		" UNIX_TIMESTAMP(`runRanges`.`created`) as `created`, "
		" UNIX_TIMESTAMP(`runRanges`.`modified`) as `modified`, "
		" `runRanges`.`name` as `name`, "
		" `runRanges`.`runMin` as `runMin`, "
		" `runRanges`.`runMax` as `runMax`, "
		"`runRanges`.`comment` as `comment` "
		" FROM `typeTables` "
		" INNER JOIN `assignments` ON `assignments`.`runRangeId`= `runRanges`.`id` "
		" INNER JOIN `variations` ON `assignments`.`variationId`= `variations`.`id` "
		" INNER JOIN `constantSets` ON `assignments`.`constantSetId` = `constantSets`.`id` "
		" INNER JOIN `typeTables` ON `constantSets`.`constantTypeId` = `typeTables`.`id` "
		" WHERE `typeTables`.`id` = '%i' "
		" %s "
		" ORDER BY `runRanges`.`runMin` ASC	 %s";
		
	query=StringUtils::Format(query.c_str(), table->GetId(), variationWhere.c_str(), limitInsertion.c_str());
	
	//query this
	if(!QuerySelect(query))
	{
		//TODO report error
		return false;
	}

	//Ok! We querried our run range! lets catch it! 
	while(FetchRow())
	{
		//ok lets read the data...
		RunRange *result = new RunRange(this, this);
		result->SetId(ReadULong(0));
		result->SetCreatedTime(ReadUnixTime(1));
		result->SetModifiedTime(ReadUnixTime(2));
		result->SetName(ReadString(3));
		result->SetMin(ReadInt(4));
		result->SetMax(ReadInt(5));
		result->SetComment(ReadString(7));
		
		SetObjectLoaded(result);
		resultRunRanges.push_back(result);
	}

	FreeSQLiteResult();
	return true;
	*/
	return false;
}

#pragma endregion Run ranges
//----------------------------------------------------------------------------------------
//	V A R I A T I O N
//----------------------------------------------------------------------------------------
#pragma region Variation

bool ccdb::SQLiteDataProvider::GetVariations(vector<Variation*>& resultVariations, ConstantsTypeTable* table, int run, int take, int startWith)
{
	//ClearErrors(); //Clear error in function that can produce new ones

	//if(!CheckConnection("SQLiteDataProvider::GetRunRanges(vector<DRunRange*>& resultRunRanges, ConstantsTypeTable* table, int take, int startWith)")) return false;
	//
	////validate table
	//if(!table || !table->GetId())
	//{
	//	//TODO report error
	//	Error(CCDB_ERROR_NO_TYPETABLE,"SQLiteDataProvider::GetVariations", "Type table is null or empty");
	//	return false;
	//}
	//
	////run range handle
	//string runRangeWhere(""); //Where clause for run range
	//if(run != 0)
	//{		
	//	runRangeWhere = StringUtils::Format(" AND `runRanges`.`runMin` <= '%i' AND `runRanges`.`runMax` >= '%i' ", run, run);
	//}

	////limits handle 
	//string limitInsertion = PrepareLimitInsertion(take, startWith);
	//
	////Ok, lets cleanup result list
	//if(resultVariations.size()>0)
	//{
	//	vector<Variation *>::iterator iter = resultVariations.begin();
	//	while(iter != resultVariations.end())
	//	{
	//		Variation *obj = *iter;
	//		if(IsOwner(obj)) delete obj;		//delete objects if this provider is owner
	//		iter++;
	//	}
	//}
	//resultVariations.clear(); //we clear the consts. Considering that some one else should handle deletion


	////ok now we must build our mighty query...
	//string query= 
	//	" SELECT "
	//	" DISTINCT `variations`.`id` as `varId`, "
	//	" UNIX_TIMESTAMP(`variations`.`created`) as `created`, "
	//	" UNIX_TIMESTAMP(`variations`.`modified`) as `modified`, "
	//	" `variations`.`name` as `name`, "
	//	" `variations`.`description` as `description`, "
	//	" `variations`.`comment` as `comment` "
	//	" FROM `runRanges` "
	//	" INNER JOIN `assignments`  ON `assignments`.`runRangeId`= `runRanges`.`id` "
	//	" INNER JOIN `variations`   ON `assignments`.`variationId`= `variations`.`id` "
	//	" INNER JOIN `constantSets` ON `assignments`.`constantSetId` = `constantSets`.`id` "
	//	" INNER JOIN `typeTables`   ON `constantSets`.`constantTypeId` = `typeTables`.`id` "
	//	" WHERE `typeTables`.`id` = '%i' "
	//	" %s "
	//	" ORDER BY `runRanges`.`runMin` ASC	 %s";
	//	
	//query=StringUtils::Format(query.c_str(), table->GetId(), runRangeWhere.c_str(), limitInsertion.c_str());
	//
	////query this
	//if(!QuerySelect(query))
	//{
	//	//TODO report error
	//	return false;
	//}

	////Ok! We querried our run range! lets catch it! 
	//while(FetchRow())
	//{
	//	//ok lets read the data...
	//	Variation *result = new Variation(this, this);
	//	result->SetId(ReadULong(0));
	//	result->SetCreatedTime(ReadUnixTime(1));
	//	result->SetModifiedTime(ReadUnixTime(2));
	//	result->SetName(ReadString(3));
	//	result->SetDescription(ReadString(4));
	//	result->SetComment(ReadString(5));
	//	
	//	SetObjectLoaded(result);
	//	resultVariations.push_back(result);
	//}

	//FreeSQLiteResult();
	//return true;
	return false;
}

vector<Variation *> ccdb::SQLiteDataProvider::GetVariations( ConstantsTypeTable *table, int run/*=0*/, int take/*=0*/, int startWith/*=0 */ )
{
	vector<Variation *> resultVariations;
	GetVariations(resultVariations, table, run, take, startWith);
	return resultVariations;
}



Variation* ccdb::SQLiteDataProvider::GetVariation( const string& name )
{
	/** @brief Gets mysql record Id for specified variation name
	 *         returns -1 if variation with this name is not found
	 *	 
	 * @param    [in] variation name
	 * @return   dbkey_t id of variation or -1 if variation with this name is not found
	 */

	char thisFunc[] = "ccdb::SQLiteDataProvider::GetVariation( const string& name )";

    ClearErrors(); //Clear error in function that can produce new ones

    //check that maybe we have this variation id by the last request?
    if(mLastVariation!=NULL && name == mLastVariation->GetName()) return mLastVariation;

    string query = "SELECT `id`, `parentId`, `name` FROM `variations` WHERE `name`= ?1";

	// prepare the SQL statement from the command line
	int result = sqlite3_prepare_v2(mDatabase, query.c_str(), -1, &mStatement, 0);
	if( result ) { ComposeSQLiteError(thisFunc); sqlite3_finalize(mStatement); return NULL; }

	result = sqlite3_bind_text(mStatement, 1, name.c_str(), -1, SQLITE_TRANSIENT);
	if( result ) { ComposeSQLiteError(thisFunc); sqlite3_finalize(mStatement); return NULL; }

	mQueryColumns = sqlite3_column_count(mStatement);
    //select variation
    mLastVariation = SelectVariation();
    return mLastVariation;
}


Variation* ccdb::SQLiteDataProvider::GetVariationById( dbkey_t id )
{
	/** @brief Gets mysql record Id for specified variation name
	 *         returns -1 if variation with this name is not found
	 *	 
	 * @param    [in] variation name
	 * @return   dbkey_t id of variation or -1 if variation with this name is not found
	 */

	char thisFunc[] = "ccdb::SQLiteDataProvider::GetVariationById( dbkey_t id )";

    ClearErrors(); //Clear error in function that can produce new ones

    //check that maybe we have this variation id by the last request?
    if(mVariationsById.find(id) != mVariationsById.end()) return mVariationsById[id];

    string query = "SELECT `id`, `parentId`, `name` FROM `variations` WHERE `id`= ?1";

	// prepare the SQL statement from the command line
	int result = sqlite3_prepare_v2(mDatabase, query.c_str(), -1, &mStatement, 0);
	if( result ) { ComposeSQLiteError(thisFunc); sqlite3_finalize(mStatement); return NULL; }

	result = sqlite3_bind_int(mStatement, 1, id);
	if( result ) { ComposeSQLiteError(thisFunc); sqlite3_finalize(mStatement); return NULL; }

    //select variation
    mLastVariation = SelectVariation();
    return mLastVariation;
}


Variation* ccdb::SQLiteDataProvider::SelectVariation()
{
    ///* Executes statement and create Variation object. mStatement should be prepared when calling the function

    char thisFunc[] = "ccdb::SQLiteDataProvider::SelectVariation()";

	// execute the statement
	dbkey_t id = (dbkey_t)-1;
    dbkey_t parentId = (dbkey_t)-1;
    string name;
    int result;
	do
	{
		result = sqlite3_step(mStatement);

		switch( result )
		{
		case SQLITE_DONE:
			break;
		case SQLITE_ROW:			
			id =  ReadULong(0);
            parentId = ReadULong(1);
            name = ReadString(2);
			break;
		default:
			ComposeSQLiteError(thisFunc);
            sqlite3_finalize(mStatement); 
            return NULL;
			break;
		}
	}
	while(result==SQLITE_ROW );

	// finalize the statement to release resources
	sqlite3_finalize(mStatement);
	
    Variation *var = new Variation(this, this);
    var->SetName(name);
    var->SetId(id);
    var->SetParentDbId(parentId);
    
    //recursive call to get variation parent
    if(parentId>0) var->SetParent(GetVariationById(parentId));
    
    //add to cache
    if(mVariationsById.find(id) == mVariationsById.end())  mVariationsById[id] = var;
    
	return var;
}


#pragma endregion Variation
//----------------------------------------------------------------------------------------
//	A S S I G N M E N T S
//----------------------------------------------------------------------------------------
#pragma region Assignments	
Assignment* ccdb::SQLiteDataProvider::GetAssignmentShort(int run, const string& path, const string& variationName, bool loadColumns /*=false*/)
{
   /** @brief Get Assignment with data blob only
    *
    * This function is optimized for fast data retrieving and is assumed to be performance critical;
    * This function doesn't return any specified information like variation object or run-range object
    * @see GetAssignmentFull
    * @param [in] run - run number
    * @param [in] path - object path
    * @param [in] variation - variation name
    * @return DAssignment object or NULL if no assignment is found or error
    */
   return GetAssignmentShort(run,path,0,variationName, loadColumns);
}


Assignment* ccdb::SQLiteDataProvider::GetAssignmentShort(int run, const string& path, time_t time, const string& variationName, bool loadColumns /*=false*/)
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
	char thisFunc[] = "ccdb::SQLiteDataProvider::GetAssignmentShort(int run, const string& path, time_t time, const string& variation, bool loadColumns /*=true*/)";
	ClearErrors(); //Clear error in function that can produce new ones

	if(!CheckConnection(thisFunc)) return NULL;
	
    //Get type table
    ConstantsTypeTable *table = GetConstantsTypeTable(path, loadColumns);
    if(!table)
    {
        Error(CCDB_ERROR_NO_TYPETABLE, "SQLiteDataProvider::GetAssignmentShort", "Type table was not found: '"+path+"'" );
        return NULL;
    }
    
    //get variation
    Variation* variation = GetVariation(variationName);
    if(!variation)
    {
        Error(CCDB_ERROR_VARIATION_INVALID,"SQLiteDataProvider::GetAssignmentShort", "No variation '"+variationName+"' was found");
        return NULL;
    }


	////ok now we must build our mighty query...
	string query(
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
	
//	cout<<query<<endl;

	// prepare the SQL statement from the command line
	int result = sqlite3_prepare_v2(mDatabase, query.c_str(), -1, &mStatement, 0);
	if( result ) { ComposeSQLiteError(thisFunc); sqlite3_finalize(mStatement); return NULL; }

	result = sqlite3_bind_int(mStatement, 1, run);	/*`directoryId`*/
	if( result ) { ComposeSQLiteError(thisFunc); sqlite3_finalize(mStatement); return NULL; }
	
	result = sqlite3_bind_int(mStatement, 2, variation->GetId());	/*`variationId`*/
	if( result ) { ComposeSQLiteError(thisFunc); sqlite3_finalize(mStatement); return NULL; }
			
	result = sqlite3_bind_int(mStatement, 3, table->GetId());	/*``typeTables`.`directoryId``*/
	if( result ) { ComposeSQLiteError(thisFunc); sqlite3_finalize(mStatement); return NULL; }
    
    if(time>0)
    {
        result = sqlite3_bind_int64(mStatement, 4, time);	/*` `assignments`.`created``*/
        if( result ) { ComposeSQLiteError(thisFunc); sqlite3_finalize(mStatement); return NULL; }
    }
	//cout<<endl<<"time "<<time<<endl;
	mQueryColumns = sqlite3_column_count(mStatement);
    int selectedRows = 0;
	// execute the statement
	Assignment *assignment = NULL;
	do
	{
		result = sqlite3_step(mStatement);
		
		switch( result )
		{
		case SQLITE_DONE:
			break;
		case SQLITE_ROW:
			assignment = new Assignment(this, this);
			assignment->SetId( ReadIndex(0) );			
			assignment->SetRawData( ReadString(1) );

			//additional fill
			assignment->SetRequestedRun(run);
            selectedRows++;
			break;
		default:
			ComposeSQLiteError(thisFunc); 
            sqlite3_finalize(mStatement); 
            return NULL;
			break;
		}
	} while(result==SQLITE_ROW );

    // finalize the statement to release resources
    sqlite3_finalize(mStatement);
        
    //If We have not found data for this variation, getting data for parent variation
    if((assignment == NULL && selectedRows==0) && variation->GetParentDbId()!=0)
    {
        return GetAssignmentShort(run, path, time, variation->GetParent()->GetName(), loadColumns);
    }
    
	if(assignment == NULL) 
	{
		delete table;
		return NULL;
	}

    assignment->SetTypeTable(table);
    assignment->BeOwner(table);
    table->SetOwner(assignment);

	return assignment;
}


Assignment* ccdb::SQLiteDataProvider::GetAssignmentFull( int run, const string& path, const string& variation )
{
	if(!CheckConnection("SQLiteDataProvider::GetAssignmentFull(int run, cconst string& path, const string& variation")) return NULL;
	return DataProvider::GetAssignmentFull(run, path, variation);
}

Assignment* ccdb::SQLiteDataProvider::GetAssignmentFull( int run, const string& path,int version, const string& variation/*= "default"*/)
{
	if(!CheckConnection("SQLiteDataProvider::GetAssignmentFull( int run, const char* path, const char* variation, int version /*= -1*/ )")) return NULL;
	return DataProvider::GetAssignmentFull(run, path, variation);
}


bool ccdb::SQLiteDataProvider::GetAssignments( vector<Assignment *> &assingments,const string& path, int runMin, int runMax, const string& runRangeName, const string& variation, time_t beginTime, time_t endTime, int sortBy/*=0*/,  int take/*=0*/, int startWith/*=0*/ )
{
	char thisFunc[] = "ccdb::SQLiteDataProvider::GetAssignments( vector<Assignment *> &assingments,const string& path, int runMin, int runMax, const string& runRangeName, const string& variation, time_t beginTime, time_t endTime, int sortBy/*=0*/,  int take/*=0*/, int startWith/*=0*/ )";
	ClearErrors(); //Clear error in function that can produce new ones

	if(!CheckConnection(thisFunc)) return false;

	//get table! 
	ConstantsTypeTable *table = GetConstantsTypeTable(path, true);
	if(!table)
	{
		Error(CCDB_ERROR_NO_TYPETABLE,"SQLiteDataProvider::GetAssignments", "Type table was not found");
		return false;
	}

	//Ok, lets cleanup result list
	if(assingments.size()>0)
	{
		vector<Assignment *>::iterator iter = assingments.begin();
		while(iter != assingments.end())
		{
			Assignment *obj = *iter;
			if(IsOwner(obj)) delete obj;	//delete objects if this provider is owner
			iter++;
		}
	}
	assingments.clear();

	//run range handle
	string runRangeWhere(""); //Where clause for run range
	if(runRangeName != "")
	{
		runRangeWhere = StringUtils::Format(" AND `runRanges`.`name` = \"%s\" ", runRangeName.c_str());
	}
	else if(runMax!=0 || runMin!=0)
	{
		runRangeWhere = StringUtils::Format(" AND `runRanges`.`runMin` <= '%i' AND `runRanges`.`runMax` >= '%i' ", runMin, runMax);
	}

	//variation handle
	string variationWhere("");
	if(variation != "")
	{
		variationWhere.assign(StringUtils::Format(" AND `variations`.`name`=\"%s\" ", variation.c_str()));
	}

	//time handle 
	string timeWhere("");
	if(beginTime!=0 || endTime!=0)
	{
		timeWhere.assign(StringUtils::Format(" AND `asCreated` >= '%i' AND `asCreated` <= '%i' ", beginTime, endTime));
	}

	//limits handle 
	string limitInsertion = PrepareLimitInsertion(take, startWith);

	//sort order
	string orderByInsertion(" ORDER BY `assignments`.`created` DESC ");
	if(sortBy == 1)
	{
		orderByInsertion.assign(" ORDER BY `assignments`.`created` ASC ");
	}


	//ok now we must build our mighty query...
	string query=
	/*fieldN*/  " SELECT "
	/*00*/  " `assignments`.`id` AS `asId`,	"
	/*01*/  " strftime('%%s', `assignments`.`created`, 'localtime')  as `asCreated`,"
	/*02*/  " strftime('%%s', `assignments`.`modified`, 'localtime') as `asModified`,"
	/*03*/  " `assignments`.`comment` as `asComment`, "
	/*04*/  " `constantSets`.`id` AS `constId`, "
	/*05*/  " `constantSets`.`vault` AS `blob`, "
	/*06*/  " `runRanges`.`id`   AS `rrId`, "
	/*07*/  " strftime('%%s', `runRanges`.`created`, 'localtime') as `rrCreated`,"
	/*08*/  " strftime('%%s', `runRanges`.`modified`, 'localtime') as `rrModified`,	"
	/*09*/  " `runRanges`.`name`   AS `rrName`, "
	/*10*/  " `runRanges`.`runMin`   AS `rrMin`, "
	/*11*/  " `runRanges`.`runMax`   AS `runMax`, "
	/*12*/  " `runRanges`.`comment` as `rrComment`, "
	/*13*/  " `variations`.`id`  AS `varId`, "
	/*14*/  " strftime('%%s', `variations`.`created`, 'localtime')  as `varCreated`,"
	/*15*/  " strftime('%%s', `variations`.`modified`, 'localtime') as `varModified`,	"
	/*16*/  " `variations`.`name` AS `varName`, "
	/*17*/  " `variations`.`comment`  AS `varComment` "
		    " FROM `runRanges` "
		    " INNER JOIN `assignments` ON `assignments`.`runRangeId`= `runRanges`.`id`"
		    " INNER JOIN `variations` ON `assignments`.`variationId`= `variations`.`id`	"
		    " INNER JOIN `constantSets` ON `assignments`.`constantSetId` = `constantSets`.`id`"
		    " INNER JOIN `typeTables` ON `constantSets`.`constantTypeId` = `typeTables`.`id`"
		    " WHERE  `typeTables`.`id` = '%i' %s %s %s %s %s";


	query=StringUtils::Format(query.c_str(), table->GetId(), runRangeWhere.c_str(), variationWhere.c_str(), timeWhere.c_str(), orderByInsertion.c_str(), limitInsertion.c_str());
	
	// prepare the SQL statement from the command line
	int result = sqlite3_prepare_v2(mDatabase, query.c_str(), -1, &mStatement, 0);
	if( result ) { ComposeSQLiteError(thisFunc); sqlite3_finalize(mStatement); return false; }

	mQueryColumns = sqlite3_column_count(mStatement);

	// execute the statement
	Assignment *assignment = NULL;
	do
	{
		result = sqlite3_step(mStatement);

		switch( result )
		{
		case SQLITE_DONE:
			break;
		case SQLITE_ROW:
			assingments.push_back(FetchAssignment(table));
			break;
		default:
			fprintf(stderr, "Error: %d : %s\n",  result, sqlite3_errmsg(mDatabase));
			break;
		}
	}
	while(result==SQLITE_ROW );

	// finalize the statement to release resources
	sqlite3_finalize(mStatement);

	return true;	
}

bool ccdb::SQLiteDataProvider::GetAssignments(vector<Assignment*>& assingments, const string& path, int run, const string& variation, time_t date, int take, int startWith)
{
	return GetAssignments(assingments, path, run, run,"",variation, 0, date, take, startWith);
}

vector<Assignment *> ccdb::SQLiteDataProvider::GetAssignments( const string& path, int run, const string& variation/*=""*/, time_t date/*=0*/, int take/*=0*/, int startWith/*=0*/ )
{
	vector<Assignment *> assingments;
	GetAssignments(assingments, path, run,variation, date, take, startWith);
	return assingments;
}

bool ccdb::SQLiteDataProvider::GetAssignments( vector<Assignment *> &assingments,const string& path, const string& runName, const string& variation/*=""*/, time_t date/*=0*/, int take/*=0*/, int startWith/*=0*/ )
{
	return GetAssignments(assingments, path, 0, 0,runName,variation, 0, date, take, startWith);
}

vector<Assignment *> ccdb::SQLiteDataProvider::GetAssignments( const string& path, const string& runName, const string& variation/*=""*/, time_t date/*=0*/, int take/*=0*/, int startWith/*=0*/ )
{
	vector<Assignment *> assingments;
	GetAssignments(assingments, path, runName,variation, date, take, startWith);
	return assingments;
}

bool ccdb::SQLiteDataProvider::FillAssignment(Assignment* assignment)
{
	//ClearErrors(); //Clear error in function that can produce new ones
	//if(assignment == NULL || !assignment->GetId())
	//{
	//	//todo report errors
	//	Error(CCDB_ERROR_ASSIGMENT_INVALID,"SQLiteDataProvider::FillAssignment", "ASSIGnMENt is NULL or has improper ID so update operations cant be done");
	//	return false;
	//}
	//
	////ok now we must build our mighty query...
	//string query=
	///*fieldN*/  " SELECT "
	///*00*/  " `assignments`.`id` AS `asId`,	"
	///*01*/  " UNIX_TIMESTAMP(`assignments`.`created`) as `asCreated`,"
	///*02*/  " UNIX_TIMESTAMP(`assignments`.`modified`) as `asModified`,	"
	///*03*/  " `assignments`.`comment` as `asComment`, "
	///*04*/  " `constantSets`.`id` AS `constId`, "
	///*05*/  " `constantSets`.`vault` AS `blob`, "
	///*06*/  " `runRanges`.`id`   AS `rrId`, "
	///*07*/  " UNIX_TIMESTAMP(`runRanges`.`created`) as `rrCreated`,"
	///*08*/  " UNIX_TIMESTAMP(`runRanges`.`modified`) as `rrModified`,	"
	///*09*/  " `runRanges`.`name`   AS `rrName`, "
	///*10*/  " `runRanges`.`runMin`   AS `rrMin`, "
	///*11*/  " `runRanges`.`runMax`   AS `runMax`, "
	///*12*/  " `runRanges`.`comment` as `rrComment`, "
	///*13*/  " `variations`.`id`  AS `varId`, "
	///*14*/  " UNIX_TIMESTAMP(`variations`.`created`) as `varCreated`,"
	///*15*/  " UNIX_TIMESTAMP(`variations`.`modified`) as `varModified`,	"
	///*16*/  " `variations`.`name` AS `varName`, "
	///*17*/  " `variations`.`comment`  AS `varComment`, "
	///*18*/  " `typeTables`.`name` AS `typeTableName`, "
	///*19*/  " `directories`.`id` AS `dirId` "
	//	    " FROM `runRanges` "
	//	    " INNER JOIN `assignments` ON `assignments`.`runRangeId`= `runRanges`.`id`"
	//	    " INNER JOIN `variations` ON `assignments`.`variationId`= `variations`.`id`	"
	//	    " INNER JOIN `constantSets` ON `assignments`.`constantSetId` = `constantSets`.`id`"
	//	    " INNER JOIN `typeTables` ON `constantSets`.`constantTypeId` = `typeTables`.`id`"
	//		" INNER JOIN `directories` ON `typeTables`.`directoryId` = `directories`.`id`"
	//	    " WHERE  `assignments`.`id` = '%i'";
	//
	//
	//query=StringUtils::Format(query.c_str(), assignment->GetId());
	////cout << query<<endl;
	////query this
	//if(!QuerySelect(query))
	//{
	//	//TODO report error
	//	cout<<"!QuerySelect(query)"<<endl;
	//	return false;
	//}
	//
	//if(!FetchRow())
	//{
	//	//TODO report error
	//	cout<<"no assignment selected!"<<endl;
	//	return false;
	//}
	//
	////fetch readed row
	//FetchAssignment(assignment, assignment->GetTypeTable());
	//
	////Ok! Here is a tricky moment. We should load a constant type table 
	////but we have an API that allows us to load such directories by name
	////The problem that we should know a full path of it. 
	////So we pulled a directory ID and data table name. 
	//// We have a list of directories by their ID thus we will know a full path
	//// of type table. 
	//// lets make this plan work
	//
	//string typeTableName = ReadString(18);
	//dbkey_t directoryId = ReadIndex(19);
	//
	////Mayby we need to update our directories?
	//UpdateDirectoriesIfNeeded();

	//if(mDirectoriesById.find(directoryId) == mDirectoriesById.end())
	//{
	//	//todo report errors
	//	Error(CCDB_ERROR,"SQLiteDataProvider::FillAssignment", "Cannot find directory locally by ID taken from database");
	//	return false;
	//}

	//Directory *parent = mDirectoriesById[directoryId];
	//
	//ConstantsTypeTable * table = GetConstantsTypeTable(typeTableName, parent, true);
	//if(!table)
	//{
	//	Error(CCDB_ERROR_NO_TYPETABLE,"SQLiteDataProvider::FillAssignment", "Type table was not loaded");
	//	return false;
	//}

	//assignment->SetTypeTable(table);
	//table->SetOwner(assignment);

	//FreeSQLiteResult();
	//
	//return true;
	return false;
}

Assignment* ccdb::SQLiteDataProvider::FetchAssignment(ConstantsTypeTable* table)
{
	Assignment * assignment = new Assignment(this, this); //it is our victim

	FetchAssignment(assignment, table);

	//take it!
	return assignment;
}


void ccdb::SQLiteDataProvider::FetchAssignment(Assignment* assignment, ConstantsTypeTable* table)
{
	//ok now we must fetch our mighty query...
	assignment->SetId(ReadIndex(0));				/*00  " `assignments`.`id` AS `asId`,	"*/
	assignment->SetCreatedTime(ReadUnixTime(1));	/*01  " UNIX_TIMESTAMP(`assignments`.`created`) as `asCreated`,"*/
	assignment->SetModifiedTime(ReadUnixTime(2));	/*02  " UNIX_TIMESTAMP(`assignments`.`modified`) as `asModified`,	"*/
	assignment->SetComment(ReadString(3));			/*03  " `assignments`.`comment) as `asComment`,	"					 */
	assignment->SetDataVaultId(ReadIndex(4));		/*04  " `constantSets`.`id` AS `constId`, "							 */
	assignment->SetRawData(ReadString(5));			/*05  " `constantSets`.`vault` AS `blob`, "							 */
	
	RunRange * runRange = new RunRange(assignment, this);	
	runRange->SetId(ReadIndex(6));					/*06  " `runRanges`.`id`   AS `rrId`, "	*/
	runRange->SetCreatedTime(ReadUnixTime(7));		/*07  " UNIX_TIMESTAMP(`runRanges`.`created`) as `rrCreated`,"*/
	runRange->SetModifiedTime(ReadUnixTime(8));		/*08  " UNIX_TIMESTAMP(`runRanges`.`modified`) as `rrModified`,	"*/
	runRange->SetName(ReadString(9));				/*09  " `runRanges`.`name`   AS `rrName`, "		*/
	runRange->SetMin(ReadInt(10));					/*10  " `runRanges`.`runMin`   AS `rrMin`, "	*/
	runRange->SetMax(ReadInt(11));					/*11  " `runRanges`.`runMax`   AS `runMax`, "	*/
	runRange->SetComment(ReadString(12));			/*12  " `runRanges`.`comment` as `rrComment`, "	*/
	
	Variation * variation = new Variation(assignment, this);
	variation->SetId(ReadIndex(13));				/*13  " `variations`.`id`  AS `varId`, */
	variation->SetCreatedTime(ReadUnixTime(14));	/*14  " UNIX_TIMESTAMP(`variations`.`created`) as `varCreated`,"	 */
	variation->SetModifiedTime(ReadUnixTime(15));	/*15  " UNIX_TIMESTAMP(`variations`.`modified`) as `varModified`,	 */
	variation->SetName(ReadString(16));			/*16  " `variations`.`name` AS `varName` "*/
	variation->SetComment(StringUtils::Decode(ReadString(12)));		/*17  " `variations`.`comment`  AS `varComment` "*/

	//compose objects
	assignment->SetRunRange(runRange);
	assignment->SetVariation(variation);
	assignment->SetTypeTable(table);
	if(IsOwner(table)) table->SetOwner(assignment);
}
#pragma end region Assignments

std::string ccdb::SQLiteDataProvider::WilcardsToLike( const string& str )
{	
	//SQLite - wildcards
	//% - *
	//_ - ?

	//encode underscores
	string result = StringUtils::Replace("_", "\\_", str);

	//replace ? to _
	StringUtils::Replace("?","_",result, result);

	//replace * to %
	StringUtils::Replace("*","%",result, result);

	return result;
}

std::string ccdb::SQLiteDataProvider::PrepareCommentForInsert( const string& comment )
{
	// The idea is that we have to place 
	// (..., NULL) in INSERT queries if comment is NULL
	// and (..., "<content>") if it is not NULL
	// So this function returns string containing NULL or \"<comment content>\"
	

	if(comment.length() == 0)
	{
		// we put empty comments as NULL
		//because comments uses "TEXT" field that takes additional size
		// if text field in DB is NULL it will be read as "" by ReadString()
		// so it is safe to do this 
		
		return string("NULL");
	}
	else
	{
		string commentIns ="\"";
		commentIns.append(comment);
		commentIns.append("\"");
		return commentIns;
	}

}



#pragma region SQLite_Field_Operations

bool ccdb::SQLiteDataProvider::IsNullOrUnreadable( int fieldNum )
{
	// Checks if there is a value with this fieldNum index (reports error in such case)
	// and if it is not null (just returns false in this case)

	if(mQueryColumns<=fieldNum)
	{
		//Add error, we have less fields than fieldNum
		Error(CCDB_WARNING_DBRESULT_FIELD_INDEX,"SQLiteDataProvider::IsNullOrUnreadable", "we have less fields than fieldNum");
		return true;
	}

	return false;
}

int ccdb::SQLiteDataProvider::ReadInt( int fieldNum )
{	
	if(IsNullOrUnreadable(fieldNum)) return 0;

	return atoi((const char*)sqlite3_column_text(mStatement,fieldNum)); //ugly isn't it?
}

unsigned int ccdb::SQLiteDataProvider::ReadUInt( int fieldNum )
{	
	if(IsNullOrUnreadable(fieldNum)) return 0;

	return static_cast<unsigned int>(atoi((const char*)sqlite3_column_text(mStatement,fieldNum))); //ugly isn't it?
}

long ccdb::SQLiteDataProvider::ReadLong( int fieldNum )
{
	if(IsNullOrUnreadable(fieldNum)) return 0;

	return atol((const char*)sqlite3_column_text(mStatement,fieldNum)); //ugly isn't it?
}

unsigned long ccdb::SQLiteDataProvider::ReadULong( int fieldNum )
{
	if(IsNullOrUnreadable(fieldNum)) return 0;

	return static_cast<unsigned long>(atol((const char*)sqlite3_column_text(mStatement,fieldNum))); //ugly isn't it?
}

dbkey_t ccdb::SQLiteDataProvider::ReadIndex( int fieldNum )
{
	if(IsNullOrUnreadable(fieldNum)) return 0;

	return static_cast<dbkey_t>(atol((const char*)sqlite3_column_text(mStatement,fieldNum))); //ugly isn't it?
}

bool ccdb::SQLiteDataProvider::ReadBool( int fieldNum )
{
	if(IsNullOrUnreadable(fieldNum)) return false;

	return static_cast<bool>(atoi((const char*)sqlite3_column_text(mStatement,fieldNum))!=0); //ugly isn't it?
}

double ccdb::SQLiteDataProvider::ReadDouble( int fieldNum )
{
	if(IsNullOrUnreadable(fieldNum)) return 0;

	return atof((const char*)sqlite3_column_text(mStatement,fieldNum)); //ugly isn't it?
}

std::string ccdb::SQLiteDataProvider::ReadString( int fieldNum )
{
	if(IsNullOrUnreadable(fieldNum)) return string("");
	const char* str = (const char*)sqlite3_column_text(mStatement,fieldNum);
	if(!str)return string("");
	return string(str);
}


time_t ccdb::SQLiteDataProvider::ReadUnixTime( int fieldNum )
{	
	return static_cast<time_t>(ReadULong(fieldNum));
}

#pragma endregion SQLite_Field_Operations


#pragma region Queries

bool ccdb::SQLiteDataProvider::QueryPrepare(const char* query, const char *functionName)
{
	int result = sqlite3_prepare_v2(mDatabase, query, -1, &mStatement, 0);
	if( result )
	{
		ComposeSQLiteError(functionName);
		sqlite3_finalize(mStatement);
		return false;
	}
	return true;
}

#pragma endregion


#pragma region Fetch_free_and_other_SQLite_operations


void ccdb::SQLiteDataProvider::FreeSQLiteResult()
{
	sqlite3_free(mStatement);
}

std::string ccdb::SQLiteDataProvider::ComposeSQLiteError(const std::string& SQLiteFunctionName)
{
	string sqliteErr=StringUtils::Format("%s failed:\nError (%s)\n",SQLiteFunctionName.c_str(), sqlite3_errmsg(mDatabase));
	return sqliteErr;
}
#pragma endregion Fetch_free_and_other_SQLite_operations


std::string ccdb::SQLiteDataProvider::PrepareLimitInsertion(  int take/*=0*/, int startWith/*=0*/ )
{
	if(startWith != 0 && take != 0) return StringUtils::Format(" LIMIT %i, %i ", startWith, take);
	if(startWith != 0 && take == 0) return StringUtils::Format(" LIMIT %i, %i ", startWith, INFINITE_RUN);
	if(startWith == 0 && take != 0) return StringUtils::Format(" LIMIT %i ", take);
	
	return string(); //No LIMIT at all, if run point is here it corresponds to if(startWith == 0 && take ==0 )

}


int ccdb::SQLiteDataProvider::CountConstantsTypeTables(Directory *dir)
{
	/**
	 * @brief This function counts number of type tables for a given directory 
	 * @param [in] directory to look tables in
	 * @return number of tables to return
	 */
	return 0;
}

