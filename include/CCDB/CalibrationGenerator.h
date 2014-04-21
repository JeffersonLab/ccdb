#ifndef DCallibrationGenerator_h
#define DCallibrationGenerator_h

#include <vector>
#include <map>
#include <stdexcept>
#include <time.h>

#include "CCDB/Calibration.h"

namespace ccdb
{
class CalibrationGenerator {
public:
    
    /** @brief Creates @see Calibration by run number and desirable variation
     *
     * @parameter [in] connectionString - Connection string to the data source
     * @parameter [in] int run - run number
     * @parameter [in] variation - desirable variation
     * @parameter [in] time - default time of constants
     * @return Calibration*
     */
    static Calibration* CreateCalibration(const std::string & connectionString, int run=0, const std::string& variation="default", const time_t time=0);
    
    
    /** @brief Checks if ccdb can work with this datasource (by connection string)
     *
     * @parameter [in] const std::string &
     * @return   true if CCDB can work with it
     */
    static bool CheckOpenable(const std::string &str); ///< Instantiate an JCalibration object (subclass)
    
    
    /** @brief   default constructor*/
    CalibrationGenerator();

    /** @brief destructor	 */
    virtual ~CalibrationGenerator();


    /** @brief Creates @see Calibration by connectionString, run number and desirable variation
     *
     * @parameter [in] connectionString - Connection string to the data source
     * @parameter [in] int run - run number
     * @parameter [in] variation - desirable variation
     * @parameter [in] time - default time of constants
     * @return Calibration*
     */
    virtual Calibration* MakeCalibration(const std::string & connectionString, int run, const std::string& variation, const time_t time=0); 


    /** @brief gets string hash based on  connectionString, run, and variation
     *
     * The hash is used for storing Calibrations in calibrations hash table
     * so if user asks DCalibration which is already exists a new DCalibration 
     * will not be created once again but already created DCalibration is returned;
     * 
     * @parameter [in] connectionString - Connection string to the data source
     * @parameter [in] int run - run number
     * @parameter [in] variation - desirable variation
     * @return   string
     */
    virtual string GetCalibrationHash(const std::string & connectionString, int run, const std::string& variation, const time_t time);

      

    /** @brief Checks the time of last activity of Calibrations and disconnects
     *         and closes ones that have inactivity longer than @see SetMaxInactiveTime
     * 
     *  @seealso GetMaxInactiveTime
     *  @seealso GetInactivityCheckInterval
     */
    void UpdateInactivity();


    /** @brief Maximum inactive time for @see UpdateInactivity function
     *  if 0 inactivity isn't checked by UpdateInactivity
     */
    time_t GetMaxInactiveTime() const { return mMaxInactiveTime; }


    /** @brief Maximum inactive time for @see UpdateInactivity function
     *  if 0 inactivity isn't checked by UpdateInactivity
     */
    void SetMaxInactiveTime(time_t val) { mMaxInactiveTime = val; }


    /** @brief UpdateInactivity is ignored if is called more frequent than mInactivityCheckInterval
     *         if value is 0 - switches off this feature
     */
    time_t GetInactivityCheckInterval() const { return mInactivityCheckInterval; }


     /** @brief UpdateInactivity is ignored if is called more frequent than mInactivityCheckInterval
     *         if value is 0 - switches off this feature
     */
    void SetInactivityCheckInterval(time_t val) { mInactivityCheckInterval = val; }

private:	

    //@parameter [in] connectionString - Connection string to the data source
    static Calibration* CreateCalibration(bool isMySQL, int run, const std::string& variation, const time_t time);

    CalibrationGenerator(const CalibrationGenerator& rhs);
    CalibrationGenerator& operator=(const CalibrationGenerator& rhs);
    static string GetConnectionErrorMessage( Calibration * calib );
    std::vector<Calibration *> mCalibrations;					///Created Calibrations
	std::map<std::string, Calibration*> mCalibrationsByHash;    ///map of connection string => DCallibration
    
	time_t mMaxInactiveTime;                                    ///Max inactive time for calibration secs
    time_t mLastInactivityCheckTime;                            ///Last time of inactivity check from Unix epoch
    time_t mInactivityCheckInterval;                            ///Interval to check inactivity secs
};
}

#endif // DCallibrationGenerator_h
