#include <stdio.h>
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
#include "CCDB/Providers/MySQLDataProvider.h"
#include "CCDB/Model/ConstantsTypeTable.h"
#include "CCDB/Model/RunRange.h"

#ifdef __MACH__
#include <mach/clock.h>
#include <mach/mach.h>
#endif


using namespace ccdb;


#pragma region constructors

ccdb::MySQLDataProvider::MySQLDataProvider(void)
{
	mIsConnected = false;
	mMySQLHnd=NULL;
	mResult=NULL;
	mRootDir = new Directory(this, this);
	mDirsAreLoaded = false;
	mLastFullQuerry="";
	mLastShortQuerry="";
    mLastVariation = NULL; 
    
}


ccdb::MySQLDataProvider::~MySQLDataProvider(void)
{
	if(IsConnected())
	{
		Disconnect();
	}
}
#pragma endregion constructors

#pragma region Connection

bool ccdb::MySQLDataProvider::Connect( std::string connectionString )
{
	ClearErrors(); //Clear error in function that can produce new ones

	//Setting default connection	
	MySQLConnectionInfo connection;
	connection.UserName.assign(CCDB_DEFAULT_MYSQL_USERNAME);
	connection.Password.assign(CCDB_DEFAULT_MYSQL_PASSWORD);
	connection.HostName.assign(CCDB_DEFAULT_MYSQL_URL);
	connection.Database.assign(CCDB_DEFAULT_MYSQL_DATABASE);
	connection.Port	= CCDB_DEFAULT_MYSQL_PORT;

	//try to parse connection string
	if(!ParseConnectionString(connectionString, connection))
	{
		Error(CCDB_ERROR_PARSE_CONNECTION_STRING, "MySQLDataProvider::Connect()", "Error parse mysql string");
		return false;
	}
						
	//try to connect
    bool result = Connect(connection);
    if(result) mConnectionString = connectionString;
    return result;
}

bool ccdb::MySQLDataProvider::Connect(MySQLConnectionInfo connection)
{
	ClearErrors(); //Clear error in function that can produce new ones

	//check if we are connected
	if(IsConnected())
	{
		Error(CCDB_ERROR_CONNECTION_ALREADY_OPENED, "MySQLDataProvider::Connect(MySQLConnectionInfo)", "Connection already opened");
		return false;
	}


	//verbose...
	Log::Verbose("ccdb::MySQLDataProvider::Connect", StringUtils::Format("Connecting to database:\n UserName: %s \n Password: %i symbols \n HostName: %s Database: %s Port: %i",
					connection.UserName.c_str(), connection.Password.length(), connection.HostName.c_str(), connection.Database.c_str(), connection.Port) );
					
	//init connection variable
	if(mMySQLHnd == NULL)mMySQLHnd = mysql_init(NULL);
	if(mMySQLHnd == NULL)
	{
		Error(CCDB_ERROR_CONNECTION_INITIALIZATION, "MySQLDataProvider::Connect(DMySQLConnectionInfo)", "mysql_init() returned NULL, probably memory allocation problem");
		return false;
	}
	
	//Try to connect to server
	if(!mysql_real_connect (
		mMySQLHnd,						//pointer to connection handler
		connection.HostName.c_str(),	//host to connect to
		connection.UserName.c_str(),	//user name
		connection.Password.c_str(),	//password
		connection.Database.c_str(),	//database to use
		connection.Port, 				//port
		NULL,							//socket (use default)
		0))								//flags (none)
	{
		string errStr = ComposeMySQLError("mysql_real_connect()");
		Error(CCDB_ERROR_CONNECTION_EXTERNAL_ERROR,"bool MySQLDataProvider::Connect(MySQLConnectionInfo)",errStr.c_str());

		mMySQLHnd=NULL;		//some compilers dont set NULL after delete
		return false;
	}
	mIsConnected = true;
	return true;
}

bool ccdb::MySQLDataProvider::ParseConnectionString(std::string conStr, MySQLConnectionInfo &connection)
{
	//first check for uri type
	int typePos = conStr.find("mysql://");
	if(typePos==string::npos)
	{
		return false;
	}

	//ok we dont need mysql:// in the future. Moreover it will mess our separation logic
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

	return true;
}


bool ccdb::MySQLDataProvider::IsConnected()
{
	return mIsConnected;
}


void ccdb::MySQLDataProvider::Disconnect()
{
	if(IsConnected())
	{
		FreeMySQLResult();	//it would free the result or do nothing
		
		mysql_close(mMySQLHnd);
		mMySQLHnd = NULL;
		mIsConnected = false;
	}
}


bool ccdb::MySQLDataProvider::CheckConnection( const string& errorSource/*=""*/ )
{
	ClearErrors(); //Clear error in function that can produce new ones

	//check connection
	if(!IsConnected())
	{
		Error(CCDB_ERROR_NOT_CONNECTED,errorSource.c_str(), "Provider is not connected to MySQL.");
		return false;
	}
	return true;
}
#pragma endregion Connection

#pragma region Directories



Directory* ccdb::MySQLDataProvider::GetDirectory( const string& path )
{
	return DataProvider::GetDirectory(path);
}


