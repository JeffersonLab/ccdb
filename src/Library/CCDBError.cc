#include "CCDB/CCDBError.h"
#include "CCDB/Helpers/StringUtils.h"

std::map<int, std::string > ccdb::CCDBError::mDescriptions;
std::map<int, std::string > ccdb::CCDBError::mKeys;

std::string ccdb::CCDBError::GetDescription() const
{
	//has the errors descriptions been set?
	if (mDescriptions.size() ==0)
	{
		FillErrors();
	}

	//check description exist
	if(mDescriptions.find(mId)==mDescriptions.end())
	{
		return StringUtils::Format("Cannot find generic description for error %d", mId);
	}
	else
	{
		return mDescriptions[mId];
	}
}

ccdb::CCDBError::CCDBError(void)
{
	mMessage = "";	
	mSource ="";	
	mId = 0;	
	mLevel = 1;  //0-fatal, 1 - error, 2 - warning
	mThreadId = 0;

}

std::string ccdb::CCDBError::GetErrorKey() const
{
	//has the errors been set?
	if (mKeys.size() ==0)
	{
		FillErrors();
	}

	//check key exist
	if(mKeys.find(mId)==mKeys.end())
	{
		return StringUtils::Format("Cannot find generic description for error %d", mId);
	}
	else
	{
		return mKeys[mId];
	}
}

