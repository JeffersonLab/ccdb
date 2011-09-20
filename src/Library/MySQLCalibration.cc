#include "UserAPI/DMySQLCallibration.h"
#include "Providers/DMySQLDataProvider.h"
#include "DPathUtils.h"
#include <stdexcept>
#include <assert.h>

namespace ccdb
{


//______________________________________________________________________________
DMySQLCalibration::DMySQLCalibration()
{
	
	
	
}
//______________________________________________________________________________
DMySQLCalibration::DMySQLCalibration( int defaultRun, string defaultVariation/*="default"*/ )
    :DCalibration(defaultRun,defaultVariation)
{
    //


}



//______________________________________________________________________________
DMySQLCalibration::~DMySQLCalibration()
{
    
}


//______________________________________________________________________________
bool DMySQLCalibration::Connect( std::string connectionString )
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
	 * @see DMySQLCalibration
	 * mysql://<username>:<password>@<mysql.address>:<port> <database>
	 *
	 * @see DFileCalibration
	 * file://<path to the Calib parent directory>
	 * 
	 * @param connectionString the Connection String
	 * @return true if connected
	 */

    //Create provider if needed
    if(mProvider == NULL)
    {
        if(!mProviderIsLocked)
        {
            mProvider = new DMySQLDataProvider();
        }
        else
        {
            //Invalid DMySQLCalibration usage 
            throw std::logic_error((const char*)ERRMSG_INVALID_CONNECT_USAGE);
        }
    }

    //Maybe we are connected?
    if(mProvider->IsConnected())
    {
        //But where we connected to?
        if(mProvider->GetConnectionString() == connectionString)
        {
            return true;
        }
        else
        {
            //The connection is open to another source. Invalid DMySQLCalibration usage 
            throw std::logic_error(ERRMSG_CONECTED_TO_ANOTHER);
        }
    }

    //Ok at this point we have not connected provider
    //but can we connect or not?
    if(mProviderIsLocked)
    {
        throw std::logic_error(ERRMSG_CONECT_LOCKED);
    }
    
    return mProvider->Connect(connectionString);

    //TODO decide maybe to throw an exception here?
}


//______________________________________________________________________________
void DMySQLCalibration::Disconnect()
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
        throw std::logic_error(ERRMSG_CONECT_LOCKED); //TODO ERRMSG_DISCONECT_LOCKED
    }

    mProvider->Disconnect();
}


//______________________________________________________________________________
bool DMySQLCalibration::IsConnected()
{
    /** @brief indicates ether the connection is open or not
	 * 
	 * @return true if  connection is open
	 */
    return mProvider->IsConnected();

}

}

