#include <iostream>
#include <sstream>

#include "CCDB/CalibrationGenerator.h"
#include "CCDB/SQLiteCalibration.h"
#include "CCDB/Providers/SQLiteDataProvider.h"
#include "CCDB/Helpers/TimeProvider.h"
#ifdef CCDB_MYSQL
#include "CCDB/MySQLCalibration.h"
#include "CCDB/Providers/MySQLDataProvider.h"
#endif //CCDB_MYSQL

using namespace std;

namespace ccdb
{


//______________________________________________________________________________
Calibration* CalibrationGenerator::CreateCalibration(const std::string & connectionString, int run, const std::string& variation, const time_t time )
{
	/** @brief Creates @see Calibration by run number and desirable variation
	 *
     * @parameter [in] connectionString - Connection string to the data source
	 * @parameter [in] int run - run number
	 * @parameter [in] variation - desirable variation
	 * @parameter [in] time - default time of constants
	 * @return Calibration*
	 */


	//is it sqlite or mysql
	bool isMySql = false; //if false SQlite provider is used		
	if(connectionString.find("mysql://")==0)
	{		
		isMySql = true;  //It is mysql
		
		#ifndef CCDB_MYSQL
		throw std::logic_error("Cannot be used with MySQL database. CCDB was compiled without MySQL support! Recompile CCDB using with-mysql=true flag. The connection string: " + connectionString);
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
	
	//now we create calibration
	Calibration * calib = CreateCalibration(isMySql, run, variation, time);    

    //Connect!
    if(!calib->Connect(connectionString))
    {
        string message = GetConnectionErrorMessage(calib);
        throw std::logic_error(message);
    }

	return calib;
}
    
//______________________________________________________________________________
bool CalibrationGenerator::CheckOpenable( const std::string & str)
{
    //Check through known connections
	#ifdef CCDB_MYSQL
	if(str.find("mysql://")== 0) return true;
	#endif

	if(str.find("sqlite://")== 0) return true;
    return false;
}


//______________________________________________________________________________
CalibrationGenerator::CalibrationGenerator()
{
    mMaxInactiveTime = 0; //Disable inactive check
    mInactivityCheckInterval = 100;
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
	string calibHash = GetCalibrationHash(connectionString, run, variation, time);

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
		throw std::logic_error("Cannot be used with MySQL database. CCDB was compiled without MySQL support! Recompile CCDB using with-mysql=true flag. The connection string: " + connectionString);
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
	
	//now we create calibration
	Calibration * calib = CreateCalibration(isMySql, run, variation, time);

    //Connect!
    if(!calib->Connect(connectionString))
    {
        string message = GetConnectionErrorMessage(calib);
        throw std::logic_error(message);
    }

	//add it to arrays
	mCalibrationsByHash[calibHash] = calib;
	mCalibrations.push_back(calib);

	return calib;
}


//______________________________________________________________________________
Calibration* CalibrationGenerator::CreateCalibration( bool isMySQL, int run, const std::string& variation, const time_t time )
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
void CalibrationGenerator::UpdateInactivity()
{
    /** @brief Checks the time of last activity of Calibrations and disconnects
     *         and closes ones that have inactivity longer than @see SetMaxInactiveTime
     * 
     *  If user would like to use his own timer (or event) to check for inactive connections
     *  He/she should set SetUseInactiveCheckTimer(false) and call UpdateInactivity manually
     */

    if(mMaxInactiveTime==0) return;

    time_t now = ccdb::TimeProvider::GetUnixTimeStamp(ccdb::ClockSources::Monotonic);

    //Maybe we may skip the current check
    if(mInactivityCheckInterval!=0)
    {
        if(now - mLastInactivityCheckTime < mInactivityCheckInterval) return;
        mLastInactivityCheckTime = now;
    }

    //Lets iterate all of them then
    for (size_t i=0; i<=mCalibrations.size(); i++)
    {
        Calibration* cal = mCalibrations[i];

        if(!cal->IsConnected()) continue;
        if(now - cal->GetLastActivityTime() > mMaxInactiveTime) cal->Disconnect();
    }
}

std::string CalibrationGenerator::GetConnectionErrorMessage( Calibration * calib )
{
    DataProvider* provider = calib->GetProvider();
    string message("CONNECTION ERROR. ");

    if(provider == NULL)
    {
        message += "Can't failed to create database Provider";
    }
    else
    {
        //error handling...
        vector<CCDBError *> errors = provider->GetErrors();
        for(int i=0; i< errors.size(); i++)
        {
            std::stringstream ss;

            ss << endl << "Key: '"<< errors[i]->GetErrorKey()<<"'  Message: '" << errors[i]->GetMessage() << "'" << std::endl;
            ss << "Source: '" << errors[i]->GetSource() << "'" << std::endl;
            ss << "Description: " << errors[i]->GetDescription() << "'" << endl;
            message += ss.str();
        }
    }

    return message;
}

}