bool ccdb::MySQLDataProvider::SearchDirectories( vector<Directory *>& resultDirectories, const string& searchPattern, const string& parentPath/*=""*/,  int take/*=0*/, int startWith/*=0*/ )
{	
	UpdateDirectoriesIfNeeded(); //do we need to update directories?

	resultDirectories.clear();

	// in MYSQL compared to wildcards % is * and _ is 
	// convert it. 
	string likePattern = WilcardsToLike(searchPattern);
	
	//do we need to search only in specific directory?
	string parentAddon(""); //this addition is to query right parent directory
	if(parentPath!="")
	{	//we should care about parent path
		
		//If parent directory is "/" this should work too, because it have an id=0
		//and tables in db which doesn't have parents should have parentId=0
		
		Directory *parentDir;
		if( (parentDir = GetDirectory(parentPath.c_str())) )
		{
			parentAddon = StringUtils::Format(" AND `parentId` = '%i'", parentDir->GetId());
		}
		else
		{
			//request was made for directory that doesn't exists
			//TODO place warning or not?
			return false;
		}
	}

	string limitAddon = PrepareLimitInsertion(take, startWith);

	//combine query
	string query = StringUtils::Format("SELECT `id` FROM `directories` WHERE name LIKE \"%s\" %s %s;",
		likePattern.c_str(), parentAddon.c_str(), limitAddon.c_str());
	
	//do query!
	if(!QuerySelect(query))
	{
		return false;
	}
	
	//Ok! We queried our directories! lets catch them! 
	while(FetchRow())
	{
		dbkey_t id = ReadIndex(0); //read db index key

		//search for such index
		map<dbkey_t,Directory *>::iterator dirIter = mDirectoriesById.find(id);
		if(dirIter != mDirectoriesById.end())
		{
			resultDirectories.push_back(dirIter->second);
		}
		else
		{
			//TODO it is some error situation! It cant happend!
		}
	}

	FreeMySQLResult();

	return true;
}

bool ccdb::MySQLDataProvider::LoadDirectories()
{
	//
	if(IsConnected())
	{
		if(!QuerySelect("SELECT `id`, `name`, `parentId`, UNIX_TIMESTAMP(`directories`.`modified`) as `updateTime`, `comment` FROM `directories`"))
		{
			//TODO: report error
			return false;
		}

		//clear diretory arrays
		mDirectories.clear();
		mDirectoriesById.clear();

		//clear root directory (delete all directory structure objects)
		mRootDir->DisposeSubdirectories(); 
		mRootDir->SetFullPath("/");

		//Ok! We querryed our directories! lets catch them! 
		while(FetchRow())
		{
			Directory *dir = new Directory(this, this);
			dir->SetId(ReadIndex(0));					// `id`, 
			dir->SetName(ReadString(1));			// `name`, 
			dir->SetParentId(ReadInt(2));			// `parentId`, 
			dir->SetModifiedTime(ReadUnixTime(3));	// UNIX_TIMESTAMP(`directories`.`updateTime`) as `updateTime`, 
			dir->SetComment(ReadString(4));			// `comment`

			mDirectories.push_back(dir);
			mDirectoriesById[dir->GetId()] = dir;
		}

		BuildDirectoryDependencies(); //

		mDirsAreLoaded=true;
	}
	return false;
}


//______________________________________________________________________________
vector<Directory *> ccdb::MySQLDataProvider::SearchDirectories( const string& searchPattern, const string& parentPath/*=""*/, int startWith/*=0*/, int select/*=0*/ )
{
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

	return DataProvider::SearchDirectories(searchPattern, parentPath, startWith, select);
}

#pragma endregion Directories


#pragma region ObjectOwnerMethods

bool ccdb::MySQLDataProvider::IsStoredObjectsOwner()
{
	return mIsStoredObjectOwner;
}


void ccdb::MySQLDataProvider::IsStoredObjectsOwner(bool flag)
{
	mIsStoredObjectOwner = flag;
}

#pragma endregion ObjectOwnerMethods

#pragma region Type Tables
ConstantsTypeTable * ccdb::MySQLDataProvider::GetConstantsTypeTable( const string& name, Directory *parentDir,bool loadColumns/*=false*/ )
{
	ClearErrors(); //Clear error in function that can produce new ones

	//check the directory is ok
	if(parentDir == NULL || parentDir->GetId()<=0)
	{
		//error
		Error(CCDB_ERROR_NO_PARENT_DIRECTORY,"MySQLDataProvider::GetConstantsTypeTable", "Parent directory is null or have invalid ID");
		return NULL;
	}

	//check connection
	if(!IsConnected())
	{
		//error !not connect
		Error(CCDB_ERROR_NOT_CONNECTED,"MySQLDataProvider::GetConstantsTypeTable", "Provider is not connected to MySQL.");
		return NULL;
	}
	
	string query = StringUtils::Format("SELECT `id`, UNIX_TIMESTAMP(`created`) as `created`, UNIX_TIMESTAMP(`modified`) as `modified`, `name`, `directoryId`, `nRows`, `nColumns`, `comment` FROM `typeTables` WHERE `name` = '%s' AND `directoryId` = '%i';",
		 /*`name`*/ name.c_str(),
		 /*`directoryId`*/ parentDir->GetId());

	if(!QuerySelect(query))
	{
		//TODO: report error
		return NULL;
	}

	
	//Ok! We querryed our directories! lets catch them! 
	if(!FetchRow())
	{
		//TODO error not selected
		return NULL;
	}

	//ok lets read the data...
	ConstantsTypeTable *result = new ConstantsTypeTable(this, this);
	result->SetId(ReadULong(0));
	result->SetCreatedTime(ReadUnixTime(1));
	result->SetModifiedTime(ReadUnixTime(2));
	result->SetName(ReadString(3));
	result->SetDirectoryId(ReadULong(4));
	result->SetNRows(ReadInt(5));
	result->SetNColumnsFromDB(ReadInt(6));
	result->SetComment(ReadString(7));
	
	SetObjectLoaded(result); //set object flags that it was just loaded from DB
	
	result->SetDirectory(parentDir);

	//some validation of loaded record...
	if(result->GetName() == "")
	{
		//TODO error, name should be not null and not empty
		Error(CCDB_ERROR_TYPETABLE_HAS_NO_NAME,"MySQLDataProvider::GetConstantsTypeTable", "");
		delete result;
		return NULL;
	}
	
	//Ok set a full path for this constant...
	result->SetFullPath(PathUtils::CombinePath(parentDir->GetFullPath(), result->GetName()));

	
	FreeMySQLResult();
	
	//load columns if needed
	if(loadColumns) LoadColumns(result);
        

	return result;
}

