#ifndef DCCDBGlobals_h__
#define DCCDBGlobals_h__

//This type is used for database ID-s that is used in DB
typedef int dbkey_t; 


//infinite run ranges may be used to set
// 1000 to INFINITE_RUN means all runs greater or equal than run 1000
// 0 - INFINITE_RUN all possible runs
#define INFINITE_RUN 2147483647

//This constant represent the delimeter that is used to separate stringified data inside database blob
#define CCDB_DATA_BLOB_DELIMETER "|"

//name of @default variation
#define CCDB_DEFAULT_VARIATION_NAME "default"

//name of run range that holds all pssible ranges [0,INFINITE_RUN]
#define CCDB_ALL_RUNRANGE_NAME "all"

/*----------------------------------------------------------------------------------------------------
 *  E R R O R   C O D E S 
 * -------------------------------------------------------------------------------------------------*/
 
//#define CCDB_ERROR_

//this flag is set when no errors are happened
//usually returned by GetLastError if no errors happened
#define CCDB_NO_ERRORS 0

//Generic error. Indicate rare and internal errors.
#define CCDB_ERROR 1000

//Development error that indicates that some method is not implemented yet
#define CCDB_WARNING 5000

//Development generic error that indicates that some method is not implemented yet
#define CCDB_ERROR_NOT_IMPLEMENTED 1001

// The error happens if the connection string cannot be used for this provider
// for MySQL provider when the string is not starts with "mysql://"
#define CCDB_ERROR_PARSE_CONNECTION_STRING 1010

// The error happens if some one tries to initialize a new connection
// without closing the old connection
#define CCDB_ERROR_CONNECTION_ALREADY_OPENED 1020

//The error happens probably because of problems with memory allocation during mysql initialization
#define CCDB_ERROR_CONNECTION_INITIALIZATION 1030

//The error happens if mysql_connect return error or, i.e., open files dont have right privileges
//the main info is contained in description for such error
#define CCDB_ERROR_CONNECTION_EXTERNAL_ERROR 1040

// The error happens if function that needs connection to DB is called 
// before connection or after connection failed. Thus trying to run function 
// on unconnected provider
#define CCDB_ERROR_NOT_CONNECTED 1050

//Query prepare statement error
#define CCDB_ERROR_QUERY_PREPARE 1055

//Error in select query execution in mysql
#define CCDB_ERROR_QUERY_SELECT 1060

//Error in update query execution in mysql
#define CCDB_ERROR_MYSQL_UPDATE 1070

//Error in insert query execution in mysql
#define CCDB_ERROR_QUERY_INSERT 1080

//Error in delete query execution in mysql
#define CCDB_ERROR_MYSQL_DELETE 1090

//Error in custom query execution in mysql
#define CCDB_ERROR_MYSQL_CUSTOM_QUERY 1100

//we have less fields than fieldNum
#define CCDB_WARNING_DBRESULT_FIELD_INDEX 5010

//My sql result was not cleaned after last query
#define CCDB_WARNING_RESULT_NOT_CLEANED 5020

//Object name format is invalid. Only English letters, numbers and '_' are allowed.
#define CCDB_ERROR_INVALID_OBJECT_NAME 1110

//Given type table is null or was not found
#define CCDB_ERROR_INVALID_ID 1120

//Unable delete nonempty object. This error is raised i.e. if one tries to delete directory that containes subdirectory of tables
// or on tries to delete type table that contain assignments. 
#define CCDB_ERROR_DELETE_NONEMPTY 1130

//The parent directory is not set. Creation of directory without parent directory (at least /-root) is impossible
#define CCDB_ERROR_NO_PARENT_DIRECTORY 1140

//Invalid id is given to function that  needs the id
#define CCDB_ERROR_DIRECTORY_INVALID_ID 1150

//Cannot find given directory
#define CCDB_ERROR_DIRECTORY_NOT_FOUND 1160

//Such directory already exists
#define CCDB_ERROR_DIRECTORY_EXISTS 1170

//No name is defined for table fetched from table. It is impossible?
#define CCDB_ERROR_TYPETABLE_HAS_NO_NAME 1180

//Given type table is null or was son found
#define CCDB_ERROR_NO_TYPETABLE 1190

//Type table doesn't have columns (column information objects)
#define CCDB_ERROR_TABLE_NO_COLUMNS 1200

//Number of rows is set to be equal zero. It is inappropriate
#define CCDB_ERROR_TABLE_NO_ROWS 1210

//The table with this name already exists
#define CCDB_ERROR_TABLE_EXISTS 1220

//Run range is NULL or has improper ID so update operations cant be done
#define CCDB_ERROR_RUNRANGE_INVALID 1230

//Run range is NULL or has improper ID so update operations cant be done
#define CCDB_ERROR_OBTAINING_RUNRANGE 1235

//Variation is NULL or has improper ID so update operations cant be done
#define CCDB_ERROR_VARIATION_INVALID 1240

//ASSIGMEN has improper ID so update operations cant be done
#define CCDB_ERROR_ASSIGMENT_INVALID_ID 1250

//ASSIGMEN is NULL or has improper ID so update operations cant be done
#define CCDB_ERROR_ASSIGMENT_INVALID 1260

//ASSIGMEN datastorage returned no assignment that corresponds to this request 
#define CCDB_ERROR_NO_ASSIGMENT 1270

//ASSIGMEN is NULL or has improper ID so update operations cant be done
#define CCDB_ERROR_DATA_INCONSISTANT 1280

/*----------------------------------------------------------------------------------------------------
 *  SYSTEM DEFINE
 * -------------------------------------------------------------------------------------------------*/


/*---- machines --------------------------------------------------------------*/

#ifdef __hpux
    /* R__HPUX10 or R__HPUX11 is determined in the Makefile */
#   define D__HPUX
#   define D__UNIX
#endif

#ifdef _AIX
#   define D__AIX
#   define D__UNIX
#endif

#ifdef __linux
#   ifndef linux
#      define linux
#   endif
#endif

#if defined(__CYGWIN__) && defined(__GNUC__)
#   ifndef linux
#      define linux
#   endif
#   ifndef D__WINGCC
#      define D__WINGCC
#   endif
#endif

#if defined(__sun) && !(defined(linux) || defined(__FCC_VERSION))
#   ifdef __SVR4
#      define D__SOLARIS
#   else
#      define D__SUN
#      include <stdlib.h>
#   endif
#   define D__UNIX
#endif

#if defined(__FCC_VERSION)    /* Solaris with Fujitsu compiler */
#   define D__SOLARIS
#   define D__UNIX
#endif

#if defined(__sgi) && !defined(linux)
#   define D__SGI
#   define D__UNIX
#endif


#if defined(linux)
#   define D__LINUX
#   define D__UNIX
#endif

#if defined(__MACH__) && defined(__i386__) && !defined(__APPLE__)
#   define D__HURD
#   define D__UNIX
#endif

#if defined(__Lynx__) && defined(__powerpc__)
#   define D__LYNXOS
#   define D__UNIX
#endif

#if defined(__FreeBSD__)
#   define D__FBSD
#   define D__UNIX
#endif

#if defined(__OpenBSD__)
#   define D__OBSD
#   define D__UNIX
#endif

#if defined(__APPLE__)
#   define D__MACOSX
#   define D__UNIX
#endif

#ifdef _HIUX_SOURCE
#   define D__HIUX
#   define D__UNIX
#endif

#ifdef WIN32
#   define D__WIN32
#endif

#ifdef _WIN32
#   define D__WIN32
#   ifndef WIN32
#      define WIN32
#   endif
#endif


#endif // DCCDBGlobals_h__

