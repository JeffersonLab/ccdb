#pragma warning(disable:4800)
#include "Tests/tests_macros.h"
#include "DConsole.h"
#include "DStringUtils.h"
#include "Providers/DMySQLDataProvider.h"
#include "Model/DDirectory.h"
#include "Model/DConstantsTypeColumn.h"
#include "DWorkUtils.h"
#include "DStopWatch.h"

using namespace std;
using namespace ccdb;

/********************************************************************* ** 
 * @brief Test of directories work
 *
 * @return true if test passed
 */
bool test_DMySQLDataProvider_TypeTables()
{
	TESTS_INIT(" - - -   DMySQLDataProvider   T Y P E   T A B L E S   - - - ")
	DMySQLDataProvider *prov = new DMySQLDataProvider();
	if(!prov->Connect(gConnectionString)) return false;
	
	CONSOLE.WriteLine(DConsole::cBrightWhite, "\n[ Type tables getting ]");
	//basic get type table functional
	TITLE("Get type table");
	DConstantsTypeTable *table = prov->GetConstantsTypeTable("/test/test_vars/test_table", true);
	TEST(table!=NULL);
	
	//print type table
	gConsole.WriteLine(DConsole::cBrightCyan, "\nCheck returned table details");
	PrintConstantsTypeTable(table);
	gConsole.WriteLine();
	delete table; //cleanup
	
	//now lets get all tables from the directory.
	//we dont need to load colums for each table, so we will place "false" there
	TITLE("Get type tables for directory          ");
	vector<DConstantsTypeTable *> tables;
	TEST(prov->GetConstantsTypeTables(tables, "/test/test_vars", false));
	
	TITLE("1 or more tables returned"); TEST(tables.size()>0);

	
	TITLE("Get type tables for directory 2");
	tables = prov->GetConstantsTypeTables("/test/test_vars", false);
	TEST(tables.size());

	
	
	TITLE("Search type tables for directory       ");
	
	//search tables are good too
	//now lets get all tables from the directory.
	//we dont need to load colums for each table, so we will place "false" there
	TEST(prov->SearchConstantsTypeTables(tables, "t??t_tab*"));
	
	TITLE("1 or more tables returned              ");
	TEST(tables.size()>0);
	
	//Now move to create new type table
	//-------------------------------------------------------------------------------------
	CONSOLE.WriteLine(DConsole::cBrightWhite, "\n[ Type tables create/update/delete ]");
	
	table = prov->GetConstantsTypeTable("/test/test_vars/new_table");
	if(table!=NULL)
	{
		//such type table already extsts.. probably from last failed test...
		//we haven't test it yet, but we should try to delete it
		prov->DeleteConstantsTypeTable(table);
		delete table;
	}
	
	table = new DConstantsTypeTable();
	table->SetName("new_table");
	table->SetComment("This is temporary created table for test reasons");
	table->SetNRows(5);
	
	//test various ways to add column
	table->AddColumn("px", DConstantsTypeColumn::cDoubleColumn);
	table->AddColumn("px");	
	DConstantsTypeColumn *column = new DConstantsTypeColumn(table);
	column->SetName("pz");
	column->SetType("int");
	table->AddColumn(column);
	table->SetDirectory(prov->GetDirectory("/test/test_vars"));
	
	//print this table
	gConsole.WriteLine(DConsole::cBrightCyan, "\nCheck creting table details");
	PrintConstantsTypeTable(table);
	gConsole.WriteLine();
	
	//create table
	TITLE("Add table to database");
	bool result = prov->CreateConstantsTypeTable(table);
	TEST(result);
	delete table;
	
	//check that it was correctly created
	TITLE("Get created type table from DB");
	table = prov->GetConstantsTypeTable("/test/test_vars/new_table", true);
	TEST(table!=NULL);
	
	//test of fields
	TITLE("Test 'name'");         TEST(table->GetName()=="new_table");
	TITLE("Test 'full path'");    TEST_STEP(table->GetFullPath()=="/test/test_vars/new_table");
	TITLE("Test 'comment'");      TEST_STEP(table->GetComment()=="This is temporary created table for test reasons");
	TITLE("Test columns number"); TEST(table->GetColumns().size()==3);
	TITLE("Test column name");    TEST(table->GetColumns()[0]->GetName() =="px");
	TITLE("Test column type");    TEST(table->GetColumns()[0]->GetTypeString() == "double");
	TITLE("Test number of rows"); TEST(table->GetNRows()==5);
	delete table;
	
	//Ok! Now lets update table
	//----------------------------------------------------------------------------
	CONSOLE.WriteLine(DConsole::cBrightWhite, "\n[ Type tables update ]");
	table = prov->GetConstantsTypeTable("/test/test_vars/edited_table");
	if(table!=NULL)
	{
		//such type table already extsts.. probably from last failed test...
		//we haven't test it yet, but we should try to delete it
		prov->DeleteConstantsTypeTable(table);
		delete table;
	}
	TITLE("Get type table to update from DB");
	table = prov->GetConstantsTypeTable("/test/test_vars/new_table", true);
	TEST(table!=NULL);
	
	//set new values
	table->SetName("edited_table");
	table->SetComment("New comment");
	table->SetNRows(3); //this value change will be ignored! 
	
	//do update
	TITLE("Test update type table");
	TEST(prov->UpdateConstantsTypeTable(table));
	delete table;
	
	//check that it was correctly updated
	TITLE("Get updated type table from DB");
	table = prov->GetConstantsTypeTable("/test/test_vars/edited_table", true);
	TEST(table!=NULL);
	
	//test of fields
	TITLE("Test 'full path'");    TEST_STEP(table->GetFullPath()=="/test/test_vars/edited_table");
	TITLE("Test 'comment'");      TEST_STEP(table->GetComment()=="New comment");
	TITLE("Test columns number"); TEST(table->GetColumns().size()==3);
	TITLE("Test column name");    TEST(table->GetColumns()[0]->GetName() =="px");
	TITLE("Test column type");    TEST(table->GetColumns()[0]->GetTypeString() == "double");
	TITLE("Test number of rows not changed"); TEST(table->GetNRows()==5);
	
	//print it
	gConsole.WriteLine(DConsole::cBrightCyan, "\nCheck created table details");
	PrintConstantsTypeTable(table);
	gConsole.WriteLine();
	delete table;
	
	//Ok! Now lets delete table
	//----------------------------------------------------------------------------
	CONSOLE.WriteLine(DConsole::cBrightWhite, "\n[ Type tables delete ]");
	
	
	TITLE("Get updated type table from DB");
	table = prov->GetConstantsTypeTable("/test/test_vars/edited_table", true);
	TEST(table!=NULL);
	
	TITLE("Deleting table");
	TEST(prov->DeleteConstantsTypeTable(table));
	
	TITLE("Check no table in DB");
	table = prov->GetConstantsTypeTable("/test/test_vars/edited_table", true);
	TEST(table==NULL);
	
	

	delete prov;//with all objects...
	return true;
}