//______________________________________________________________________________
ConstantsTypeTable * ccdb::MySQLDataProvider::GetConstantsTypeTable(const string& path, bool loadColumns/*=false*/ )
{
	return DataProvider::GetConstantsTypeTable(path, loadColumns);
}


bool ccdb::MySQLDataProvider::GetConstantsTypeTables( vector<ConstantsTypeTable *>& resultTypeTables, const string&  parentDirPath, bool loadColumns/*=false*/ )
{
	//and directory
	Directory *dir = GetDirectory(parentDirPath);

	//probably one may wish to check dir to be !=NULL,
	//but such check is in GetConstantsTypeHeaders( DDirectory *parentDir, vector<ConstantsTypeTable *>& consts );
	return GetConstantsTypeTables(resultTypeTables, dir);
}


bool ccdb::MySQLDataProvider::GetConstantsTypeTables(  vector<ConstantsTypeTable *>& resultTypeTables, Directory *parentDir, bool loadColumns/*=false*/)
{
	ClearErrors(); //Clear error in function that can produce new ones

	//check the directory is ok
	if((parentDir == NULL || parentDir->GetId()<=0) && (parentDir!=mRootDir))
	{
		//TODO error
		Error(CCDB_ERROR_NO_PARENT_DIRECTORY,"MySQLDataProvider::GetConstantsTypeTables", "Parent directory is null or has invald ID");
		return false;
	}
	
	//Ok, lets cleanup result list
		resultTypeTables.clear(); //we clear the consts. Considering that some one else should handle deletion

	string query = StringUtils::Format("SELECT `id`, UNIX_TIMESTAMP(`created`) as `created`, UNIX_TIMESTAMP(`modified`) as `modified`, `name`, `directoryId`, `nRows`, `nColumns`, `comment` FROM `typeTables` WHERE `directoryId` = '%i';",
		/*`directoryId`*/ parentDir->GetId());

	if(!QuerySelect(query))
	{
		//no report error
		return false;
	}

	//Ok! We querryed our directories! lets catch them! 
	while(FetchRow())
	{
		//ok lets read the data...
		ConstantsTypeTable *result = new ConstantsTypeTable(this, this);
		result->SetId(ReadIndex(0));
		result->SetCreatedTime(ReadUnixTime(1));
		result->SetModifiedTime(ReadUnixTime(2));
		result->SetName(ReadString(3));
		result->SetDirectoryId(ReadULong(4));
		result->SetNRows(ReadInt(5));
		result->SetNColumnsFromDB(ReadInt(6));
		result->SetComment(ReadString(7));
		
		if(loadColumns) LoadColumns(result);
		result->SetDirectory(parentDir);
		
		SetObjectLoaded(result); //set object flags that it was just loaded from DB
		resultTypeTables.push_back(result);
	}

	FreeMySQLResult();

	return true;
}


vector<ConstantsTypeTable *> ccdb::MySQLDataProvider::GetConstantsTypeTables( const string& parentDirPath, bool loadColumns/*=false*/ )
{
	vector<ConstantsTypeTable *> tables;
	GetConstantsTypeTables(tables, parentDirPath, loadColumns);
	return tables;
}


vector<ConstantsTypeTable *> ccdb::MySQLDataProvider::GetConstantsTypeTables( Directory *parentDir, bool loadColumns/*=false*/ )
{
	
		vector<ConstantsTypeTable *> tables;
		GetConstantsTypeTables(tables, parentDir, loadColumns);
		return tables;
	
}



