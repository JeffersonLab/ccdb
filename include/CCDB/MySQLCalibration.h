#ifndef DMySQLCalibration_h
#define DMySQLCalibration_h

#include <string>
#include "CCDB/Calibration.h"

#define ERRMSG_INVALID_CONNECT_USAGE "Invalid DMySQLCalibration usage. Using DMySQLCalibration::Connect method with provider == NULL and ProviderIsLocked==true." 
#define ERRMSG_CONECTED_TO_ANOTHER "The connection is open to another source. DCalibration is already connected using another connection string" 
#define ERRMSG_CONECT_LOCKED "Can't connect, provider is locked. The provider is in locked state, this means that it is controlled somwere else, and many DCalibrations may relay on it."
using namespace std;

namespace ccdb
{

class MySQLCalibration: public Calibration
{
    
public:
       	/** @brief    DMySQLCalibration
	 *
	 * @return   
	 */
    MySQLCalibration(int defaultRun, string defaultVariation="default");

	/** @brief    DMySQLCalibration
	 *
	 * @return   
	 */
	MySQLCalibration();

	/** @brief    ~DMySQLCalibration
	 *
	 * @return   
	 */
	virtual ~MySQLCalibration();

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
	virtual bool Connect(std::string connectionString);

	/**
	 * @brief closes connection to data
	 * Closes connection to data. 
	 * If underlayed @see DProvider* object is "locked"
	 * (user could check this by 
	 * 
	 */
	virtual void Disconnect();

	/** @brief indicates ether the connection is open or not
	 * 
	 * @return true if  connection is open
	 */
	virtual bool IsConnected();

private:
    MySQLCalibration(const MySQLCalibration& rhs);
    MySQLCalibration& operator=(const MySQLCalibration& rhs);
};

}

#endif // DMySQLCallibration_h
