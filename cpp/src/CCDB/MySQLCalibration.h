#ifndef DMySQLCalibration_h
#define DMySQLCalibration_h

#include <string>
#include "CCDB/Calibration.h"

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
        explicit MySQLCalibration(int defaultRun, string defaultVariation="default", time_t defaultTime=0);

        /** @brief    DMySQLCalibration
         *
         * @return
         */
        MySQLCalibration();

        /** @brief    ~DMySQLCalibration
         *
         * @return
         */
        ~MySQLCalibration() override;

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
        bool Connect(std::string connectionString) override;

        /**
         * @brief closes connection to data
         * Closes connection to data.
         * If underlayed @see DProvider* object is "locked"
         * (user could check this by
         *
         */
        void Disconnect() override;

        /** @brief indicates ether the connection is open or not
         *
         * @return true if  connection is open
         */
        bool IsConnected() override;

    private:
        MySQLCalibration(const MySQLCalibration& rhs);
        MySQLCalibration& operator=(const MySQLCalibration& rhs);
    };

}

#endif // DMySQLCallibration_h