bool ccdb::MySQLDataProvider::SearchConstantsTypeTables( vector<ConstantsTypeTable *>& typeTables, const string& pattern, const string& parentPath /*= ""*/, bool loadColumns/*=false*/, int take/*=0*/, int startWith/*=0 */ )
{
	ClearErrors(); //Clear error in function that can produce new ones

	// in MYSQL compared to wildcards % is * and _ is 
	// convert it. 
	string likePattern = WilcardsToLike(pattern);
    
	//do we need to search only in specific directory?
	string parentAddon("");         //this addition is to query with right parent directory
	Directory *parentDir = NULL;    //we will need it later anyway
	if(parentPath!="")
	{	
        //we must take care of parent path!
        if((parentDir = GetDirectory(parentPath.c_str())))
        {
            parentAddon = StringUtils::Format(" AND `directoryId` = '%i'", parentDir->GetId());
        }
        else
        {
            //request was made for directory that doesn't exits
            //TODO place warning or not?
            Error(CCDB_ERROR_DIRECTORY_NOT_FOUND,"MySQLDataProvider::SearchConstantsTypeTables", "Path to search is not found");
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
	string query = StringUtils::Format("SELECT `id`, UNIX_TIMESTAMP(`created`) as `created`, UNIX_TIMESTAMP(`modified`) as `modified`, `name`, `directoryId`, `nRows`, `nColumns`, `comment` FROM `typeTables` WHERE `name` LIKE '%s' %s ORDER BY `name` %s;",
		likePattern.c_str(), parentAddon.c_str(), limitAddon.c_str());
        
	if(!QuerySelect(query))
	{
		//no report error
		return false;
	}

    
	//Ok! We queried our directories! lets catch them! 
	while(FetchRow())
	{
		//ok lets read the data...
		ConstantsTypeTable *result = new ConstantsTypeTable(this, this);

		result->SetId(ReadULong(0));
		result->SetCreatedTime(ReadUnixTime(1));
		result->SetModifiedTime(ReadUnixTime(2));
		result->SetName(ReadString(3));
		result->SetDirectoryId(ReadULong(4));
		result->SetNRows(ReadInt(5));
		result->SetNColumnsFromDB(ReadInt(6));
		result->SetComment(ReadString(7));

        if(parentDir) //we already may have parrent directory
        {
		    result->SetDirectory(parentDir);
        }
        else //Or we should find it...
        {
            result->SetDirectory(mDirectoriesById[result->GetDirectoryId()]);
        }

		SetObjectLoaded(result); //set object flags that it was just loaded from DB
		
		typeTables.push_back(result);
	}

    //Load COLUMNS if needed...
	if(loadColumns)
    {
        for (int i=0; i< typeTables.size(); i++)
        {
            LoadColumns(typeTables[i]);
        }   
    }
    
	FreeMySQLResult();
	
	return true;
}


std::vector<ConstantsTypeTable *> ccdb::MySQLDataProvider::SearchConstantsTypeTables( const string& pattern, const string& parentPath /*= ""*/, bool loadColumns/*=false*/, int take/*=0*/, int startWith/*=0 */ )
{
	std::vector<ConstantsTypeTable *> tables;
	SearchConstantsTypeTables(tables, pattern, parentPath,loadColumns, take, startWith);
	return tables;
}

bool ccdb::MySQLDataProvider::LoadColumns( ConstantsTypeTable* table )
{
	ClearErrors(); //Clear error in function that can produce new ones

	//check the directory is ok
	if(table->GetId()<=0)
	{
		//TODO error
		Error(CCDB_ERROR_INVALID_ID,"MySQLDataProvider::LoadColumns", "Type table has wrong ID");
		return false;
	}
		
	string query = StringUtils::Format("SELECT `id`, UNIX_TIMESTAMP(`created`) as `created`, UNIX_TIMESTAMP(`modified`) as `modified`, `name`, `columnType`, `comment` FROM `columns` WHERE `typeId` = '%i' ORDER BY `order`;",
		/*`directoryId`*/ table->GetId());

	if(!QuerySelect(query))
	{
		return false;
	}

	//clear(); //we clear the consts. Considering that some one else should handle deletion

	//Ok! We querried our directories! lets catch them! 
	while(FetchRow())
	{
		//ok lets read the data...
		ConstantsTypeColumn *result = new ConstantsTypeColumn(table, this);
		result->SetId(ReadULong(0));				
		result->SetCreatedTime(ReadUnixTime(1));
		result->SetModifiedTime(ReadUnixTime(2));
		result->SetName(ReadString(3));
		result->SetType(ReadString(4));
		result->SetComment(ReadString(5));
		result->SetDBTypeTableId(table->GetId());

		SetObjectLoaded(result); //set object flags that it was just loaded from DB

		table->AddColumn(result);
	}

	FreeMySQLResult();

	return true;
}
#pragma endregion Type Tables

#pragma region Run ranges



RunRange* ccdb::MySQLDataProvider::GetRunRange( int min, int max, const string& name /*= ""*/ )
{
	//build query
	string query = "SELECT `id`, UNIX_TIMESTAMP(`created`) as `created`, UNIX_TIMESTAMP(`modified`) as `modified`, `name`, `runMin`, `runMax`,  `comment`"
	               " FROM `runRanges` WHERE `runMin`='%i' AND `runMax`='%i' AND `name`=\"%s\"";
	query = StringUtils::Format(query.c_str(), min, max, name.c_str());
	
	//query this
	if(!QuerySelect(query))
	{
		//NO report error
		return NULL;
	}
	
	//Ok! We queried our run range! lets catch it! 
	
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
		//TODO warning not uniq row
		Error(CCDB_ERROR,"MySQLDataProvider::GetRunRange", "Run range with such min, max and name is not alone in the DB");
	}

	FreeMySQLResult();
	return result;
}


RunRange* ccdb::MySQLDataProvider::GetRunRange( const string& name )
{
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
		Error(CCDB_ERROR,"MySQLDataProvider::GetRunRange", "Run range with such name is not alone in the DB");
	}

	FreeMySQLResult();
	return result;
}


