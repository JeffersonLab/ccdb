#ifndef DMySQLCalibration_h
#define DMySQLCalibration_h

#include <string>
#include "CCDB/Calibration.h"

using namespace std;

namespace ccdb
{

class MySQLCalibration: public Calibration
{
    
public:
     /** @brief Ctor takes default run number and default variation
	 *
	 *  The default run number and default variation are used when no run or variation
	 *  is explicitly defined in user request. 
	 *
	 * @param defaultRun       [in] Sets default run number
	 * @param defaultVariation [in] Sets default variation
	 * @param defaultTime      [in] Sets default time for the coefficitnts
	 */
    MySQLCalibration(int defaultRun, string defaultVariation="default", time_t defaultTime=0);

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
     * @see MySQLCalibration
     * mysql://<username>:<password>@<mysql.address>:<port>/<database>
     *
     * @see SQLiteCalibration
     * sqlite://<path to sqlite file>
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
