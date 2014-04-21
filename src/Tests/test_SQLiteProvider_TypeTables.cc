#pragma warning(disable:4800)
#include "Tests/catch.hpp"
#include "Tests/tests.h"

#include "CCDB/Providers/SQLiteDataProvider.h"
#include "CCDB/Model/Directory.h"
#include "CCDB/Model/ConstantsTypeColumn.h"
#include "CCDB/Model/ConstantsTypeTable.h"

using namespace std;
using namespace ccdb;

/********************************************************************* ** 
 * @brief Test of directories work
 *
 * @return true if test passed
 */
TEST_CASE("CCDB/SQLiteDataProvider/TypeTables","TypeTables tests")
{
	
	SQLiteDataProvider *prov = new SQLiteDataProvider();
	if(!prov->Connect(TESTS_SQLITE_STRING)) return;

    bool result;
	
    //TYPE TABLE BASICS
    //======================================================
    //basic get type table functional

    //get type table from DB
	ConstantsTypeTable *table = prov->GetConstantsTypeTable("/test/test_vars/test_table", true);
    REQUIRE(table!=NULL);
	REQUIRE(table->GetColumns().size() == 3);
	REQUIRE(table->GetColumnsCount() == 3);
	REQUIRE(table->GetName() == "test_table");
	REQUIRE(table->GetFullPath() == "/test/test_vars/test_table");
	REQUIRE(table->GetDirectory() != NULL);
	REQUIRE(table->GetDirectory()->GetName() == "test_vars");
	REQUIRE(table->GetColumns()[0]->GetName() == string("x"));
	
	//print type table
	delete table; //cleanup
	
	//get all tables from the directory.
    vector<ConstantsTypeTable *> tables;
    //result = prov->GetConstantsTypeTables(tables, "/test/test_vars", false); //we dont need to load colums for each table, so we place last argument "false"
	
    //test we've got
	//REQUIRE(result);
	//REQUIRE(tables.size()>0);

	//second implementation of getting type tables from the directory	
	//tables = prov->GetConstantsTypeTables("/test/test_vars", false);

	//REQUIRE(tables.size());

    //SEARCH TYPE TABLES
    //======================================================
    //basic get type table functional

	
    //search tables are good too
    //now lets get all tables from the directory.
	result = prov->SearchConstantsTypeTables(tables, "t??t_tab*");

	REQUIRE(result);
	REQUIRE(tables.size()>0);

    //Search table in the specified path
    tables = prov->SearchConstantsTypeTables("*", "/test/test_vars",true);
    REQUIRE(tables.size()>0);

	tables = prov->SearchConstantsTypeTables("*", "",true);
	REQUIRE(tables.size()>0);
	
	//create new type table
	//-------------------------------------------------------------------------------------
	//table = prov->GetConstantsTypeTable("/test/test_vars/new_table");
	//if(table!=NULL)
	//{
	//	//such type table already extsts.. probably from last failed test...
	//	//we haven't test it yet, but we should try to delete it
	//	prov->DeleteConstantsTypeTable(table);
	//	delete table;
	//}
	//
	//table = new ConstantsTypeTable();
	//table->SetName("new_table");
	//table->SetComment("This is temporary created table for test reasons");
	//table->SetNRows(5);
	//
	////test various ways to add column
	//table->AddColumn("px", ConstantsTypeColumn::cDoubleColumn);
	//table->AddColumn("px");	
	//ConstantsTypeColumn *column = new ConstantsTypeColumn(table);
	//column->SetName("pz");
	//column->SetType("int");
	//table->AddColumn(column);
	//table->SetDirectory(prov->GetDirectory("/test/test_vars"));
	//

	////create table
	//result = prov->CreateConstantsTypeTable(table);
	//REQUIRE(result);
	//delete table;
	//
	////check that it was correctly created
	////Get created type table from DB
	//table = prov->GetConstantsTypeTable("/test/test_vars/new_table", true);
	//REQUIRE(table!=NULL);
	//
	////test of fields
 //   REQUIRE(table->GetName()=="new_table");
 //   REQUIRE(table->GetFullPath()=="/test/test_vars/new_table");
 //   REQUIRE(table->GetComment()=="This is temporary created table for test reasons");
	//REQUIRE(table->GetColumns().size()==3);
	//REQUIRE(table->GetColumns()[0]->GetName() =="px");
	//REQUIRE(table->GetColumns()[0]->GetTypeString() == "double");
	//REQUIRE(table->GetNRows()==5);
	//delete table;
	//
	////Ok! Now lets update table
	////----------------------------------------------------------------------------

	//table = prov->GetConstantsTypeTable("/test/test_vars/edited_table");
	//if(table!=NULL)
	//{
	//	//such type table already extsts.. probably from last failed test...
	//	//we haven't test it yet, but we should try to delete it
	//	prov->DeleteConstantsTypeTable(table);
	//	delete table;
	//}
	//
 //   //Get type table to update from DB
	//table = prov->GetConstantsTypeTable("/test/test_vars/new_table", true);
	//REQUIRE(table!=NULL);
	//
	////set new values
	//table->SetName("edited_table");
	//table->SetComment("New comment");
	//table->SetNRows(3); //this value change will be ignored! 
	//
	////Test update type table
	//REQUIRE(prov->UpdateConstantsTypeTable(table));
	//delete table;
	//
	////check that it was correctly updated
 //   //Get updated type table from DB
	//table = prov->GetConstantsTypeTable("/test/test_vars/edited_table", true);
	//REQUIRE(table!=NULL);
	//
 //   //test of fields
 //   REQUIRE(table->GetFullPath()=="/test/test_vars/edited_table");
	//REQUIRE(table->GetComment()=="New comment");
	//REQUIRE(table->GetColumns().size()==3);
	//REQUIRE(table->GetColumns()[0]->GetName() =="px");
	//REQUIRE(table->GetColumns()[0]->GetTypeString() == "double");
	//REQUIRE(table->GetNRows()==5);
	//delete table;
	//
	////Ok! Now lets delete table
	////----------------------------------------------------------------------------
	//
	////Get updated type table from DB
	//table = prov->GetConstantsTypeTable("/test/test_vars/edited_table", true);
	//REQUIRE(table!=NULL);
	//
	////Deleting table
	//REQUIRE(prov->DeleteConstantsTypeTable(table));
	//
	////Check no table in DB
	//table = prov->GetConstantsTypeTable("/test/test_vars/edited_table", true);
	//REQUIRE(table==NULL);

	delete prov;//with all objects...
}
