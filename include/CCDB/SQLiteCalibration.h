#ifndef DSQLiteCalibration_h
#define DSQLiteCalibration_h

#include <string>
#include "CCDB/Calibration.h"

using namespace std;

namespace ccdb
{

class SQLiteCalibration: public Calibration
{
    
public:
    /** @brief Ctor takes default run number and default variation
	 *
	 *  The default run number and default variation are used when no run or variation
	 *  is explicitly defined in user request. 
	 *
	 * @param defaultRun       [in] Sets default run number
	 * @param defaultVariation [in] Sets default variation
	 */
    SQLiteCalibration(int defaultRun, string defaultVariation="default", time_t defaultTime=0);

	/** @brief Just a default ctor 
	 */
	SQLiteCalibration();

	/** @brief    ~DSQLiteCalibration
	 *
	 * @return   
	 */
	virtual ~SQLiteCalibration();

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
    SQLiteCalibration(const SQLiteCalibration& rhs);
    SQLiteCalibration& operator=(const SQLiteCalibration& rhs);
};

}

#endif // DMySQLCallibration_h
