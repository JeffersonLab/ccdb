/**
 * 	Simpliest example of how to get access to CCDB data
 */

#include <CCDB/Calibration.h>
#include <CCDB/CalibrationGenerator.h>
#include <CCDB/SQLiteCalibration.h>
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
	
	vector<vector<double> > data;
	calib->GetCalib(data, "/test/test_vars/test_table");
		
	//iterate data and print
	for(int row = 0; row < data.size(); row++)
	{
		for (int col = 0; col< data[0].size(); col++)
		{
			cout<< data[row][col] << "\t";
		}
		cout<<endl;
	}
	
	//The data could be
	//vector<double> data;          =>  data[1] - row index 0, col index 1
	//vector<vector<double> >       =>  data[0][1] - row index 0, col index 1
	//vector<map<string, double> >  =>  data[0]["y"] - row index 0, "y" column
	//map<string, double> >         =>  data["y"] - row index 0, "y" column	
	//Type is int, string, double
	//
	//for more sophisticated data manipulation, like getting column types, 
	//see assignments.cc example
}