bool ccdb::MySQLDataProvider::GetRunRanges(vector<RunRange*>& resultRunRanges, ConstantsTypeTable* table, const string& variation/*=""*/, int take/*=0*/, int startWith/*=0*/)
{
	ClearErrors(); //Clear error in function that can produce new ones

	if(!CheckConnection("MySQLDataProvider::GetRunRanges(vector<DRunRange*>& resultRunRanges, ConstantsTypeTable* table, int take, int startWith)")) return false;
	
	//validate table
	if(!table || !table->GetId())
	{
		//TODO report error
		Error(CCDB_ERROR_NO_TYPETABLE,"MySQLDataProvider::GetRunRanges", "Type table is null or have invalid id");
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

	FreeMySQLResult();
	return true;
}



#pragma endregion Run ranges

#pragma region Variations

bool ccdb::MySQLDataProvider::GetVariations(vector<Variation*>& resultVariations, ConstantsTypeTable* table, int run, int take, int startWith)
{
	ClearErrors(); //Clear error in function that can produce new ones

	if(!CheckConnection("MySQLDataProvider::GetRunRanges(vector<DRunRange*>& resultRunRanges, ConstantsTypeTable* table, int take, int startWith)")) return false;
	
	//validate table
	if(!table || !table->GetId())
	{
		//TODO report error
		Error(CCDB_ERROR_NO_TYPETABLE,"MySQLDataProvider::GetVariations", "Type table is null or empty");
		return false;
	}
	
	//run range handle
	string runRangeWhere(""); //Where clause for run range
	if(run != 0)
	{		
		runRangeWhere = StringUtils::Format(" AND `runRanges`.`runMin` <= '%i' AND `runRanges`.`runMax` >= '%i' ", run, run);
	}

	//limits handle 
	string limitInsertion = PrepareLimitInsertion(take, startWith);
	
	//Ok, lets cleanup result list
	if(resultVariations.size()>0)
	{
		vector<Variation *>::iterator iter = resultVariations.begin();
		while(iter != resultVariations.end())
		{
			Variation *obj = *iter;
			if(IsOwner(obj)) delete obj;		//delete objects if this provider is owner
			iter++;
		}
	}
	resultVariations.clear(); //we clear the consts. Considering that some one else should handle deletion


	//ok now we must build our mighty query...
	string query= 
		" SELECT "
		" DISTINCT `variations`.`id` as `varId`, "
		" UNIX_TIMESTAMP(`variations`.`created`) as `created`, "
		" UNIX_TIMESTAMP(`variations`.`modified`) as `modified`, "
		" `variations`.`name` as `name`, "
		" `variations`.`description` as `description`, "
		" `variations`.`comment` as `comment` "
		" FROM `runRanges` "
		" INNER JOIN `assignments`  ON `assignments`.`runRangeId`= `runRanges`.`id` "
		" INNER JOIN `variations`   ON `assignments`.`variationId`= `variations`.`id` "
		" INNER JOIN `constantSets` ON `assignments`.`constantSetId` = `constantSets`.`id` "
		" INNER JOIN `typeTables`   ON `constantSets`.`constantTypeId` = `typeTables`.`id` "
		" WHERE `typeTables`.`id` = '%i' "
		" %s "
		" ORDER BY `runRanges`.`runMin` ASC	 %s";
		
	query=StringUtils::Format(query.c_str(), table->GetId(), runRangeWhere.c_str(), limitInsertion.c_str());
	
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
		Variation *result = new Variation(this, this);
		result->SetId(ReadULong(0));
		result->SetCreatedTime(ReadUnixTime(1));
		result->SetModifiedTime(ReadUnixTime(2));
		result->SetName(ReadString(3));
		result->SetDescription(ReadString(4));
		result->SetComment(ReadString(5));
		
		SetObjectLoaded(result);
		resultVariations.push_back(result);
	}

	FreeMySQLResult();
	return true;
}

vector<Variation *> ccdb::MySQLDataProvider::GetVariations( ConstantsTypeTable *table, int run/*=0*/, int take/*=0*/, int startWith/*=0 */ )
{
	vector<Variation *> resultVariations;
	GetVariations(resultVariations, table, run, take, startWith);
	return resultVariations;
}


Variation* ccdb::MySQLDataProvider::GetVariation( const string& name )
{
	ClearErrors(); //Clear error in function that can produce new ones
    if(mLastVariation!=NULL && mLastVariation->GetName()==name) return mLastVariation;

    return SelectVariation("`name`= \"" + name + "\"");
}

/** @brief Load variation by name
* 
* @param     const char * name
* @return   DVariation*
*/
Variation* ccdb::MySQLDataProvider::GetVariationById(int id)
{
    if(mVariationsById.find(id) != mVariationsById.end()) return mVariationsById[id];
    
    ClearErrors(); //Clear error in function that can produce new ones
    return SelectVariation("`id`= " + StringUtils::IntToString(id) + "");
}