void ccdb::CCDBError::FillErrors()
{
	//0) get error defines from DCCDBGlobals.h
	//1) join comment lines
	// ^:b*{//.*}\n:b*//{.+}
	// \1 \2
	//2) join comment lines
	// ^:b*//{.*}\n:b*\#define {:i+}:b{:z}
	// mDescriptions[\3] = "\1"; \nmKeys[\3] = "\2"; 


mDescriptions[0] = "This flag is set when no errors are happened usually returned by GetLastError if no errors happened"; 
mKeys[0] = "CCDB_NO_ERRORS"; 

mDescriptions[1000] = "Generic error. Indicate rare and internal errors."; 
mKeys[1000] = "CCDB_ERROR"; 

mDescriptions[5000] = "Development generic error that indicates that some method is not implemented yet"; 
mKeys[5000] = "CCDB_WARNING"; 

mDescriptions[1001] = "Development generic error that indicates that some method is not implemented yet"; 
mKeys[1001] = "CCDB_ERROR_NOT_IMPLEMENTED"; 

mDescriptions[1010] = " The error happens if the connection string cannot be used for this provider  for MySQL provider when the string is not starts with \"mysql://\""; 
mKeys[1010] = "CCDB_ERROR_PARSE_CONNECTION_STRING"; 

mDescriptions[1020] = " The error happens if some one tries to initialize a new connection  without closing the old connection"; 
mKeys[1020] = "CCDB_ERROR_CONNECTION_ALREADY_OPENED"; 

mDescriptions[1030] = "The error happens probably because of problems with memory allocation during mysql initialization"; 
mKeys[1030] = "CCDB_ERROR_CONNECTION_INITIALIZATION"; 

mDescriptions[1040] = "The error happens if mysql_connect return error or, i.e., open files dont have right privileges the main info is contained in description for such error"; 
mKeys[1040] = "CCDB_ERROR_CONNECTION_EXTERNAL_ERROR"; 

// The error happens if function that needs connection to DB is called   before connection or after connection failed. Thus trying to run function 
mDescriptions[1050] = " on unconnected provider"; 
mKeys[1050] = "CCDB_ERROR_NOT_CONNECTED"; 

mDescriptions[1060] = "Error in select query execution in mysql"; 
mKeys[1060] = "CCDB_ERROR_MYSQL_SELECT"; 

mDescriptions[1070] = "Error in update query execution in mysql"; 
mKeys[1070] = "CCDB_ERROR_MYSQL_UPDATE"; 

mDescriptions[1080] = "Error in insert query execution in mysql"; 
mKeys[1080] = "CCDB_ERROR_MYSQL_INSERT"; 

mDescriptions[1090] = "Error in delete query execution in mysql"; 
mKeys[1090] = "CCDB_ERROR_MYSQL_DELETE"; 

mDescriptions[1100] = "Error in custom query execution in mysql"; 
mKeys[1100] = "CCDB_ERROR_MYSQL_CUSTOM_QUERY"; 

mDescriptions[5010] = "we have less fields than fieldNum"; 
mKeys[5010] = "CCDB_WARNING_MYSQL_FIELD_NUM"; 

mDescriptions[5020] = "My sql result was not cleaned after last query"; 
mKeys[5020] = "CCDB_WARNING_RESULT_NOT_CLEANED"; 

mDescriptions[1110] = "Object name format is invalid. Only English letters, numbers and '_' are allowed."; 
mKeys[1110] = "CCDB_ERROR_INVALID_OBJECT_NAME"; 

mDescriptions[1120] = "Given type table is null or was not found"; 
mKeys[1120] = "CCDB_ERROR_INVALID_ID"; 

mDescriptions[1130] = "Unable delete nonempty object. This error is raised i.e. if one tries to delete directory that containes subdirectory of tables  or on tries to delete type table that contain assignments. "; 
mKeys[1130] = "CCDB_ERROR_DELETE_NONEMPTY"; 

mDescriptions[1140] = "The parent directory is not set. Creation of directory without parent directory (at least /-root) is impossible"; 
mKeys[1140] = "CCDB_ERROR_NO_PARENT_DIRECTORY"; 

mDescriptions[1150] = "Invalid id is given to function that  needs the id"; 
mKeys[1150] = "CCDB_ERROR_DIRECTORY_INVALID_ID"; 

mDescriptions[1160] = "Cannot find given directory"; 
mKeys[1160] = "CCDB_ERROR_DIRECTORY_NOT_FOUND"; 

mDescriptions[1170] = "Such directory already exists"; 
mKeys[1170] = "CCDB_ERROR_DIRECTORY_EXISTS"; 

mDescriptions[1180] = "No name is defined for table fetched from table. It is impossible?"; 
mKeys[1180] = "CCDB_ERROR_TYPETABLE_HAS_NO_NAME"; 

mDescriptions[1190] = "Given type table is null or was son found"; 
mKeys[1190] = "CCDB_ERROR_NO_TYPETABLE"; 

mDescriptions[1200] = "Type table doesn't have columns (column information objects)"; 
mKeys[1200] = "CCDB_ERROR_TABLE_NO_COLUMNS"; 

mDescriptions[1210] = "Number of rows is set to be equal zero. It is inappropriate"; 
mKeys[1210] = "CCDB_ERROR_TABLE_NO_ROWS"; 

mDescriptions[1220] = "The table with this name already exists"; 
mKeys[1220] = "CCDB_ERROR_TABLE_EXISTS"; 

mDescriptions[1230] = "Run range is NULL or has improper ID so update operations can't be done";
mKeys[1230] = "CCDB_ERROR_RUNRANGE_INVALID"; 

mDescriptions[1235] = "Run range is NULL or has improper ID so update operations can't be done";
mKeys[1235] = "CCDB_ERROR_OBTAINING_RUNRANGE";

mDescriptions[1240] = "Variation is NULL or has improper ID so update operations can't be done";
mKeys[1240] = "CCDB_ERROR_VARIATION_INVALID"; 

mDescriptions[1250] = "ASSIGMEN has improper ID so update operations can't be done";
mKeys[1250] = "CCDB_ERROR_ASSIGMENT_INVALID_ID";

mDescriptions[1260] = "ASSIGMEN is NULL or has improper ID so update operations can't be done";
mKeys[1260] = "CCDB_ERROR_ASSIGMENT_INVALID";

mDescriptions[1270] = "ASSIGMEN data storage returned no assignment that corresponds to this request";
mKeys[1270] = "CCDB_ERROR_NO_ASSIGMENT";

mDescriptions[1280] = "ASSIGMEN is NULL or has improper ID so update operations can't be done";
mKeys[1280] = "CCDB_ERROR_DATA_INCONSISTANT"; 
}

