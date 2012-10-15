#include <iostream>
#include <sstream>

#include "CCDB/CalibrationGenerator.h"
#include "CCDB/SQLiteCalibration.h"
#include "CCDB/Providers/MySQLDataProvider.h"
#include "CCDB/Providers/SQLiteDataProvider.h"

#ifdef CCDB_MYSQL
#include "CCDB/MySQLCalibration.h"
#endif //CCDB_MYSQL

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
Calibration* CalibrationGenerator::MakeCalibration( const std::string & connectionString, int run, const std::string& variation, const time_t time )
{
	/** @brief Creates @see Calibration by connectionString, run number and desirable variation
	 *
	 * @parameter [in] connectionString - Connection string to the data source
	 * @parameter [in] int run - run number
	 * @parameter [in] variation - desirable variation
	 * @parameter [in] time - default time of constants
	 * @return Calibration*
	 */

	//hash of requested variation
	string calibHash = GetCalibrationHash(connectionString, run, variation,time);

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
		
		#ifndef CCDB_MYSQL
		throw std::logic_error("Cannot connect to MySQL database. CCDB was compiled without MySQL support! Recompile CCDB using mysql=1 flag. The connection string: " + connectionString);
		#endif //CCDB_MYSQL
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
			//error handling...
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
	Calibration * calib = CreateCalibration(isMySql, provider, run, variation, time);
	calib->UseProvider(provider, true);

	//add it to arrays
	mCalibrationsByHash[calibHash] = calib;
	mCalibrations.push_back(calib);

	return calib;
}

//______________________________________________________________________________
Calibration* CalibrationGenerator::CreateCalibration( bool isMySQL, DataProvider *prov, int run, const std::string& variation, const time_t time )
{	
	
	if (isMySQL)
	{
		#ifdef CCDB_MYSQL
			return new MySQLCalibration(run, variation, time);
		#else
			return NULL;
		#endif //CCDB_MYSQL
	}
	else
	{
		return new SQLiteCalibration(run, variation, time);
	}
}



//______________________________________________________________________________
string CalibrationGenerator::GetCalibrationHash( const std::string & connectionString, int run, const std::string& variation, const time_t time )
{   
     //gets string hash based on  connectionString, run, and variation
     //
     //The hash is used for storing Calibrations in calibrations hash table
     //so if user asks DCalibration which is already exists a new DCalibration 
     //will not be created once again but already created DCalibration is returned;

    //right now our hash will be just a summ of strings
    ostringstream strstrm;
    strstrm<<connectionString<<run<<variation<<time;
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

