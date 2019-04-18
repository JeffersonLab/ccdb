#include <stdexcept>
#include <assert.h>

#include "CCDB/SQLiteCalibration.h"
#include "CCDB/Providers/SQLiteDataProvider.h"
#include "CCDB/Helpers/PathUtils.h"

namespace ccdb
{


//______________________________________________________________________________
SQLiteCalibration::SQLiteCalibration()
{	
}

//______________________________________________________________________________
SQLiteCalibration::SQLiteCalibration( int defaultRun, string defaultVariation/*="default"*/ , time_t defaultTime/*=0*/ )
    :Calibration(defaultRun,defaultVariation, defaultTime)
{
}


//______________________________________________________________________________
SQLiteCalibration::~SQLiteCalibration()
{   
}


//______________________________________________________________________________
bool SQLiteCalibration::Connect( std::string connectionString )
{
    /**
	 * @brief Connects to database using connection string
	 * 
	 * Connects to database using connection string
	 * the Connection String generally has form: 
	 * <type>://<needed information to access data>
	 *
	 * The examples of the Connection Strings are:
	 *
	 * @see DSQLiteCalibration
	 * mysql://<username>:<password>@<mysql.address>:<port> <database>
	 *
	 * @see DFileCalibration
	 * file://<path to the Calib parent directory>
	 * 
	 * @param connectionString the Connection String
	 * @return true if connected
	 */
    Lock();

    UpdateActivityTime();

    //Create provider if needed
    if(mProvider == NULL)
    {
        if(!mProviderIsLocked)
        {
            mProvider = new SQLiteDataProvider();
        }
        else
        {
            Unlock();
            //Invalid DSQLiteCalibration usage 
            throw std::logic_error((const char*)ERRMSG_INVALID_CONNECT_USAGE);
        }
    }

    //Maybe we are connected?
    if(mProvider->IsConnected())
    {
        Unlock();

        //But where we connected to?
        if(mProvider->GetConnectionString() == connectionString)
        {   
            return true;
        }
        else
        {
            //The connection is open to another source. Invalid DSQLiteCalibration usage 
            throw std::logic_error(ERRMSG_CONNECTED_TO_ANOTHER);
        }
    }

    //Ok at this point we have not connected provider
    //but can we connect or not?
    if(mProviderIsLocked)
    {
        Unlock();
        throw std::logic_error(ERRMSG_CONNECT_LOCKED);
    }

    bool result = mProvider->Connect(connectionString);
    Unlock();
    return result;
    //TODO decide maybe to throw an exception here?
}


//______________________________________________________________________________
void SQLiteCalibration::Disconnect()
{
    /**
	 * @brief closes connection to data
	 * Closes connection to data. 
	 * If underlayed @see DProvider* object is "locked"
	 * (user could check this by 
	 * 
	 */
    //Ok at this point we have not connected provider
    //but can we connect or not?
    if(mProviderIsLocked)
    {
        throw std::logic_error(ERRMSG_CONNECT_LOCKED); //TODO ERRMSG_DISCONECT_LOCKED
    }

    mProvider->Disconnect();
}


//______________________________________________________________________________
bool SQLiteCalibration::IsConnected()
{
    /** @brief indicates ether the connection is open or not
	 * 
	 * @return true if  connection is open
	 */
    if(mProvider==NULL) return false;
    return mProvider->IsConnected();
}

}