/**
* Get variation by database request
*/
Variation* ccdb::MySQLDataProvider::SelectVariation(const string& whereClause)
{
    //TODO: Implement method
    string query = "SELECT `id`, UNIX_TIMESTAMP(`created`) as `created`, UNIX_TIMESTAMP(`modified`) as `modified`, `name`, `description`, `comment`, `parentId`"
        " FROM `variations` WHERE "+whereClause+";";

    //query this
    if(!QuerySelect(query))
    {
        //TODO report error
        return NULL;
    }

    //Ok! We queried our run range! lets catch it! 
    if(!FetchRow())
    {
        //nothing was selected
        return NULL;
    }

    //ok lets read the data...
    Variation *result = new Variation(this, this);
    result->SetId(ReadULong(0));
    result->SetCreatedTime(ReadUnixTime(1));
    result->SetModifiedTime(ReadUnixTime(2));
    result->SetName(ReadString(3));
    result->SetDescription(ReadString(4));
    result->SetComment(ReadString(5));
    result->SetParentDbId(ReadULong(6));

    if(mReturnedRowsNum>1)
    {
        //TODO warning not uniq row
    }

    result->SetOwner(this, true);

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


#pragma endregion Variations

//----------------------------------------------------------------------------------------
//	A S S I G N M E N T S
//----------------------------------------------------------------------------------------

#pragma region Assignment
Assignment* ccdb::MySQLDataProvider::GetAssignmentShort(int run, const string& path, const string& variationName, bool loadColumns /*=false*/)
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
    return GetAssignmentShort(run, path, 0, variationName, loadColumns);
}


Assignment* ccdb::MySQLDataProvider::GetAssignmentShort(int run, const string& path, time_t time, const string& variationName, bool loadColumns /*=false*/)
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

	ClearErrors(); //Clear error in function that can produce new ones

	if(!CheckConnection("MySQLDataProvider::GetAssignmentShort( int run, const char* path, const char* variation, int version /*= -1*/ )")) return NULL;
	        
    //Get directory. Directories should be cached. So this doesn't make a database request
    
    ConstantsTypeTable *table = GetConstantsTypeTable(path, loadColumns);
    if(!table)
    {
        Error(CCDB_ERROR_NO_TYPETABLE, "MySQLDataProvider::GetAssignmentShort", "Type table was not found: '"+path+"'" );
        return NULL;
    }

    //retrieve name of our constant table 
    string tableName = PathUtils::ExtractObjectname(path);

    //get variation
    Variation* variation = GetVariation(variationName);
    if(!variation)
    {
        Error(CCDB_ERROR_VARIATION_INVALID,"MySQLDataProvider::GetAssignmentShort", "No variation '"+variationName+"' was found");
        return NULL;
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
		//TODO report error
		return NULL;
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
		Error(CCDB_ERROR_NO_ASSIGMENT,"MySQLDataProvider::GetAssignmentShort(int, const string&, time_t, const string&)", 
            StringUtils::Format("No data was selected. Table '%s' for run='%i', timestampt='%lu' and variation='%s' ", path.c_str(), run, time, variationName.c_str()));
		return NULL;
	}

	//ok lets read the data...
	Assignment *result = new Assignment(this, this);
	result->SetId( ReadIndex(0) );
	result->SetRawData( ReadString(1) );
	
	//additional fill
	result->SetRequestedRun(run);
	result->SetVariationId(variation->GetId());
	
    //type table
    result->SetTypeTable(table);
    result->BeOwner(table);
    table->SetOwner(result);

	if(mReturnedRowsNum>1)
	{
		//TODO warning not uniq row
	}

	FreeMySQLResult();
	return result;

}

Assignment* ccdb::MySQLDataProvider::GetAssignmentFull( int run, const string& path, const string& variation )
{
	if(!CheckConnection("MySQLDataProvider::GetAssignmentFull(int run, cconst string& path, const string& variation")) return NULL;
	return DataProvider::GetAssignmentFull(run, path, variation);
}

Assignment* ccdb::MySQLDataProvider::GetAssignmentFull( int run, const string& path,int version, const string& variation/*= "default"*/)
{
	if(!CheckConnection("MySQLDataProvider::GetAssignmentFull( int run, const char* path, const char* variation, int version /*= -1*/ )")) return NULL;
	return DataProvider::GetAssignmentFull(run, path, variation);
}


