#include <iostream>
#include <sstream>

#include "CCDB/CalibrationGenerator.h"
#include "CCDB/MySQLCalibration.h"
#include "CCDB/SQLiteCalibration.h"
#include "CCDB/Providers/MySQLDataProvider.h"
#include "CCDB/Providers/SQLiteDataProvider.h"

using namespace std;

namespace ccdb
{

//______________________________________________________________________________
CalibrationGenerator::CalibrationGenerator()
{
}


//______________________________________________________________________________
CalibrationGenerator::~CalibrationGenerator()
{
}


//______________________________________________________________________________
Calibration* CalibrationGenerator::MakeCalibration( const std::string & connectionString, int run, const std::string& context )
{
	//hash of requested variation
	string calibHash = GetCalibrationHash(connectionString, run, context);

	//first we look maybe we already have such a calibration
	if(mCalibrationsByHash.find(calibHash) != mCalibrationsByHash.end())
	{
		return mCalibrationsByHash[calibHash];
	}

	//is it sqlite or mysql
	bool isMySql = false; //if false SQlite provider is used		
	if(connectionString.find("mysql://")==0)
	{		
		isMySql = true;  //It is mysql
	}
	else
	{
		//It should be sqlite, but lets check then...
		if(connectionString.find("sqlite://")!=0)
		{	
			//something wrong here!!!
			throw std::logic_error("Unknown connection string type. mysql:// and sqlite:// are only known types now. The connection string: " + connectionString);
		}
	}

	//Ok, we have to create calibration
	//but lets see, maybe we at least have a DataProvider for this connectionString
	DataProvider *provider = NULL;
	if(mProvidersByUrl.find(connectionString) != mProvidersByUrl.end())
	{
		provider = static_cast<DataProvider *>(mProvidersByUrl[connectionString]);

		//lets see the provider is connected... if not it is useless
		if(provider!= NULL && !provider->IsConnected()) provider = NULL;
	}

	//Create a new provider if no old one
	if(provider == NULL)
	{
		provider =  (isMySql)?  (DataProvider *)new MySQLDataProvider() : (DataProvider *)new SQLiteDataProvider();

		//and connect it
		if(!provider->Connect(connectionString))
		{
			//error hangling...
			vector<CCDBError *> errors = provider->GetErrors();
			string message;
			for(int i=0; i< errors.size(); i++)
			{
				message = errors[i]->GetMessage() + " in ";
				message += errors[i]->GetErrorKey() + " in ";
				message += errors[i]->GetSource() + " in ";
				message += errors[i]->GetDescription() + " in ";
			}
			delete provider;
			throw std::logic_error(message.c_str());
		}

		mProvidersByUrl[connectionString] = provider;
	}
	
	//now we create calibration
	Calibration * calib = (isMySql)? static_cast<Calibration*>(new MySQLCalibration()): static_cast<Calibration*>(new SQLiteCalibration());
	calib->UseProvider(provider, true);

	//add it to arrays
	mCalibrationsByHash[calibHash] = calib;
	mCalibrations.push_back(calib);

	return calib;
}


//______________________________________________________________________________
string CalibrationGenerator::GetCalibrationHash( const std::string & connectionString, int run, const std::string& variation )
{   
     //gets string hash based on  connectionString, run, and variation
     //
     //The hash is used for storing Calibrations in calibrations hash table
     //so if user asks DCalibration which is already exists a new DCalibration 
     //will not be created once again but already created DCalibration is returned;

    //right now our hash will be just a summ of strings
    ostringstream strstrm;
    strstrm<<connectionString<<run<<variation;
    return strstrm.str();
}


//______________________________________________________________________________
bool CalibrationGenerator::CheckOpenable( const std::string & str)
{
    //Check through known connections
	if(str.find("mysql://")== 0) return true;
	if(str.find("sqlite://")== 0) return true;
    return false;
}

}

