#include <CCDB/Calibration.h>
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
	//Create calibraion object
	//auto_ptr<Calibration> calib((Calibration*)new SQLiteCalibration(/*run = */ 0, "default", 0));
	SQLiteCalibration *calib = new SQLiteCalibration(100);
    
    //get some connection string
    
    string connection_str = create_connection_string();    
    if (!connection_str.size())
    {
		cout<<"No connection string"<<endl;
		return 1;
	}
	cout<<"Connecting to "<<connection_str<<endl;
	
	//connect
	int result = calib->Connect(connection_str);
	cout<<"result is"<<result<<endl;
	//get data
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
}
