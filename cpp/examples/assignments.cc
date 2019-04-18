/**
 * Example shows how to manipulate with Assignment object to get 
 * extended information about data fields.
 */

#include <CCDB/Calibration.h>
#include <CCDB/CalibrationGenerator.h>
#include <CCDB/SQLiteCalibration.h>
#include <CCDB/Model/Assignment.h>
#include <CCDB/Model/ConstantsTypeColumn.h>
#include <stdio.h>
#include <string>
#include <vector>
#include <memory>
#include <stdlib.h>     

using namespace std;
using namespace ccdb;

string create_connection_string()
{
	/** creates example connection string to ccdb demo sqlite database*/
	string ccdb_home(getenv("CCDB_HOME"));
	return string("sqlite://" + ccdb_home + "/sql/ccdb.sqlite");
}


int main()
{
	//Obtain connection string. You can change it to "mysql://localhost for example
	string connection_str = create_connection_string();
	if (!connection_str.size())
    {
		cout<<"No connection string"<<endl;
		return 1;
	}
	cout<<"Connecting to "<<connection_str<<endl;
	
	
	// Create calibraion object
	// To specify run number, variation and time, the full signature of CreateCalibration is:
	// CreateCalibration(connection_str, int run=0, const string& variation="default", const time_t time=0);
	//
	// (!) remark: CreateCalibration throws logic_error with explanation if something goes wrong
	auto_ptr<Calibration> calib(CalibrationGenerator::CreateCalibration(connection_str));
	
	// The calibration object is now connected and ready to work. Lets get data:
	
	//Assignment object holds all information about data obtained
	auto_ptr<Assignment> a(calib->GetAssignment("/test/test_vars/test_table"));
	
	//type table class holds information about table
	cout<<"A full path requested: "<< a->GetTypeTable()->GetFullPath() <<endl;
	
	//table holds information about columns
	const vector<ConstantsTypeColumn *> &columns = a->GetTypeTable()->GetColumns();
	cout<<"Columns:"<<endl;
	for(size_t i=0; i< columns.size(); i++)
	{
		cout<<"  name: '"<< columns[i]->GetName() <<"'   type: '"<< columns[i]->GetTypeString()<<"'"<<endl;
	}
	
	// With assignment class we can access cell values individually
	//
	//assignment has a->GetRowsCount() and GetColumnsCount() functions 
	//that are actually calls the functions of ConstantsTypeTable class
	for(size_t rowI = 0; rowI < a->GetRowsCount(); rowI++)
	{
		for(size_t colI = 0; colI < a->GetColumnsCount(); colI++)
		{
			//To get value use one of a->GetValue...(...) functions
			//To get value type one can use GetValueType(...) functions:			
			cout<<"row: "<<rowI<<" column: "<<colI<<" value: "<< a->GetValueDouble(rowI, colI) 
			    << " is it double: "<< (bool)(a->GetValueType(colI) == ConstantsTypeColumn::cDoubleColumn) <<endl;
			
		}
	}
		
	//There are a lot of GetValue... overloads
	// 
	//Each type of GetValue function has 4 overloads:
	//GetVelue...(size_t columnIndex);
	//GetVelue...(size_t rowIndex, size_t columnIndex);
	//GetVelue...(string columnName);
	//GetVelue...(size_t rowIndex, string columnName);
	//
	//The types correspond to ccdb types:
	// string         GetValue(...)
	// int            GetValueInt(...)
	// unsigned int   GetVelueUInt(...)
	// double         GetVelueDouble(...)
	// long           GetVelueLong(...)
	// unsigned long  GetVelueULong(...)
	// bool           GetVelueBool(...)
	
	// So the result of next function calls results should be equal
	cout<<endl<<"Using different versions of GetValueDouble function"<<endl;
	cout<<"row 0, column 1(named 'y')"<<endl;
	cout<<"GetValueDouble(size_t columnIndex)                 : "<< a->GetValueDouble(1)<<endl;
	cout<<"GetValueDouble(size_t rowIndex, size_t columnIndex): "<< a->GetValueDouble(0, 1)<<endl;
	cout<<"GetValueDouble(string columnName)                  : "<< a->GetValueDouble("y")<<endl;
	cout<<"GetValueDouble(size_t rowIndex, string columnName) : "<< a->GetValueDouble(0, "y")<<endl;


	// GetVelue (without type after) returns string representation of data. 
	// It is how data is stored in the DB
	cout<<endl<<"String stored in db is: '"<< a->GetValue("y")<<"'"<< endl;
	
}