bool ccdb::MySQLDataProvider::GetAssignments( vector<Assignment *> &assingments,const string& path, int runMin, int runMax, const string& runRangeName, const string& variation, time_t beginTime, time_t endTime, int sortBy/*=0*/,  int take/*=0*/, int startWith/*=0*/ )
{
	ClearErrors(); //Clear error in function that can produce new ones

	if(!CheckConnection("MySQLDataProvider::GetAssignments( ... )")) return false;

	//get table! 
	ConstantsTypeTable *table = GetConstantsTypeTable(path, true);
	if(!table)
	{
		//TODO report error
		Error(CCDB_ERROR_NO_TYPETABLE,"MySQLDataProvider::GetAssignments", "Type table was not found");
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
	/*01*/  " UNIX_TIMESTAMP(`assignments`.`created`) as `asCreated`,"
	/*02*/  " UNIX_TIMESTAMP(`assignments`.`modified`) as `asModified`,	"
	/*03*/  " `assignments`.`comment` as `asComment`, "
	/*04*/  " `constantSets`.`id` AS `constId`, "
	/*05*/  " `constantSets`.`vault` AS `blob`, "
	/*06*/  " `runRanges`.`id`   AS `rrId`, "
	/*07*/  " UNIX_TIMESTAMP(`runRanges`.`created`) as `rrCreated`,"
	/*08*/  " UNIX_TIMESTAMP(`runRanges`.`modified`) as `rrModified`,	"
	/*09*/  " `runRanges`.`name`   AS `rrName`, "
	/*10*/  " `runRanges`.`runMin`   AS `rrMin`, "
	/*11*/  " `runRanges`.`runMax`   AS `runMax`, "
	/*12*/  " `runRanges`.`comment` as `rrComment`, "
	/*13*/  " `variations`.`id`  AS `varId`, "
	/*14*/  " UNIX_TIMESTAMP(`variations`.`created`) as `varCreated`,"
	/*15*/  " UNIX_TIMESTAMP(`variations`.`modified`) as `varModified`,	"
	/*16*/  " `variations`.`name` AS `varName`, "
	/*17*/  " `variations`.`comment`  AS `varComment` "
		    " FROM `runRanges` "
		    " INNER JOIN `assignments` ON `assignments`.`runRangeId`= `runRanges`.`id`"
		    " INNER JOIN `variations` ON `assignments`.`variationId`= `variations`.`id`	"
		    " INNER JOIN `constantSets` ON `assignments`.`constantSetId` = `constantSets`.`id`"
		    " INNER JOIN `typeTables` ON `constantSets`.`constantTypeId` = `typeTables`.`id`"
		    " WHERE  `typeTables`.`id` = '%i' %s %s %s %s %s";


	query=StringUtils::Format(query.c_str(), table->GetId(), runRangeWhere.c_str(), variationWhere.c_str(), timeWhere.c_str(), orderByInsertion.c_str(), limitInsertion.c_str());
	//query this
	if(!QuerySelect(query))
	{
		//TODO report error
		return false;
	}

	//Ok! We querried our run range! lets catch it! 
	while(FetchRow())
	{
		assingments.push_back(FetchAssignment(table));
		
	}

	FreeMySQLResult();
	
	return true;
}

bool ccdb::MySQLDataProvider::GetAssignments(vector<Assignment*>& assingments, const string& path, int run, const string& variation, time_t date, int take, int startWith)
{
	return GetAssignments(assingments, path, run, run,"",variation, 0, date, take, startWith);
}

vector<Assignment *> ccdb::MySQLDataProvider::GetAssignments( const string& path, int run, const string& variation/*=""*/, time_t date/*=0*/, int take/*=0*/, int startWith/*=0*/ )
{
	vector<Assignment *> assingments;
	GetAssignments(assingments, path, run,variation, date, take, startWith);
	return assingments;
}

bool ccdb::MySQLDataProvider::GetAssignments( vector<Assignment *> &assingments,const string& path, const string& runName, const string& variation/*=""*/, time_t date/*=0*/, int take/*=0*/, int startWith/*=0*/ )
{
	return GetAssignments(assingments, path, 0, 0,runName,variation, 0, date, take, startWith);
}

vector<Assignment *> ccdb::MySQLDataProvider::GetAssignments( const string& path, const string& runName, const string& variation/*=""*/, time_t date/*=0*/, int take/*=0*/, int startWith/*=0*/ )
{
	vector<Assignment *> assingments;
	GetAssignments(assingments, path, runName,variation, date, take, startWith);
	return assingments;
}



bool ccdb::MySQLDataProvider::FillAssignment(Assignment* assignment)
{
	ClearErrors(); //Clear error in function that can produce new ones
	if(assignment == NULL || !assignment->GetId())
	{
		//TODO report errors
		Error(CCDB_ERROR_ASSIGMENT_INVALID,"MySQLDataProvider::FillAssignment", "ASSIGnMENt is NULL or has improper ID so update operations cant be done");
		return false;
	}
	
	//ok now we must build our mighty query...
	string query=
	/*fieldN*/  " SELECT "
	/*00*/  " `assignments`.`id` AS `asId`,	"
	/*01*/  " UNIX_TIMESTAMP(`assignments`.`created`) as `asCreated`,"
	/*02*/  " UNIX_TIMESTAMP(`assignments`.`modified`) as `asModified`,	"
	/*03*/  " `assignments`.`comment` as `asComment`, "
	/*04*/  " `constantSets`.`id` AS `constId`, "
	/*05*/  " `constantSets`.`vault` AS `blob`, "
	/*06*/  " `runRanges`.`id`   AS `rrId`, "
	/*07*/  " UNIX_TIMESTAMP(`runRanges`.`created`) as `rrCreated`,"
	/*08*/  " UNIX_TIMESTAMP(`runRanges`.`modified`) as `rrModified`,	"
	/*09*/  " `runRanges`.`name`   AS `rrName`, "
	/*10*/  " `runRanges`.`runMin`   AS `rrMin`, "
	/*11*/  " `runRanges`.`runMax`   AS `runMax`, "
	/*12*/  " `runRanges`.`comment` as `rrComment`, "
	/*13*/  " `variations`.`id`  AS `varId`, "
	/*14*/  " UNIX_TIMESTAMP(`variations`.`created`) as `varCreated`,"
	/*15*/  " UNIX_TIMESTAMP(`variations`.`modified`) as `varModified`,	"
	/*16*/  " `variations`.`name` AS `varName`, "
	/*17*/  " `variations`.`comment`  AS `varComment`, "
	/*18*/  " `typeTables`.`name` AS `typeTableName`, "
	/*19*/  " `directories`.`id` AS `dirId` "
		    " FROM `runRanges` "
		    " INNER JOIN `assignments` ON `assignments`.`runRangeId`= `runRanges`.`id`"
		    " INNER JOIN `variations` ON `assignments`.`variationId`= `variations`.`id`	"
		    " INNER JOIN `constantSets` ON `assignments`.`constantSetId` = `constantSets`.`id`"
		    " INNER JOIN `typeTables` ON `constantSets`.`constantTypeId` = `typeTables`.`id`"
			" INNER JOIN `directories` ON `typeTables`.`directoryId` = `directories`.`id`"
		    " WHERE  `assignments`.`id` = '%i'";
	
	
	query=StringUtils::Format(query.c_str(), assignment->GetId());
	//cout << query<<endl;
	//query this
	if(!QuerySelect(query))
	{
		//TODO report error
		cout<<"!QuerySelect(query)"<<endl;
		return false;
	}
	
	if(!FetchRow())
	{
		//TODO report error
		cout<<"no assignment selected!"<<endl;
		return false;
	}
	
	//fetch readed row
	FetchAssignment(assignment, assignment->GetTypeTable());
	
	//Ok! Here is a tricky moment. We should load a constant type table 
	//but we have an API that allows us to load such directories by name
	//The problem that we should know a full path of it. 
	//So we pulled a directory ID and data table name. 
	// We have a list of directories by their ID thus we will know a full path
	// of type table. 
	// lets make this plan work
	
	string typeTableName = ReadString(18);
	dbkey_t directoryId = ReadIndex(19);
	
	//maybe we need to update our directories?
	UpdateDirectoriesIfNeeded();

	if(mDirectoriesById.find(directoryId) == mDirectoriesById.end())
	{
		//TODO report errors
		Error(CCDB_ERROR,"MySQLDataProvider::FillAssignment", "Cannot find directory locally by ID taken from database");
		return false;
	}

	Directory *parent = mDirectoriesById[directoryId];
	
	ConstantsTypeTable * table = GetConstantsTypeTable(typeTableName, parent, true);
	if(!table)
	{
		Error(CCDB_ERROR_NO_TYPETABLE,"MySQLDataProvider::FillAssignment", "Type table was not loaded");
		return false;
	}

	assignment->SetTypeTable(table);
	table->SetOwner(assignment);

	FreeMySQLResult();
	
	return true;
}

Assignment* ccdb::MySQLDataProvider::FetchAssignment(ConstantsTypeTable* table)
{
	Assignment * assignment = new Assignment(this, this); //it is our victim

	FetchAssignment(assignment, table);

	//take it!
	return assignment;
}


void ccdb::MySQLDataProvider::FetchAssignment(Assignment* assignment, ConstantsTypeTable* table)
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

#pragma endregion Assignment

#pragma region Misc

std::string ccdb::MySQLDataProvider::WilcardsToLike( const string& str )
{	
	//MySQL - wildcards
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

std::string ccdb::MySQLDataProvider::PrepareCommentForInsert( const string& comment )
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

#pragma endregion Misc

#pragma region MySQL_Field_Operations

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

	if(mRow[fieldNum]==NULL) 
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
	if(!CheckConnection("MySQLDataProvider::QuerySelect")) return false;
	
	//do we have some results we need to free?
	if(mResult!=NULL)
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

bool ccdb::MySQLDataProvider::QueryCustom( const string& query )
{
	if(!CheckConnection("MySQLDataProvider::QueryCustom")) return false;

	//do we have some results we need to free?
	if(mResult!=NULL)
	{	
		FreeMySQLResult();
	}
	//query
	if(mysql_query(mMySQLHnd, query.c_str()))
	{
		string errStr = ComposeMySQLError("mysql_query()"); errStr.append("\n Query: "); errStr.append(query);
		Error(CCDB_ERROR_MYSQL_CUSTOM_QUERY,"ccdb::MySQLDataProvider::QueryCustom( string query )",errStr.c_str());
		return false;
	}
	return true;
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
	mResult = NULL;
}

std::string ccdb::MySQLDataProvider::ComposeMySQLError(std::string mySqlFunctionName)
{
	string mysqlErr=StringUtils::Format("%s failed:\nError %u (%s)\n",mySqlFunctionName.c_str(), mysql_errno(mMySQLHnd), mysql_error (mMySQLHnd));
	return mysqlErr;
}
#pragma endregion Fetch_free_and_other_MySQL_operations



dbkey_t ccdb::MySQLDataProvider::GetUserId( string userName )
{
	if(userName == "" || !ValidateName(userName))
	{
		return 1; //anonymous id
	}

	string query = StringUtils::Format("SELECT `id` FROM `authors` WHERE `name` = \"%s\" LIMIT 0,1", userName.c_str());
	if(!QuerySelect(query))
	{
		return 1; //anonymous id
	}


	if(!FetchRow())
	{
		return 1; //anonymous id
	}

	dbkey_t id = ReadIndex(0);

	FreeMySQLResult();

	if(id<=0) return 1;
	return id;
}


std::string ccdb::MySQLDataProvider::PrepareLimitInsertion(  int take/*=0*/, int startWith/*=0*/ )
{
	if(startWith != 0 && take != 0) return StringUtils::Format(" LIMIT %i, %i ", startWith, take);
	if(startWith != 0 && take == 0) return StringUtils::Format(" LIMIT %i, %i ", startWith, INFINITE_RUN);
	if(startWith == 0 && take != 0) return StringUtils::Format(" LIMIT %i ", take);
	
	return string(); //No LIMIT at all, if run point is here it corresponds to if(startWith == 0 && take ==0 )
}


int ccdb::MySQLDataProvider::CountConstantsTypeTables(Directory *dir)
{
	/**
	 * @brief This function counts number of type tables for a given directory 
	 * @param [in] directory to look tables in
	 * @return number of tables to return
	 */
	return 0;
}

