#ifndef DCallibrationGenerator_h
#define DCallibrationGenerator_h

#include <vector>
#include <map>
#include <stdexcept>

#include "CCDB/Calibration.h"

namespace ccdb
{
class CalibrationGenerator {
public:
	/** @brief   default constructor*/
	CalibrationGenerator();
	/** @brief destructor	 */
	virtual ~CalibrationGenerator();

	/** @brief Creates @see DCalibration by connectionString, run number and desirable variation
	 *
	 * @parameter [in] connectionString - Connection string to the data source
	 * @parameter [in] int run - run number
	 * @parameter [in] variation - desirable variation
	 * @return   DCalibration*
	 */
	virtual Calibration* MakeCalibration(const std::string & connectionString, int run, const std::string& variation); 

	/** @brief    CheckOpenable
	 *
	 * @parameter [in] const std::string &
	 * @return   bool
	 */
	static bool CheckOpenable(const std::string &str); ///< Instantiate an JCalibration object (subclass)
    
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
    virtual string GetCalibrationHash(const std::string & connectionString, int run, const std::string& variation);
private:	
	CalibrationGenerator(const CalibrationGenerator& rhs);
	CalibrationGenerator& operator=(const CalibrationGenerator& rhs);
	std::vector<Calibration *> mCalibrations;					///Created Calibrations
	std::map<std::string, Calibration*> mCalibrationsByHash;    ///map of connection string => DCallibration
	std::map<std::string, DataProvider*> mProvidersByUrl;      ///map of connection string => DCallibration
};
}

#endif // DCallibrationGenerator_h