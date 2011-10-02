#ifndef benchmark_PreparedStatements_h__
#define benchmark_PreparedStatements_h__

#include <string.h>
#include <my_global.h>
#include <mysql.h>
#include "CCDB/Console.h"
#include "CCDB/Helpers/StopWatch.h"
#include "CCDB/Providers/MySQLDataProvider.h"
#include "CCDB/Model/Assignment.h"
#include "Benchmarks/benchmarks.h"
#include "CCDB/Model/ConstantsTypeTable.h"



/////////////////////////////////////////////////////////
/////////////////////////////////////////////////////////
#define STRING_SIZE 50

#define SELECT_SAMPLE "SELECT col1, col2, col3, col4 FROM test_table"

MYSQL_STMT    *stmt;
MYSQL_BIND    out_bind[2];
MYSQL_BIND    in_binds[4];
MYSQL_RES     *prepare_meta_result;
MYSQL_TIME    ts;
unsigned long length[4];
int           param_count, column_count, row_count;
short         small_data;
int           int_data;
char          str_data[STRING_SIZE];
my_bool       is_null[4];
my_bool       error[4];
char select_query[]=
    "SELECT `assignments`.`id` AS `asId`, "
    "`constantSets`.`vault` AS `blob` "
    "FROM  `assignments` "
    "USE INDEX (id_UNIQUE) "
    "INNER JOIN `runranges` ON `assignments`.`runRangeId`= `runRanges`.`id` "
    "INNER JOIN `constantSets` ON `assignments`.`constantSetId` = `constantSets`.`id` "
    "WHERE  `runRanges`.`runMin` <= ? "
    "AND `runRanges`.`runMax` >= ? "
    "AND  `assignments`.`variationId` =? "
    "AND `constantSets`.`constantTypeId` = ? "
    "ORDER BY `assignments`.`id` DESC "
    "LIMIT 1 ";

MYSQL *mysql;
unsigned long table_id = 1;
unsigned int variationId=1;
unsigned long variation_leng = 7;
char * variation = "default";

//_______________________________________________________________
bool PreparedQueriesInit()
{
    //Initialize statements

    //init mysql
    mysql = mysql_init(NULL);
    if(mysql == NULL)
    {
        fprintf(stderr, "mysql_init() returned NULL, probably memory allocation problem");
        return false;
    }

    //Try to connect to server
    if(!mysql_real_connect (
        mysql,          //pointer to connection handler
        "localhost",    //host to connect to
        "ccdb_user",    //user name
        "",             //password
        "ccdb",         //database to use
        0,              //port
        NULL,           //socket (use default)
        0))             //flags (none)
    {
        fprintf(stderr,"cant connect to database");
        return false;
    }

    /* Prepare a SELECT query to fetch data from test_table */
    stmt = mysql_stmt_init(mysql);
    if (!stmt)
    {
        fprintf(stderr, " mysql_stmt_init(), out of memory\n");
        return false;
    }
    if (mysql_stmt_prepare(stmt, select_query, strlen(select_query)))
    {
        fprintf(stderr, " mysql_stmt_prepare(), SELECT failed\n");
        fprintf(stderr, " %s\n", mysql_stmt_error(stmt));
        return false;
    }
    fprintf(stdout, " prepare, SELECT successful\n");

    /* Get the parameter count from the statement */
    param_count= mysql_stmt_param_count(stmt);
    fprintf(stdout, " total parameters in SELECT: %d\n", param_count);

    if (param_count != 4) /* validate parameter count */
    {
        fprintf(stderr, " invalid parameter count returned by MySQL\n");
        return false;
    }

    /* Fetch result set meta information */
    prepare_meta_result = mysql_stmt_result_metadata(stmt);
    if (!prepare_meta_result)
    {
        fprintf(stderr, " mysql_stmt_result_metadata(), returned no meta information\n");
        fprintf(stderr, " %s\n", mysql_stmt_error(stmt));
        return false;
    }

    /* Get total columns in the query */
    column_count= mysql_num_fields(prepare_meta_result);
    fprintf(stdout, " total columns in SELECT statement: %d\n", column_count);

    if (column_count != 2) /* validate column count */
    {
        fprintf(stderr, " invalid column count returned by MySQL\n");
        return false;
    }

    memset(in_binds, 0, sizeof(in_binds));
    int run = 100;

    /* INTEGER PARAM */
    /* This is a number type, so there is no need
    to specify buffer_length */
    in_binds[0].buffer_type= MYSQL_TYPE_LONG;
    in_binds[0].buffer= (void *)&run;
    in_binds[0].is_null= 0;
    in_binds[0].length= 0;

    in_binds[1].buffer_type= MYSQL_TYPE_LONG;
    in_binds[1].buffer= (void *)&run;
    in_binds[1].is_null= 0;
    in_binds[1].length= 0;

    /* STRING PARAM */
    in_binds[2].buffer_type= MYSQL_TYPE_LONG;
    in_binds[2].buffer= &variationId;
    in_binds[1].is_null= 0;
    in_binds[1].length= 0;

    /* Type tables ID */
    in_binds[3].buffer_type= MYSQL_TYPE_LONG;
    in_binds[3].buffer= (void *)&table_id;
    in_binds[3].is_null= 0;
    in_binds[3].length= 0;

    /* Bind the buffers */
    if (mysql_stmt_bind_param(stmt, in_binds))
    {
        fprintf(stderr, " mysql_stmt_bind_param() failed\n");
        fprintf(stderr, " %s\n", mysql_stmt_error(stmt));
        return false;
    }

    /* Bind the result buffers for all 4 columns before fetching them */
    memset(out_bind, 0, sizeof(out_bind));

    /* INTEGER COLUMN */
    out_bind[0].buffer_type= MYSQL_TYPE_LONG;
    out_bind[0].buffer= (char *)&int_data;
    out_bind[0].is_null= &is_null[0];
    out_bind[0].length= &length[0];
    out_bind[0].error= &error[0];

    /* STRING COLUMN */
    out_bind[1].buffer_type= MYSQL_TYPE_STRING;
    out_bind[1].buffer= (char *)str_data;
    out_bind[1].buffer_length= STRING_SIZE;
    out_bind[1].is_null= &is_null[1];
    out_bind[1].length= &length[1];
    out_bind[1].error= &error[1];

    /* Bind the result buffers */
    if (mysql_stmt_bind_result(stmt, out_bind))
    {
        fprintf(stderr, " mysql_stmt_bind_result() failed\n");
        fprintf(stderr, " %s\n", mysql_stmt_error(stmt));
        return false;
    }

    //all is done 
    return true;
}

