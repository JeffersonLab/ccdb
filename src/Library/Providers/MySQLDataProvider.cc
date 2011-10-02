#include <stdlib.h>
#include <iostream>
#include <sstream>
#include <time.h>
#include <string.h>
#include <limits.h>

#include "CCDB/Globals.h"
#include "CCDB/Log.h"
#include "CCDB/Helpers/StringUtils.h"
#include "CCDB/Providers/MySQLDataProvider.h"
#include "CCDB/Model/ConstantsTypeTable.h"
#include "CCDB/Model/RunRange.h"


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
		Error(CCDB_ERROR_PARSE_CONNECTION_STRING, "DMySQLDataProvider::Connect()", "Error parse mysql string");
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
	Log::Verbose("ccdb::DMySQLDataProvider::Connect", StringUtils::Format("Connecting to database:\n UserName: %s \n Password: %i symbols \n HostName: %s Database: %s Port: %i",
					connection.UserName.c_str(), connection.Password.length(), connection.HostName.c_str(), connection.Database.c_str(), connection.Port) );
					
	//init connection variable
	if(mMySQLHnd == NULL)mMySQLHnd = mysql_init(NULL);
	if(mMySQLHnd == NULL)
	{
		Error(CCDB_ERROR_CONNECTION_INITIALIZATION, "DMySQLDataProvider::Connect(DMySQLConnectionInfo)", "mysql_init() returned NULL, probably memory allocation problem");
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
			conStr=string("");
			logPassStr=conStr.substr(0,atPos);
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
	int whitePos=conStr.find(' ');
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

bool ccdb::MySQLDataProvider::MakeDirectory( const string& newDirName, const string& parentDirFullPath, const string& comment /*= ""*/ )
{
	ClearErrors(); //Clear error in function that can produce new ones

	//validate symbols in directory name
	string name(newDirName);

	if(!ValidateName(name))
	{
		Error(CCDB_ERROR_INVALID_OBJECT_NAME,"ccdb::DMySQLDataProvider::MakeDirectory", "Object name format is invalid.");
		return false;
	}

	//get parent directory
	Directory * parentDir = GetDirectory(parentDirFullPath);
	if(parentDir == NULL)
	{
		Error(CCDB_ERROR_NO_PARENT_DIRECTORY,"DMySQLDataProvider::MakeDirectory", "Provider is not connected to MySQL.");
		return false;
	}

	//maybe such directory already exists?
	string fullPath = StringUtils::CombinePath(parentDir->GetFullPath() ,name);
	Directory * dir = GetDirectory(fullPath.c_str());
	if(dir)
	{
		Error(CCDB_ERROR_DIRECTORY_EXISTS,"DMySQLDataProvider::MakeDirectory", "Such directory already exists");
		return false;
	}
	
	//ok... maybe table with such name exist? 
	ConstantsTypeTable *tmpTable = GetConstantsTypeTable(fullPath);
	if(tmpTable)
	{
		delete tmpTable; 
		//error? Warning?
		Error(CCDB_ERROR_TABLE_EXISTS,"DMySQLDataProvider::MakeDirectory", "Table with this name already exists");
		return false;
	}
	//building such query
	string commentInsertion = PrepareCommentForInsert(comment);	//might be NULL or \"<comment>\"
	string query = StringUtils::Format(						
		"INSERT INTO `directories` (`modified`, `name`, `parentId`, `comment`) VALUES (NULL, '%s', '%i', %s);", 
		name.c_str(), 
		parentDir->GetId(), 
		commentInsertion.c_str());

	//query DB! 
	bool result = QueryInsert(query.c_str()); 

	if(result)
	{
		//here we save parent name because next, when LoadDirectories will be called link to directory will become junk 
		string parentName = parentDir->GetName();

		//Here we might create new DDirectory * and add it to parent directory,
		//It is extremely fast comparing to database requests
		//but! there some values that might be automatically set by MYSQL
		//assuming that adding directory is "handmade" and sole operation
		//we just reload all directories from DB;
		LoadDirectories();

		//And log such function
		AdLogRecord("directories;", 
			StringUtils::Format("directories_%i;", mLastInsertedId), 
			StringUtils::Format("Directory %s created in %s", name.c_str(), parentName.c_str()),
			StringUtils::Encode(StringUtils::Format("Related comments: %s", commentInsertion.c_str())));
	}
	
	return result;
}


Directory* ccdb::MySQLDataProvider::GetDirectory( const string& path )
{
	//maybe we need to update our directories?
	UpdateDirectoriesIfNeeded();
	
	//search full path
	map<string, Directory*>::iterator it = mDirectoriesByFullPath.find(string(path));

	//found?
	if(it == mDirectoriesByFullPath.end()) return NULL; //not found
	return it->second; //found
}


bool ccdb::MySQLDataProvider::UpdateDirectory( Directory *dir )
{
	ClearErrors(); //Clear error in function that can produce new ones

	//Check id! 
	if(dir->GetId() <= 0 )
	{
		//TODO: report error
		Error(CCDB_ERROR_DIRECTORY_INVALID_ID,"DMySQLDataProvider::UpdateDirectory", "Id <= 0");
		return false;
	}

	string query = StringUtils::Format("UPDATE `directories` SET `modified` = NULL, `name` = '%s', `parentId` = %i, `comment` = %s, WHERE `id` = '%i'",
		/*name */		StringUtils::Encode(dir->GetName()).c_str(),
		/*partntId */	dir->GetParentId(),
		/*comment */	PrepareCommentForInsert(dir->GetComment().c_str()).c_str(),
		/*id */			dir->GetId());
	return QueryUpdate(query);
}

bool ccdb::MySQLDataProvider::DeleteDirectory( const string& fullPath )
{
	ClearErrors(); //Clear error in function that can produce new ones

	Directory *dir = GetDirectory(fullPath);
	if(!dir)
	{
		Error(CCDB_ERROR_DIRECTORY_NOT_FOUND,"DMySQLDataProvider::DeleteDirectory", "Directory not found with this path");
		return false;
	}
	return DeleteDirectory(dir);
}

bool ccdb::MySQLDataProvider::DeleteDirectory( Directory *dir )
{
	ClearErrors(); //Clear error in function that can produce new ones

	//check not NULL
	if(dir==NULL)
	{
		Error(CCDB_ERROR_DIRECTORY_NOT_FOUND,"DMySQLDataProvider::DeleteDirectory", "Directory not found with this path");
		return false;
	}

	//check id...
	if(dir->GetId()<=0)
	{
		//TODO: ERROR report
		Error(CCDB_ERROR_DIRECTORY_INVALID_ID,"DMySQLDataProvider::DeleteDirectory", "Directory invalid id");

		return false;
	}
	
	if(dir->GetSubdirectories().size()>0)
	{
		//TODO error, have children
		Error(CCDB_ERROR_DELETE_NONEMPTY,"DMySQLDataProvider::DeleteDirectory", "Directory contains subdirectory");
		return false;
	}
	
	string assCountQuery = StringUtils::Format("SELECT `id` FROM `typeTables` WHERE `directoryId`='%i' LIMIT 1",dir->GetId());
	if(!QuerySelect(assCountQuery)) 
	{
		return false;
	}
	if(mReturnedRowsNum > 0)
	{
		//TODO warning
		Error(CCDB_ERROR_DELETE_NONEMPTY,"DMySQLDataProvider::DeleteDirectory", "Directory contains type tables");
		return false;
	}
	string affectedIds;
	
	string query = StringUtils::Format("DELETE FROM `directories` WHERE id = '%i';", dir->GetId());
	
	bool result =  QueryDelete(query.c_str());
	if(result)
	{
		//just log this wicked action
		AdLogRecord("directories;",
		StringUtils::Format("directories_%l;", dir->GetId()),
		StringUtils::Format("Delete directory %s", dir->GetName().c_str()),
		StringUtils::Format("Delete directory %s,\n comments: %s", dir->GetName().c_str(), dir->GetComment().c_str()));
	}
	LoadDirectories();

	return result;
}

#pragma endregion Directories



bool ccdb::MySQLDataProvider::IsStoredObjectsOwner()
{
	return mIsStoredObjectOwner;
}

void ccdb::MySQLDataProvider::IsStoredObjectsOwner(bool flag)
{
	mIsStoredObjectOwner = flag;
}

ConstantsTypeTable * ccdb::MySQLDataProvider::GetConstantsTypeTable( const string& name, Directory *parentDir,bool loadColumns/*=false*/ )
{
	ClearErrors(); //Clear error in function that can produce new ones

	//check the directory is ok
	if(parentDir == NULL || parentDir->GetId()<=0)
	{
		//error
		Error(CCDB_ERROR_NO_PARENT_DIRECTORY,"DMySQLDataProvider::GetConstantsTypeTable", "Parent directory is null or have invalid ID");
		return NULL;
	}

	//check connection
	if(!IsConnected())
	{
		//error !not connect
		Error(CCDB_ERROR_NOT_CONNECTED,"DMySQLDataProvider::GetConstantsTypeTable", "Provider is not connected to MySQL.");
		return NULL;
	}
	
	string query = StringUtils::Format("SELECT `id`, UNIX_TIMESTAMP(`created`) as `created`, UNIX_TIMESTAMP(`modified`) as `modified`, `name`, `directoryId`, `nRows`, `nColumns`, `comments` FROM `typeTables` WHERE `name` = '%s' AND `directoryId` = '%i';",
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
		Error(CCDB_ERROR_TYPETABLE_HAS_NO_NAME,"DMySQLDataProvider::GetConstantsTypeTable", "");
		delete result;
		return NULL;
	}
	
	//Ok set a full path for this constant...
	result->SetFullPath(StringUtils::CombinePath(parentDir->GetFullPath(), result->GetName()));

	
	FreeMySQLResult();
	
	//load columns if needed
	if(loadColumns) LoadColumns(result);
	return result;
}

ConstantsTypeTable * ccdb::MySQLDataProvider::GetConstantsTypeTable(const string& path, bool loadColumns/*=false*/ )
{
	//get directory path
	string dirPath = StringUtils::ExtractDirectory(path);
	
	//and directory
	Directory *dir = GetDirectory(dirPath.c_str());
	//probably one may wish to check dir to be !=NULL,
	//but such check is in GetConstantsTypeHeader(const char* name, DDirectory *parentDir);
	
	//retrieve name of our constant table 
	string name = StringUtils::ExtractObjectname(path);
	
	//get it from db etc...
	return GetConstantsTypeTable(name.c_str(), dir, loadColumns);
}

bool ccdb::MySQLDataProvider::GetConstantsTypeTables( vector<ConstantsTypeTable *>& resultTypeTables, const string&  parentDirPath, bool loadColumns/*=false*/ )
{
	//and directory
	Directory *dir = GetDirectory(parentDirPath);
	//probably one may wish to check dir to be !=NULL,
	//but such check is in GetConstantsTypeHeaders( DDirectory *parentDir, vector<DConstantsTypeTable *>& consts );
	return GetConstantsTypeTables(resultTypeTables, dir);
}

bool ccdb::MySQLDataProvider::GetConstantsTypeTables(  vector<ConstantsTypeTable *>& resultTypeTables, Directory *parentDir, bool loadColumns/*=false*/)
{
	ClearErrors(); //Clear error in function that can produce new ones

	//check the directory is ok
	if((parentDir == NULL || parentDir->GetId()<=0) && (parentDir!=mRootDir))
	{
		//TODO error
		Error(CCDB_ERROR_NO_PARENT_DIRECTORY,"DMySQLDataProvider::GetConstantsTypeTables", "Parent directory is null or has invald ID");
		return NULL;
	}
	
	//Ok, lets cleanup result list
		resultTypeTables.clear(); //we clear the consts. Considering that some one else should handle deletion

	string query = StringUtils::Format("SELECT `id`, UNIX_TIMESTAMP(`created`) as `created`, UNIX_TIMESTAMP(`modified`) as `modified`, `name`, `directoryId`, `nRows`, `nColumns`, `comments` FROM `typeTables` WHERE `directoryId` = '%i';",
		/*`directoryId`*/ parentDir->GetId());

	if(!QuerySelect(query))
	{
		//no report error
		return NULL;
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

bool ccdb::MySQLDataProvider::CreateConstantsTypeTable( ConstantsTypeTable *table )
{
	ClearErrors(); //Clear error in function that can produce new ones

	//validation
	if(table == NULL)
	{
		//TODO error? Warning?
		Error(CCDB_ERROR_NO_TYPETABLE,"DMySQLDataProvider::CreateConstantsTypeTable", "Type table is null or invalid");
		return false;
	}

	if(table->GetDirectory() == NULL)
	{
		//TODO error? Warning?
		Error(CCDB_ERROR_NO_PARENT_DIRECTORY,"DMySQLDataProvider::CreateConstantsTypeTable", "Directory pointer is NULL for this type table object");
		return false;
	}

	if(table->GetColumns().size() <=0)
	{
		//TODO error? Warning?
		Error(CCDB_ERROR_TABLE_NO_COLUMNS,"DMySQLDataProvider::CreateConstantsTypeTable", "No colums for this type table object. Cant create");
		return false;
	}

	if(!ValidateName(table->GetName()))
	{
		//TODO error? Warning?
		Error(CCDB_ERROR_INVALID_OBJECT_NAME,"DMySQLDataProvider::CreateConstantsTypeTable", "Name has invalid format");
		return false;
	}
	if(!table->GetNRows())
	{
		//TODO error? Warning?
		Error(CCDB_ERROR_TABLE_NO_ROWS,"DMySQLDataProvider::CreateConstantsTypeTable", "Nomber of rows is equal to 0");
		return false;
	}

	//ok... maybe table with such name exist? 
	ConstantsTypeTable *tmpTable = GetConstantsTypeTable(table->GetName().c_str(), table->GetDirectory());
	if(tmpTable)
	{
		delete tmpTable; 
		//error? Warning?
		Error(CCDB_ERROR_TABLE_EXISTS,"DMySQLDataProvider::CreateConstantsTypeTable", "Table with this name already exists");
		return false;
	}

	//ok... maybe directory with such name exist? 
	Directory *tmpDir = GetDirectory(StringUtils::CombinePath(table->GetDirectory()->GetFullPath(), table->GetName()) );
	if(tmpDir)
	{	
		//error? Warning?
		Error(CCDB_ERROR_DIRECTORY_EXISTS,"DMySQLDataProvider::CreateConstantsTypeTable", "There is a directory with such name");
		return false;
	}


	//start query, lock tables, make transaction imune;
	if(!QueryCustom("START TRANSACTION;"))
	{
		return false; 
	}
	
	string query = 
	" INSERT INTO `typeTables` "
	"	(`modified`, `name`, `directoryId`, `nRows`, `nColumns`, `comments`) VALUES "
	"	(   NULL   , \"%s\",      '%i'    ,   '%i' ,     '%i'  ,     %s	  ); ";
	
	query = StringUtils::Format(query.c_str(), 
		table->GetName().c_str(),
		table->GetDirectory()->GetId(),
		table->GetNRows(),
		table->GetNColumns(),
		PrepareCommentForInsert(table->GetComment().c_str()).c_str()  );
	
	//query...
	if(!QueryInsert(query))
	{
		//no report error
		QueryCustom("ROLLBACK;"); //rollback transaction doesnt matter will it happen or not but we should try
		return false;
	}
	
	table->SetId(static_cast<dbkey_t>(mLastInsertedId));
	
	//Now it is time to create columns
	if(!CreateColumns(table))
	{
		QueryCustom("ROLLBACK;"); //rollback transaction. Will it happen or not depends on error - but we should try
		return false;
	}
	
	//commit changes

	if(!QueryCustom("COMMIT;"))
	{
		return false; 
	}

	//add log record
	AdLogRecord("typeTables;",
		StringUtils::Format("typeTables_%l;", table->GetId()),
		StringUtils::Format("Created constants type table %s", table->GetName().c_str()),
		StringUtils::Format("Created constants type table %s,\n comments: %s", table->GetName().c_str(), table->GetComment().c_str()));
	
	return true;
}

ConstantsTypeTable* ccdb::MySQLDataProvider::CreateConstantsTypeTable( const string& name, const string& parentPath, int rowsNumber, map<string, string> columns, const string& comments /*=""*/ )
{
	return CreateConstantsTypeTable(name, GetDirectory(parentPath), rowsNumber, columns, comments);
}

ConstantsTypeTable* ccdb::MySQLDataProvider::CreateConstantsTypeTable( const string& name, Directory *parentDir, int rowsNumber, map<string, string> columns, const string& comments /*=""*/ )
{
	ConstantsTypeTable *table = new ConstantsTypeTable();
	table->SetName(name);
	table->SetComment(comments);
	table->SetNRows(rowsNumber);

	map<string, string>::const_iterator iter = columns.begin();
	for(; iter != columns.end(); iter++)
	{
		table->AddColumn(iter->first, ConstantsTypeColumn::StringToType(iter->second));
	}
	table->SetDirectory(parentDir);

	if(CreateConstantsTypeTable(table)) return table;
	else return NULL;
}



bool ccdb::MySQLDataProvider::SearchConstantsTypeTables( vector<ConstantsTypeTable *>& typeTables, const string& pattern, const string& parentPath /*= ""*/, bool loadColumns/*=false*/, int take/*=0*/, int startWith/*=0 */ )
{
	ClearErrors(); //Clear error in function that can produce new ones

	// in MYSQL compared to wildcards % is * and _ is 
	// convert it. 
	string likePattern = WilcardsToLike(pattern);
    
	//do we need to search only in specific directory?
	string parentAddon(""); 		//this is addon to query indicates this
	Directory *parentDir = NULL; //will need it anyway later
	if(parentPath!="")
	{	//we should care about parent path!
		if(parentDir = GetDirectory(parentPath.c_str()))
		{
			parentAddon = StringUtils::Format(" AND `directoryId` = '%i'", parentDir->GetId());
		}
		else
		{
			//request was made for directory that doestn exits
			//TODO place warning or not?
			Error(CCDB_ERROR_DIRECTORY_NOT_FOUND,"DMySQLDataProvider::SearchConstantsTypeTables", "Path to search is not found");
			return false;
		}
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
	string query = StringUtils::Format("SELECT `id`, UNIX_TIMESTAMP(`created`) as `created`, UNIX_TIMESTAMP(`modified`) as `modified`, `name`, `directoryId`, `nRows`, `nColumns`, `comments` FROM `typeTables` WHERE `name` LIKE '%s' %s ORDER BY `name` %s;",
		likePattern.c_str(), parentAddon.c_str(), limitAddon.c_str());
        
	if(!QuerySelect(query))
	{
		//no report error
		return NULL;
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


bool ccdb::MySQLDataProvider::UpdateConstantsTypeTable( ConstantsTypeTable *table )
{
	ClearErrors(); //Clear error in function that can produce new ones

	if(!table || !table->GetId())
	{
		//TODO warning
		Error(CCDB_ERROR_NO_TYPETABLE,"DMySQLDataProvider::UpdateConstantsTypeTable", "Type table is null or have wrong ID");
		return false;
	}
	
	if(!table->GetDirectory())
	{
		//TODO warning
		Error(CCDB_ERROR_NO_PARENT_DIRECTORY,"DMySQLDataProvider::UpdateConstantsTypeTable", "Directory is NULL for the table");
		return false;
	}
	
	if(!ValidateName(table->GetName()))
	{
		//done error
		Error(CCDB_ERROR_INVALID_OBJECT_NAME,"DMySQLDataProvider::UpdateConstantsTypeTable", "Table name is incorect. Only letters, digits and '_' are allowed. ");
		return false;
	}
	
	ConstantsTypeTable *existingTable =GetConstantsTypeTable(table->GetFullPath());
	
	if(existingTable!=NULL && existingTable->GetId()!=table->GetId())
	{
		//error
		Error(CCDB_ERROR_NO_TYPETABLE,"DMySQLDataProvider::UpdateConstantsTypeTable", "Another table whith such name is found");
		return false;
	}
	
	string query = StringUtils::Format(" UPDATE `typeTables`"
			" SET `modified` = NULL, `name` = \"%s\", `directoryId` = '%i', `comments` = %s "
			" WHERE `id` = '%i' ", 
			table->GetName().c_str(), 
			table->GetDirectory()->GetId(), 
			PrepareCommentForInsert(table->GetComment()).c_str(),
			table->GetId());
	
	bool result = QueryUpdate(query);
	if(result)
	{
		AdLogRecord("typeTables;",
		StringUtils::Format("typeTables_%l;", table->GetId()),
		StringUtils::Format("Update constants type table %s", table->GetName().c_str()),
		StringUtils::Format("Update constants type table %s,\n comments: %s", table->GetName().c_str(), table->GetComment().c_str()));
	}
	else
	{
		//probably the error is printed by QueryUpdate
		return false;
	}
	
	return true;
}

bool ccdb::MySQLDataProvider::DeleteConstantsTypeTable( ConstantsTypeTable *table )
{
	ClearErrors(); //Clear error in function that can produce new ones

	//validation
	if(table == NULL || table->GetId() <=0)
	{
		//TODO error? Warning?
		Error(CCDB_ERROR_NO_TYPETABLE,"DMySQLDataProvider::DeleteConstantsTypeTable", "Type table is null or have wrong ID");
		return false;
	}
	
	string assCountQuery = StringUtils::Format(" SELECT `id` FROM `constantSets` WHERE `constantTypeId`='%i' LIMIT 1", table->GetId() );
	if(!QuerySelect(assCountQuery)) 
	{	
		return false;
	}
	if(mReturnedRowsNum > 0)
	{
		return false;
	}
	FreeMySQLResult();
	

	string query = StringUtils::Format("DELETE FROM `typeTables` WHERE `id` = %i ;", table->GetId());
	if(!QueryDelete(query))
	{
		return false;
	}

	//Delete columns
	query = StringUtils::Format("DELETE FROM `columns` WHERE `typeId` = %i ;", table->GetId());
	if(!QueryDelete(query))
	{
		return false;
	}
	else
	{
		//just log this wicked action
		AdLogRecord("typeTables;",
		StringUtils::Format("typeTables_%l;", table->GetId()),
		StringUtils::Format("Delete constants type table %s", table->GetName().c_str()),
		StringUtils::Format("Delete constants type table %s,\n comments: %s", table->GetName().c_str(), table->GetComment().c_str()));
	}
	return true;
}

bool ccdb::MySQLDataProvider::CreateColumn(ConstantsTypeColumn* column)
{

	/** @brief Creates columns for the table
	 *
	 * @param parentDir
	 * @return vector of constants
	 */
	
	string query = 
		"INSERT INTO `columns`												  "
		"	( `modified`, `name`, `typeId`, `columnType`, `order`, `comment`) "
		"	VALUES															  "
		"	(   NULL    , \"%s\",   '%i'  ,    '%s'     ,  '%i'  ,    %s    );";

	query = StringUtils::Format(query.c_str(), 
		column->GetName().c_str(), 
		column->GetTypeTableId(),  
		column->GetTypeString().c_str(),
		column->GetOrder(),
		PrepareCommentForInsert(column->GetComment()).c_str());
	
	if(!QueryInsert(query))
	{
		return false;
	}
	
	return true;
}
bool ccdb::MySQLDataProvider::CreateColumns(ConstantsTypeTable* table)
{
/** @brief Loads columns for the table
 *
 * @param parentDir
 * @return vector of constants
 */
	ClearErrors(); //Clear error in function that can produce new ones

	//get and validate parent table ID
	dbkey_t tableId = table->GetId();
	if(tableId <=0)
	{
		//TODO WARNING try to create columns without table key
		Error(CCDB_ERROR_INVALID_ID,"DMySQLDataProvider::CreateColumns", "Type table has wrong DB ID");
		return false; 
	}

	if(table->GetColumns().size() <=0)
	{
		//TODO WARNING try to create columns without columns
		Error(CCDB_ERROR_TABLE_NO_COLUMNS,"DMySQLDataProvider::CreateColumns", "Table have no columns or colums are not loaded");
		return false; 
	}
	
	//TODO begin transaction

	const vector<ConstantsTypeColumn *>& columns = table->GetColumns();
	vector<ConstantsTypeColumn *>::const_iterator iter= columns.begin();
	for(; iter<columns.end(); ++iter)
	{
		ConstantsTypeColumn *column= *iter;
		if(!(CreateColumn(column )))
		{	
			return false;
		}
	}

	//TODO end transaction
	return true;
}

bool ccdb::MySQLDataProvider::LoadColumns( ConstantsTypeTable* table )
{
	ClearErrors(); //Clear error in function that can produce new ones

	//check the directory is ok
	if(table->GetId()<=0)
	{
		//TODO error
		Error(CCDB_ERROR_INVALID_ID,"DMySQLDataProvider::LoadColumns", "Type table has wrong ID");
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

bool ccdb::MySQLDataProvider::CreateRunRange( RunRange *run )
{
	ClearErrors(); //Clear error in function that can produce new ones

	//query;
	string query = StringUtils::Format("INSERT INTO `runRanges` (`modified`, `runMin`, `runMax`, `name`, `comment`)"
		"VALUES (NULL, '%i', '%i', '%s', '%s');",
		run->GetMin(),
		run->GetMax(),
		run->GetName().c_str(),
		run->GetComment().c_str());
	
	//Do query
	if(!QueryInsert(query))
	{
		//NO report error
		return false;
	}
    
    run->SetId(mLastInsertedId);

	return true;
}

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
	
	//Ok! We querryed our run range! lets catch it! 
	
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
		Error(CCDB_ERROR,"DMySQLDataProvider::GetRunRange", "Run range with such min, max and name is not alone in the DB");
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
		Error(CCDB_ERROR,"DMySQLDataProvider::GetRunRange", "Run range with such name is not alone in the DB");
	}

	FreeMySQLResult();
	return result;
}

RunRange* ccdb::MySQLDataProvider::GetOrCreateRunRange( int min, int max, const string& name/*=""*/, const string& comment/*=""*/ )
{
	//if one gets NULL after that function it is probably only because 
	//run range with such name already exists but have different min and max ranges
	// or, surely, because error with MySQL coGetOrCreateRunRangennection or something like this happened
	RunRange *result = GetRunRange(min,max, name);
	if(!result)
	{
		//Ok, lets try to create it...
		result = new RunRange(this, this);
		result->SetRange(min, max);
		result->SetName(string(name));
		result->SetComment(string(comment));
		//TODO deside how to handle comment and time;
		//TODO (!) Maybe change to REPLACE instead of insert?
		//Try to create and return null if it was impossible
		if(!CreateRunRange(result)) 
        {
            Error(CCDB_ERROR_OBTAINING_RUNRANGE,"DDataProvider::GetOrCreateRunRange", 
                  StringUtils::Format("Can not get or create run range run-min: %i, run-max: %i, run-name: %s", min, max, name.c_str()));
            return NULL;
        }

	}
	return result;
}


bool ccdb::MySQLDataProvider::GetRunRanges(vector<RunRange*>& resultRunRanges, ConstantsTypeTable* table, const string& variation/*=""*/, int take/*=0*/, int startWith/*=0*/)
{
	ClearErrors(); //Clear error in function that can produce new ones

	if(!CheckConnection("DMySQLDataProvider::GetRunRanges(vector<DRunRange*>& resultRunRanges, DConstantsTypeTable* table, int take, int startWith)")) return false;
	
	//validate table
	if(!table || !table->GetId())
	{
		//TODO report error
		Error(CCDB_ERROR_NO_TYPETABLE,"DMySQLDataProvider::GetRunRanges", "Type table is null or have invalid id");
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

bool ccdb::MySQLDataProvider::DeleteRunRange(RunRange* run)
{
	ClearErrors(); //Clear errors in function that can produce new ones

	if(!run || run->GetId() <=0)
	{
		//TODO error;
		Error(CCDB_ERROR_RUNRANGE_INVALID,"DMySQLDataProvider::DeleteRunRange", "Runrange is null or have invalid ID");
		return false;
	}
	string assCountQuery = StringUtils::Format("SELECT `id` FROM `assignments` WHERE `runRangeId`='%i' LIMIT 1",run->GetId() );
	if(!QuerySelect(assCountQuery)) 
	{
		//TODO error;
		return false;
	}
	if(mReturnedRowsNum > 0)
	{
		//TODO warning
		Error(CCDB_ERROR_DELETE_NONEMPTY,"DMySQLDataProvider::DeleteRunRange", "There is assigment that linked to this runrange. Impossible to delete it");
		return false;
	}
	FreeMySQLResult();

	string query = StringUtils::Format("DELETE FROM `runRanges` WHERE `runRanges`.`id`='%i';", run->GetId());
	bool result = QueryDelete(query);
	if(result)
	{
		AdLogRecord("runranges;",StringUtils::Format("runRanges_%i;", run->GetId()), "Delete run range", StringUtils::Format("Delete run range: from %i to %i with name %s", run->GetMin(), run->GetMax(), run->GetName().c_str()));
	}
	return result;
}

bool ccdb::MySQLDataProvider::UpdateRunRange(RunRange* run)
{
	ClearErrors(); //Clear error in function that can produce new ones

	if(run==NULL || run->GetId()<=0) 
	{
		//TODO error
		Error(CCDB_ERROR_RUNRANGE_INVALID,"DMySQLDataProvider::UpdateRunRange", "Run range is null or has wrong id");
		return false;
	}

	string query=StringUtils::Format(
		"UPDATE `runRanges` SET `modified` = NULL, " 
		" `name` = \"%s\", `runMin` = '%i', `runMax` = '%i', `comment` = %s "
		" WHERE `runRanges`.`id` = '%i' ;",
		StringUtils::Encode(run->GetName()).c_str(), 
		run->GetMin(),
		run->GetMax(),
		StringUtils::Encode(run->GetComment()).c_str(),
		run->GetId());
	return QueryUpdate(query);

}


bool ccdb::MySQLDataProvider::GetVariations(vector<Variation*>& resultVariations, ConstantsTypeTable* table, int run, int take, int startWith)
{
	ClearErrors(); //Clear error in function that can produce new ones

	if(!CheckConnection("DMySQLDataProvider::GetRunRanges(vector<DRunRange*>& resultRunRanges, DConstantsTypeTable* table, int take, int startWith)")) return false;
	
	//validate table
	if(!table || !table->GetId())
	{
		//TODO report error
		Error(CCDB_ERROR_NO_TYPETABLE,"DMySQLDataProvider::GetVariations", "Type table is null or empty");
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

	//TODO: Implement method
	string query = 
		"SELECT											 "
		"`id`,											 "
		"UNIX_TIMESTAMP(`created`) as `created`,		 "
		"UNIX_TIMESTAMP(`modified`) as `modified`,		 "
		"`name`,										 "
		"`description`,									 "
		"`comment`										 "
		"FROM `variations`								 "
		"WHERE `name`= \"%s\";							 ";
	query = StringUtils::Format(query.c_str(), name.c_str());
	//query this
	if(!QuerySelect(query))
	{
		//TODO report error
		return NULL;
	}

	//Ok! We querried our run range! lets catch it! 
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

	if(mReturnedRowsNum>1)
	{
		//TODO warning not uniq row
	}

	FreeMySQLResult();
	return result;
}

dbkey_t ccdb::MySQLDataProvider::GetVariationId( const string& name )
{
    ClearErrors(); //Clear error in function that can produce new ones

    //check that maybe we have this variation id by the last request?
    if(name == mLastVariationName) return mLastVariationId;

    string query = "SELECT	`id` FROM `variations` WHERE `name`= \"%s\";";
    query = StringUtils::Format(query.c_str(), name.c_str());


    //query this
    if(!QuerySelect(query))
    {
        //TODO report error
        return (dbkey_t)-1;
    }

    //Ok! We querried our run range! lets catch it! 
    if(!FetchRow())
    {
        //nothing was selected
        return (dbkey_t)-1;
    }

    //ok lets read the data...
    dbkey_t result = ReadULong(0);

    //save variation so maybe we don't need to query it next time
    mLastVariationName = name;
    mLastVariationId = result;

    FreeMySQLResult();
    return result;
}
bool ccdb::MySQLDataProvider::CreateVariation( Variation *variation )
{
	ClearErrors(); //Clear error in function that can produce new ones

	string query=
		"INSERT INTO `variations` "
		"(`modified`,			  "
		"`name`,				  "
		"`description`,			  "
		"`comment`)				  "
		"VALUES	(NULL, \"%s\",	\"\", %s);";
	
	//TODO decide what to do with description of variation
	query = StringUtils::Format(query.c_str(), variation->GetName().c_str(), variation->GetComment().c_str());
	
	//Do query
	if(!QueryInsert(query))
	{
		//TODO report error
		return false;
	}

	return true;
}


bool ccdb::MySQLDataProvider::UpdateVariation( Variation *variation )
{
	ClearErrors(); //Clear error in function that can produce new ones

	//validate
	if(!variation || variation->GetId()<=0)
	{
		//TODO warning
		Error(CCDB_ERROR_VARIATION_INVALID,"DMySQLDataProvider::UpdateVariation", "Variation is NULL or has bad ID so update operations cant be done");
		return false;
	}
	
	string query = "UPDATE `variations` SET `modified` = NULL, `name` = \"%s\", `comment` = %s, WHERE `id` = %i";
	query = StringUtils::Format(query.c_str(), variation->GetName().c_str(), PrepareCommentForInsert(variation->GetComment().c_str()).c_str(), variation->GetId());

	if(!QueryUpdate(query))
	{
		//TODO report something
		return false;
	}

	return true;
}


bool ccdb::MySQLDataProvider::DeleteVariation( Variation *variation )
{
	ClearErrors(); //Clear error in function that can produce new ones

	//validate
	if(!variation || variation->GetId()<=0)
	{
		//TODO warning
		Error(CCDB_ERROR_VARIATION_INVALID,"DMySQLDataProvider::DeleteVariation", "Variation is NULL or has bad ID so delete operations cant be done");
		return false;
	}
	
	string assCountQuery = StringUtils::Format("SELECT `id` FROM `assignments` WHERE `variationId`='%i' LIMIT 1",variation->GetId() );
	if(!QuerySelect(assCountQuery)) 
	{
		//TODO error;
		return false;
	}
	if(mReturnedRowsNum > 0)
	{
		//TODO warning
		return false;
	}
	string query = StringUtils::Format("DELETE FROM `variations` WHERE `id` = %'i'", variation->GetId());

	bool result = QueryDelete(query);
	if(result)
	{
		AdLogRecord("variations;",StringUtils::Format("variations_%i;", variation->GetId()), "Delete run variation", StringUtils::Format("Delete variation: name %s", variation->GetName().c_str()));
	}
	return result;
}

//----------------------------------------------------------------------------------------
//	A S S I G N M E N T S
//----------------------------------------------------------------------------------------
	
Assignment* ccdb::MySQLDataProvider::GetAssignmentShort(int run, const string& path, const string& variation, bool loadColumns /*=true*/)
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

	ClearErrors(); //Clear errors in function that can produce new ones ;)

	if(!CheckConnection("DMySQLDataProvider::GetAssignmentShort(int run, const string& path, const string& variation)")) return NULL;

	//get table! 
	ConstantsTypeTable *table = GetConstantsTypeTable(path, loadColumns);
	if(!table)
	{
		//TODO report error
		Error(CCDB_ERROR_NO_TYPETABLE,"DMySQLDataProvider::GetAssignmentShort", StringUtils::Format("Table with the name '%s' was not found", path.c_str()));
		return NULL;
	}

    //get variation id
    int varId = GetVariationId( variation );

	//ok now we must build our mighty query...
    //TODO this is not optimized request. The request could be optimized.
	string query=
        "SELECT `assignments`.`id` AS `asId`, "
        "`constantSets`.`vault` AS `blob` "
        "FROM  `assignments` "
        "USE INDEX (id_UNIQUE) "
        "INNER JOIN `runRanges` ON `assignments`.`runRangeId`= `runRanges`.`id` "
        "INNER JOIN `constantSets` ON `assignments`.`constantSetId` = `constantSets`.`id` "
        "WHERE  `runRanges`.`runMin` <= '%i' "
        "AND `runRanges`.`runMax` >= '%i' "
        "AND `assignments`.`variationId`= '%i' "
        "AND `constantSets`.`constantTypeId` ='%i' "
        "ORDER BY `assignments`.`id` DESC "
        "LIMIT 1 ";

	query=StringUtils::Format(query.c_str(), run, run, varId, table->GetId());
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
	Assignment *result = new Assignment(this, this);
	result->SetId( ReadIndex(0) );
	//result->SetCreatedTime( ReadUnixTime(1) );
	//result->SetModifiedTime( ReadUnixTime(2) );
	result->SetRawData( ReadString(1) );
	
	//additional fill
	result->SetRequestedRun(run);
	result->SetTypeTable(table);
	if(IsOwner(table)) table->SetOwner(result); //new ownership?
	

	if(mReturnedRowsNum>1)
	{
		//TODO warning not uniq row
		Error(CCDB_ERROR,"DMySQLDataProvider::GetAssignmentShort", "Many variations return instead of one");
	}

	FreeMySQLResult();
	return result;
}


Assignment* ccdb::MySQLDataProvider::GetAssignmentShort(int run, const string& path, time_t time, const string& variation, bool loadColumns /*=true*/)
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

	if(!CheckConnection("DMySQLDataProvider::GetAssignmentShort( int run, const char* path, const char* variation, int version /*= -1*/ )")) return NULL;
	
	//get table! 
	ConstantsTypeTable *table = GetConstantsTypeTable(path, loadColumns);
	if(!table)
	{
		Error(CCDB_ERROR_NO_TYPETABLE,"DMySQLDataProvider::GetAssignmentShort", "No type table with this path was found");
		return NULL;
	}

    //get variation id
    int varId = GetVariationId( variation );

	//ok now we must build our mighty query...
	string query=
        "SELECT `assignments`.`id` AS `asId`, "
        "`constantSets`.`vault` AS `blob` "
        "FROM  `assignments` "
        "USE INDEX (id_UNIQUE) "
        "INNER JOIN `runRanges` ON `assignments`.`runRangeId`= `runRanges`.`id` "
        "INNER JOIN `constantSets` ON `assignments`.`constantSetId` = `constantSets`.`id` "
        "WHERE  `runRanges`.`runMin` <= '%i' "
        "AND `runRanges`.`runMax` >= '%i' "
        "AND `assignments`.`variationId`= '%i' "
        "AND (UNIX_TIMESTAMP(`assignments`.`created`) <= '%lu') "
        "AND `constantSets`.`constantTypeId` ='%i' "
        "ORDER BY `assignments`.`id` DESC "
        "LIMIT 1 ";
		

	query=StringUtils::Format(query.c_str(), run,run, varId, time, table->GetId());
	
	//query this
	if(!QuerySelect(query))
	{
		//TODO report error
		return NULL;
	}

	//Ok! We querried our run range! lets catch it! 
	if(!FetchRow())
	{
		//nothing was selected
		return NULL;
	}

	//ok lets read the data...
	Assignment *result = new Assignment(this, this);
	result->SetId(ReadULong(0));
	result->SetCreatedTime(ReadUnixTime(1));
	result->SetModifiedTime(ReadUnixTime(2));
	result->SetRunRangeId(ReadInt(3));
	result->SetVariationId(ReadInt(4));
	result->SetDataVaultId(ReadInt(5));
	result->SetRawData(ReadString(6));
	
	//additional fill
	result->SetRequestedRun(run);
	result->SetTypeTable(table);
	
	if(mReturnedRowsNum>1)
	{
		//TODO warning not uniq row
	}

	FreeMySQLResult();
	return result;

}

Assignment* ccdb::MySQLDataProvider::GetAssignmentShortByVersion(int run, const string& path, int version, const string& variation)
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

	if(!CheckConnection("DMySQLDataProvider::GetAssignmentShort( int run, const char* path, const char* variation, int version /*= -1*/ )")) return NULL;
	
	//get table! 
	ConstantsTypeTable *table = GetConstantsTypeTable(path, true);
	if(!table)
	{
		//TODO report error
		Error(CCDB_ERROR_NO_TYPETABLE,"DMySQLDataProvider::GetAssignmentShort", "No type table with this path was found");
		return NULL;
	}

	//ok now we must build our mighty query...
	string query= 
		" SELECT 													"
		" `assignments`.`id` AS `asId`,								"
		" UNIX_TIMESTAMP(`assignments`.`created`) as `asCreated`,	"
		" UNIX_TIMESTAMP(`assignments`.`modified`) as `asModified`,	"
		" `runRanges`.`id`   AS `runRangeId`, 						"
		" `variations`.`id`  AS `varId`,								"
		" `constantSets`.`id` AS `constId`,							"
		" `constantSets`.`vault` AS `blob`,							"
		" FROM `typeTables` 											"
		" INNER JOIN `assignments` ON `assignments`.`runRangeId`= `runRanges`.`id` "
		" INNER JOIN `variations` ON `assignments`.`variationId`= `variations`.`id` "
		" INNER JOIN `constantSets` ON `assignments`.`constantSetId` = `constantSets`.`id` "
		" INNER JOIN `typeTables` ON `constantSets`.`constantTypeId` = `typeTables`.`id` "
		" WHERE "
		" `runRanges`.`runMin` < '%i' "
		" AND `runRanges`.`runMax` > '%i' "
		" AND (UNIX_TIMESTAMP(`assignments`.`creation`) = 0 OR 1 = 1) "
		" AND `variations`.`name`=\"%s\"	"
		" AND `typeTables`.`id` = %i	"
		" ORDER BY `assignments`.`time` DESC	"
		" LIMIT 0,1; ";
		

	query=StringUtils::Format(query.c_str(), run,run, variation.c_str(), table->GetId());
	
	//query this
	if(!QuerySelect(query))
	{
		//TODO report error
		return NULL;
	}

	//Ok! We querried our run range! lets catch it! 
	if(!FetchRow())
	{
		//nothing was selected
		return NULL;
	}

	//ok lets read the data...
	Assignment *result = new Assignment(this, this);
	result->SetId(ReadULong(0));
	result->SetCreatedTime(ReadUnixTime(1));
	result->SetModifiedTime(ReadUnixTime(2));
	result->SetRunRangeId(ReadInt(3));
	result->SetVariationId(ReadInt(4));
	result->SetDataVaultId(ReadInt(5));
	result->SetRawData(ReadString(6));
	
	//additional fill
	result->SetRequestedRun(run);
	result->SetTypeTable(table);
	
	if(mReturnedRowsNum>1)
	{
		//TODO warning not uniq row
	}

	FreeMySQLResult();
	return result;
}

bool ccdb::MySQLDataProvider::CreateAssignment(Assignment *assignment )
{   
	ClearErrors(); //Clear error in function that can produce new ones

	//Check runrange...
	RunRange * runRange= assignment->GetRunRange();
    //TODO event range handling

    //Validation of inputted object
    if(!assignment->GetRunRange())           {cout<<"!assignment->GetRunRange()"<<endl;           return false;}
    if(!assignment->GetRunRange()->GetId())  
    {
        Error(CCDB_ERROR_RUNRANGE_INVALID,"DMySQLDataProvider::CreateAssignment(DAssignment *assignment)", StringUtils::Format("Runrange is null or have invalid ID. ID is: %i" + assignment->GetRunRange()->GetId()));
        return false;
    }
    if(!assignment->GetVariation())          {cout<<"!assignment->GetVariation()"<<endl;          return false;}
	if(!assignment->GetVariation()->GetId()) {cout<<"!assignment->GetVariation()->GetId()"<<endl; return false;}

	ConstantsTypeTable *table = assignment->GetTypeTable();
	if(table == NULL || !table->GetId())
	{
		//TODO warning
		Error(CCDB_ERROR_NO_TYPETABLE,"DMySQLDataProvider::CreateAssignment", "Table is NULL or has wrong id");
		return false;
	}

	//start query, lock tables, make transaction imune;
	if(!QueryCustom("START TRANSACTION;"))
	{
        cout<<"!QueryCustom(\"START TRANSACTION;\")"<<endl;
		return false; 
	}

	//add constants
	string query = 
		" INSERT INTO `constantSets` (`modified`, `vault`, `constantTypeId`) "
	    "                      VALUES(   NULL   ,  \"%s\",	       %i      );";
	query = StringUtils::Format(query.c_str(), assignment->GetRawData().c_str(), table->GetId());
	
	//query...
	if(!QueryInsert(query))
	{
		//TODO report error
		QueryCustom("ROLLBACK;"); //rollback transaction doesnt matter will it happen or not but we should try
        cout<<"!QueryInsert(query)1"<<endl;
		return false;
	}
	assignment->SetDataVaultId(static_cast<dbkey_t>(mLastInsertedId));

	query = "INSERT INTO `assignments` "
	"	(				"
	"	`modified`,		"
	"	`variationId`,	"
	"	`runRangeId`,	"
	"	`eventRangeId`,	"
	"	`constantSetId`,"
	"	`comment`)		"
	"	VALUES	(NULL, "		//modified update 
	"  %i, "					//  #{variationId: INT}
	"	%i, "					//  #{runRangeId: INT},		  
	"	NULL,"					//	#{eventRangeId: INT},
	"	LAST_INSERT_ID(), "		//	#{constantSetId: INT},	
	"	%s "					//	#{comment: TEXT}
	");	";
	query = StringUtils::Format(query.c_str(), 
		assignment->GetVariation()->GetId(), 
		assignment->GetRunRange()->GetId(),
		PrepareCommentForInsert(assignment->GetComment().c_str()).c_str());
	//query...
	if(!QueryInsert(query))
	{
		//TODO report error
		QueryCustom("ROLLBACK;"); //rollback transaction doesnt matter will it happen or not but we should try
        cout<<"!QueryInsert(query)2"<<endl;
		return false;
	}
	assignment->SetId(static_cast<dbkey_t>(mLastInsertedId));
	
	//adjust number in data table
	query = StringUtils::Format("UPDATE typeTables SET nAssignments=nAssignments+1 WHERE id='%i';", table->GetId());
	QueryUpdate(query);
	
	//commit changes
	if(!QueryCustom("COMMIT;"))
	{	
        cout<<"!QueryCustom(\"COMMIT;\")"<<endl;
		return false; 
	}

	//just log this wicked action
	AdLogRecord("assignments;constantSets;",
		StringUtils::Format("assignments_%i;constantSets_%i", assignment->GetId(), assignment->GetDataVaultId()),
		StringUtils::Format("Add assignment to %s", assignment->GetTypeTable()->GetName().c_str()),
		StringUtils::Format("Add assignment to %s,\n comments: %s", assignment->GetTypeTable()->GetName().c_str(), table->GetComment().c_str()));
	return true;
}

Assignment* ccdb::MySQLDataProvider::CreateAssignment(const std::vector<std::vector<std::string> >& data, const std::string& path, int runMin, int runMax, const std::string& variationName, const std::string& comments)
{
    // cout <<"HERE HERE"<<endl;
	/* Creates Assignment using related object.
	* Validation:
	* If no such run range found, the new will be created (with no name)
	* No action will be done (and NULL will be returned):
	* 
	* -- If no type table with such path exists
	* -- If data is inconsistent with columns number and rows number
	* -- If no variation with such name found */
	ClearErrors(); //Clear error in function that can produce new ones
	
	Variation* variation = GetVariation(variationName);
	if(variation == NULL)
	{
		 //TODO error message
		Error(CCDB_ERROR_VARIATION_INVALID,"DMySQLDataProvider::CreateAssignment", "Variation is NULL or has improper ID");
		return NULL;
	}
	 
	ConstantsTypeTable* table=GetConstantsTypeTable(path, true);
	if(!table)
	{
		//TODO error message
		Error(CCDB_ERROR_NO_TYPETABLE,"DMySQLDataProvider::CreateAssignment", "Type table is NULL or has improper ID");
		return NULL;
	}
	 
	//check that we have right rows number
	if(data.size()!= table->GetNRows())
	{
		 //error message
		Error(CCDB_ERROR_DATA_INCONSISTANT,"DMySQLDataProvider::CreateAssignment", 
              StringUtils::Format("Number of rows is inconsistent. Rows in table definition: %i, actual rows number %i",table->GetNRows(), data.size()));
		return NULL;
	}

	//fill data blob vector
	vector<string> vectorBlob;
	for (size_t rowIter=0; rowIter<data.size(); rowIter++)
	{
		const vector<string> &row = data[rowIter];
		if(row.size() != table->GetNColumns())
		{
			//TODO error handle
			Error(CCDB_ERROR_DATA_INCONSISTANT, "DMySQLDataProvider::CreateAssignment", 
                    StringUtils::Format("Number of columns is inconsistent. Row with inconsistency (zero based): %i , columns by table definition: %i, actual columns number %i",rowIter, table->GetNColumns(), row.size()));
			return NULL;
		}

		for (int i=0; i<row.size(); i++)
		{
			vectorBlob.push_back(row[i]);
		}
	}
	
	//last one we need is a run range
	RunRange * runRange = GetOrCreateRunRange(runMin, runMax, "", "");
	if(runRange == NULL)
	{
		//error reporting is in GetOrCreateRunRange
		return NULL;
	}

	Assignment * assignment=new Assignment(this, this);
	assignment->SetRawData(Assignment::VectorToBlob(vectorBlob));
	
	assignment->SetVariation(variation);
	assignment->BeOwner(variation);

	assignment->SetRunRange(runRange);
	assignment->BeOwner(runRange);

	assignment->SetTypeTable(table);	//set this table
	assignment->BeOwner(table);			//new table should be owned by assignment

	assignment->SetComment(StringUtils::Encode(comments));

	if(CreateAssignment(assignment))
	{
		return assignment;
	}
	else 
	{
		delete assignment;
		return NULL;
	}
}

Assignment* ccdb::MySQLDataProvider::GetAssignmentFull( int run, const string& path, const string& variation )
{
	if(!CheckConnection("DMySQLDataProvider::GetAssignmentFull(int run, cconst string& path, const string& variation")) return NULL;
	vector<Assignment *> assigments;
	if(!GetAssignments(assigments, path, run,run, "", variation, 0, 0, 0, 1, 0))
	{
		return NULL;
	}
	
	if(assigments.size()<=0) return NULL;
	
	return *assigments.begin();
	
}

Assignment* ccdb::MySQLDataProvider::GetAssignmentFull( int run, const string& path,int version, const string& variation/*= "default"*/)
{

	if(!CheckConnection("DMySQLDataProvider::GetAssignmentFull( int run, const char* path, const char* variation, int version /*= -1*/ )")) return NULL;
	
	//get table! 
	vector<Assignment *> assigments;
	if(!GetAssignments(assigments, path, run,run, "", variation, 0, 0, 1, 1, version))
	{
		return NULL;
	}

	if(assigments.size()<=0) return NULL;

	return *assigments.begin();
}


bool ccdb::MySQLDataProvider::GetAssignments( vector<Assignment *> &assingments,const string& path, int runMin, int runMax, const string& runRangeName, const string& variation, time_t beginTime, time_t endTime, int sortBy/*=0*/,  int take/*=0*/, int startWith/*=0*/ )
{
	ClearErrors(); //Clear error in function that can produce new ones

	if(!CheckConnection("DMySQLDataProvider::GetAssignments( ... )")) return false;

	//get table! 
	ConstantsTypeTable *table = GetConstantsTypeTable(path, true);
	if(!table)
	{
		//TODO report error
		Error(CCDB_ERROR_NO_TYPETABLE,"DMySQLDataProvider::GetAssignments", "Type table was not found");
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
		return NULL;
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

bool ccdb::MySQLDataProvider::UpdateAssignment(Assignment* assignment)
{
	Error(
		CCDB_ERROR_NOT_IMPLEMENTED, 
		"DMySQLDataProvider::UpdateAssignment(DAssignment* assignment)",
		"Method is not implemented");
	return false;
}

bool ccdb::MySQLDataProvider::DeleteAssignment(Assignment* assignment)
{
	ClearErrors(); //Clear error in function that can produce new ones

	//Check primary ID
	if(!assignment->GetId())
	{
		//todo error
		Error(CCDB_ERROR_ASSIGMENT_INVALID_ID,"DMySQLDataProvider::DeleteAssignment", "!assignment->GetId()");
		return false;
	}
	
	//Check data vault ID
	if(!assignment->GetDataVaultId())
	{
		//todo error 
		Error(CCDB_ERROR_ASSIGMENT_INVALID_ID,"DMySQLDataProvider::DeleteAssignment", "!assignment->GetDataVaultId()");
		return false;
	}
	
	//Check that all is OK with table
	if(!assignment->GetTypeTable() || !assignment->GetTypeTable()->GetId())
	{
		//todo error 
		Error(CCDB_ERROR_NO_TYPETABLE,"DMySQLDataProvider::DeleteAssignment", "Type table is null or has improper id");
		return false;
	}
	
	//start query, lock tables, make transaction imune;
	if(!QueryCustom("START TRANSACTION;"))
	{
		return false; 
	}
	
	//add constants
	string query = StringUtils::Format(" DELETE FROM  constantSets WHERE constantSets.id = '%i% ;",assignment->GetDataVaultId());
	
	//query...
	if(!QueryDelete(query))
	{
		//TODO report error
		QueryCustom("ROLLBACK;"); //rollback transaction doesnt matter will it happen or not but we should try
		return false;
	}
	
	query = StringUtils::Format(" DELETE FROM  assignments WHERE assignments.id = '%i% ;",assignment->GetId());
	
	//query...
	if(!QueryDelete(query))
	{
		//TODO report error
		QueryCustom("ROLLBACK;"); //rollback transaction doesnt matter will it happen or not but we should try
		return false;
	}
	
	//adjust number in data table
	query = StringUtils::Format("UPDATE typeTables SET nAssignments=nAssignments-1 WHERE id='%i';", assignment->GetTypeTable()->GetId());
	QueryUpdate(query);
	
	//commit changes
	if(!QueryCustom("COMMIT;"))
	{
		return false; 
	}
	
	return true;
}

bool ccdb::MySQLDataProvider::FillAssignment(Assignment* assignment)
{
	ClearErrors(); //Clear error in function that can produce new ones
	if(assignment == NULL || !assignment->GetId())
	{
		//todo report errors
		Error(CCDB_ERROR_ASSIGMENT_INVALID,"DMySQLDataProvider::FillAssignment", "ASSIGnMENt is NULL or has improper ID so update operations cant be done");
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
	
	//Mayby we need to update our directories?
	UpdateDirectoriesIfNeeded();

	if(mDirectoriesById.find(directoryId) == mDirectoriesById.end())
	{
		//todo report errors
		Error(CCDB_ERROR,"DMySQLDataProvider::FillAssignment", "Cannot find directory locally by ID taken from database");
		return false;
	}

	Directory *parent = mDirectoriesById[directoryId];
	
	ConstantsTypeTable * table = GetConstantsTypeTable(typeTableName, parent, true);
	if(!table)
	{
		Error(CCDB_ERROR_NO_TYPETABLE,"DMySQLDataProvider::FillAssignment", "Type table was not loaded");
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

		BuildDirectoryDependences(); //

		mDirsAreLoaded=true;
	}
	return false;
}

void ccdb::MySQLDataProvider::BuildDirectoryDependences()
{
	// this method is supposed to be called after new directories are loaded, but dont have hierarchical structure

	//clear the full path dictionary
	mDirectoriesByFullPath.clear();
	mDirectoriesByFullPath[mRootDir->GetFullPath()] = mRootDir;

	//begin loop through the directories
	vector<Directory *>::iterator dirIter = mDirectories.begin();
	for(;dirIter < mDirectories.end(); dirIter++)
	{
		// retrieve parent id 
		// and check if it have parent directory
		Directory *dir = *dirIter; //(*dirIter) cool it is C++, baby

		if(dir->GetParentId() >0)
		{
			//this directory must have a parent! so now search it
			map<int,Directory *>::iterator parentDirIter = mDirectoriesById.find(dir->GetParentId()) ;
			if(parentDirIter!=mDirectoriesById.end())
			{
				//We found parent
				parentDirIter->second->AddSubdirectory(*dirIter);
			}
			else
			{
				//TODO : ADD error, parent Id not found
				Error(CCDB_ERROR_NO_PARENT_DIRECTORY,"DMySQLDataProvider::BuildDirectoryDependences", "Parent directory with wrong id");
				continue; //we have to stop operate this directory...
			}
		}
		else
		{
			// this directory doesn't have parent 
			// (means it doesn't have parentId so it lays in root directory)
			// so we place it to root directory
			mRootDir->AddSubdirectory(*dirIter);
		}

		//creating full path for this directory
		string fullpath = StringUtils::CombinePath(dir->GetParentDirectory()->GetFullPath(), dir->GetName());
		dir->SetFullPath(fullpath);


		//add to our full path map
		mDirectoriesByFullPath[dir->GetFullPath()] = dir;
	}
}

Directory*const ccdb::MySQLDataProvider::GetRootDirectory()
{
	UpdateDirectoriesIfNeeded();
	return mRootDir;
}

bool ccdb::MySQLDataProvider::CheckDirectoryListActual()
{
	//TODO: method should check the database if the directories was updated in DB. Now it only checks if directories were loaded

	if(!mDirsAreLoaded) return false; //directories are not loaded

	return !mNeedCheckDirectoriesUpdate; 
}

bool ccdb::MySQLDataProvider::UpdateDirectoriesIfNeeded()
{	
	//Logic to check directories...
	//if(!CheckDirectoryListActual()) return LoadDirectories(); //TODO check braking links
	//repairing it
	if(!mDirsAreLoaded) return LoadDirectories();
	return true;
}

bool ccdb::MySQLDataProvider::SearchDirectories( vector<Directory *>& resultDirectories, const string& searchPattern, const string& parentPath/*=""*/,  int take/*=0*/, int startWith/*=0*/ )
{	
	UpdateDirectoriesIfNeeded(); //do we need to update directories?

	resultDirectories.clear();

	// in MYSQL compared to wildcards % is * and _ is 
	// convert it. 
	string likePattern = WilcardsToLike(searchPattern);
	
	//do we need to search only in specific directory?
	string parentAddon(""); //this is addon to query indicates this
	if(parentPath!="")
	{	//we should care about parent path
		
		//If parent directory is "/" this should work too, because it have an id=0
		//and tabeles in db wich doesnt have parents should have parentId=0
		
		Directory *parentDir;
		if(parentDir = GetDirectory(parentPath.c_str()))
		{
			parentAddon = StringUtils::Format(" AND `parentId` = '%i'", parentDir->GetId());
		}
		else
		{
			//request was made for directory that doestn exits
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

vector<Directory *> ccdb::MySQLDataProvider::SearchDirectories( const string& searchPattern, const string& parentPath/*=""*/, int startWith/*=0*/, int select/*=0*/ )
{
	vector<Directory *> result;
	SearchDirectories(result, searchPattern, parentPath, startWith, select);
	return result;
}

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



#pragma region MySQL_Field_Operations

bool ccdb::MySQLDataProvider::IsNullOrUnreadable( int fieldNum )
{
	// Checks if there is a value with this fieldNum index (reports error in such case)
	// and if it is not null (just returns false in this case)

	if(mReturnedFieldsNum<=fieldNum)
	{
		//Add error, we have less fields than fieldNum
		Error(CCDB_WARNING_MYSQL_FIELD_NUM,"DMySQLDataProvider::IsNullOrUnreadable", "we have less fields than fieldNum");
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
	if(!CheckConnection("DMySQLDataProvider::QuerySelect")) return false;
	
	//do we have some results we need to free?
	if(mResult!=NULL)
	{		
		FreeMySQLResult();
	}

	//query
	if(mysql_query(mMySQLHnd, query))
	{
		string errStr = ComposeMySQLError("mysql_query()"); errStr.append("\n Query: "); errStr.append(query);
		Error(CCDB_ERROR_MYSQL_SELECT,"ccdb::DMySQLDataProvider::QuerySelect()",errStr.c_str());
		return false;
	}

	//get results
	mResult = mysql_store_result(mMySQLHnd);

	if(!mResult)
	{
		string errStr = ComposeMySQLError("mysql_query()"); errStr.append("\n Query: "); errStr.append(query);
		Error(CCDB_ERROR_MYSQL_SELECT,"ccdb::DMySQLDataProvider::QuerySelect()",errStr.c_str());

			
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


bool ccdb::MySQLDataProvider::QueryInsert( const char* query )
{
	if(!CheckConnection("DMySQLDataProvider::QueryCustom")) return false;
		
	//do we have some results we need to free?
	if(mResult!=NULL)
	{	
		FreeMySQLResult();
	}

	//query
	if(mysql_query(mMySQLHnd, query))
	{
		string errStr = ComposeMySQLError("mysql_query()"); errStr.append("\n Query: "); errStr.append(query);
		Error(CCDB_ERROR_MYSQL_SELECT,"ccdb::DMySQLDataProvider::QueryInsert()",errStr.c_str());
		return false;
	}

	//get last inserted id
	if ((mResult = mysql_store_result(mMySQLHnd)) == 0 &&
		mysql_field_count(mMySQLHnd) == 0 &&
		mysql_insert_id(mMySQLHnd) != 0)
	{
		mLastInsertedId = mysql_insert_id(mMySQLHnd);
		return true;
	}

	return false;	
}

bool ccdb::MySQLDataProvider::QueryInsert( const string& query )
{
	return QueryInsert(query.c_str());
}


bool ccdb::MySQLDataProvider::QueryUpdate( const char* query )
{
	if(!CheckConnection("DMySQLDataProvider::QueryCustom")) return false;
	
	//do we have some results we need to free?
	if(mResult!=NULL)
	{	
		FreeMySQLResult();
	}

	//query
	if(mysql_query(mMySQLHnd, query))
	{
		//TODO: error report
		string errStr = ComposeMySQLError("mysql_query()"); errStr.append("\n Query: "); errStr.append(query);
		Error(CCDB_ERROR_MYSQL_UPDATE,"ccdb::DMySQLDataProvider::QueryUpdate()",errStr.c_str());
		return false;
	}

	mReturnedAffectedRows = mysql_affected_rows(mMySQLHnd);

	return mReturnedAffectedRows>0;
}

bool ccdb::MySQLDataProvider::QueryUpdate( const string& query ) /*/Do "Update" queries */
{
	return QueryUpdate(query.c_str());
}

bool ccdb::MySQLDataProvider::QueryDelete( const char* query )
{
	if(!CheckConnection("DMySQLDataProvider::QueryCustom")) return false;
	
	//do we have some results we need to free?
	if(mResult!=NULL)
	{	
		FreeMySQLResult();
	}
	//query
	if(mysql_query(mMySQLHnd, query))
	{
		//TODO: error report
		string errStr = ComposeMySQLError("mysql_query()"); errStr.append("\n Query: "); errStr.append(query);
		Error(CCDB_ERROR_MYSQL_DELETE,"ccdb::DMySQLDataProvider::QueryDelete()",errStr.c_str());
		return false;
	}

	mReturnedAffectedRows = mysql_affected_rows(mMySQLHnd);

	return true;
}

bool ccdb::MySQLDataProvider::QueryDelete( const string& query )
{
	return QueryDelete(query.c_str());
}

bool ccdb::MySQLDataProvider::QueryCustom( const string& query )
{
	if(!CheckConnection("DMySQLDataProvider::QueryCustom")) return false;

	//do we have some results we need to free?
	if(mResult!=NULL)
	{	
		FreeMySQLResult();
	}
	//query
	if(mysql_query(mMySQLHnd, query.c_str()))
	{
		string errStr = ComposeMySQLError("mysql_query()"); errStr.append("\n Query: "); errStr.append(query);
		Error(CCDB_ERROR_MYSQL_CUSTOM_QUERY,"ccdb::DMySQLDataProvider::QueryCustom( string query )",errStr.c_str());
		return false;
	}
	return true;
}



#pragma endregion


#pragma region Fetch_free_and_other_MySQL_operations

bool ccdb::MySQLDataProvider::FetchRow()
{	
    
	if(mRow = mysql_fetch_row(mResult)) return true;
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


void ccdb::MySQLDataProvider::AdLogRecord( string userName, string affectedTables, string affectedIds, string shortDescription, string fullDescription )
{
	int id = GetUserId(userName);	

	string query = "INSERT INTO `logs` "
		" (`affectedTables`, `affectedIds`, `authorId`, `description`,  `fullDescription`) VALUES "
		" (    \"%s\"      ,      \"%s\"  , 	 %i   ,    \"%s\"    ,        \"%s\"     ); ";
	query = StringUtils::Format(query.c_str(), affectedTables.c_str(), affectedIds.c_str(), id, shortDescription.c_str(), fullDescription.c_str());
	
	QueryInsert(query);
	
}

void ccdb::MySQLDataProvider::AdLogRecord( string affectedTables, string affectedIds, string shortDescription, string fullDescription )
{
	AdLogRecord(mLogUserName, affectedTables, affectedIds, shortDescription, fullDescription);
}

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