//_______________________________________________________________
bool benchmark_PreparedStatements()
{
    //Do benchmark 

    if(!PreparedQueriesInit()) return false;

    MySQLDataProvider *prov = new MySQLDataProvider();
    if(!prov->Connect("mysql://ccdb_user@localhost")) return false;

    BENCHMARK_INIT("P R E P A R E D   Q U E R I E S    B E N C H M A R K S");

    BENCHMARK_START("Get assignment prepared statements benchmark");
    /* Execute the SELECT query */
    for (int i=0; i<10000; i++)
    {
        prov->GetConstantsTypeTable("/test/test_vars/test_table",false);

        if (mysql_stmt_execute(stmt))
        {
            fprintf(stderr, " mysql_stmt_execute(), failed\n");
            fprintf(stderr, " %s\n", mysql_stmt_error(stmt));
            exit(0);
        }

        /* Now buffer all results to client (optional step) */
        if (mysql_stmt_store_result(stmt))
        {
            fprintf(stderr, " mysql_stmt_store_result() failed\n");
            fprintf(stderr, " %s\n", mysql_stmt_error(stmt));
            exit(0);
        }
    }

    BENCHMARK_FINISH("1000 times prepared statements");

    /* Fetch all rows */
    row_count= 0;
    fprintf(stdout, "Fetching results ...\n");
    while (!mysql_stmt_fetch(stmt))
    {
        row_count++;
        fprintf(stdout, "  row %d\n", row_count);

        /* column 1 */
        fprintf(stdout, "   column1 (integer)  : ");
        if (is_null[0]) fprintf(stdout, " NULL\n");
        else fprintf(stdout, " %d(%ld)\n", int_data, length[0]);

        /* column 2 */
        fprintf(stdout, "   column2 (string)   : ");
        if (is_null[1]) fprintf(stdout, " NULL\n");
        else fprintf(stdout, " %s(%ld)\n", str_data, length[1]);
    }
    int_data = 0;

    /* Execute the SELECT query */
    if (mysql_stmt_execute(stmt))
    {
        fprintf(stderr, " mysql_stmt_execute(), failed\n");
        fprintf(stderr, " %s\n", mysql_stmt_error(stmt));
        exit(0);
    }

    /* Now buffer all results to client (optional step) */
    if (mysql_stmt_store_result(stmt))
    {
        fprintf(stderr, " mysql_stmt_store_result() failed\n");
        fprintf(stderr, " %s\n", mysql_stmt_error(stmt));
        exit(0);
    }

    /* Fetch all rows */
    row_count= 0;
    fprintf(stdout, "Fetching results ...\n");
    while (!mysql_stmt_fetch(stmt))
    {
        row_count++;
        fprintf(stdout, "  row %d\n", row_count);

        /* column 1 */
        fprintf(stdout, "   column1 (integer)  : ");
        if (is_null[0]) fprintf(stdout, " NULL\n");
        else fprintf(stdout, " %d(%ld)\n", int_data, length[0]);

        /* column 2 */
        fprintf(stdout, "   column2 (string)   : ");
        if (is_null[1]) fprintf(stdout, " NULL\n");
        else fprintf(stdout, " %s(%ld)\n", str_data, length[1]);

    }

    /* Free the prepared result metadata */
    mysql_free_result(prepare_meta_result);


    /* Close the statement */
    if (mysql_stmt_close(stmt))
    {
        fprintf(stderr, " failed while closing the statement\n");
        fprintf(stderr, " %s\n", mysql_stmt_error(stmt));
        exit(0);
    }

    return true;
}

#endif // benchmark_PreparedStatements_h__