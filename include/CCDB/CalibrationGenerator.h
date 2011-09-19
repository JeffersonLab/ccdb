#ifndef DCallibrationGenerator_h
#define DCallibrationGenerator_h
#include "UserAPI/DCalibration.h"
#include <vector>
#include <map>
#include <stdexcept>

namespace ccdb
{
class DCalibrationGenerator {
public:
	/** @brief   default constructor*/
	DCalibrationGenerator();
	/** @brief destructor	 */
	virtual ~DCalibrationGenerator();

	/** @brief Creates @see DCalibration by connectionString, run number and desirable variation
	 *
	 * @parameter [in] connectionString - Connection string to the data source
	 * @parameter [in] int run - run number
	 * @parameter [in] variation - desirable variation
	 * @return   DCalibration*
	 */
	virtual DCalibration* MakeCalibration(const std::string & connectionString, int run, const std::string& variation); 

	/** @brief    CheckOpenable
	 *
	 * @parameter [in] const std::string &
	 * @return   bool
	 */
	virtual bool CheckOpenable(const std::string &str); ///< Instantiate an JCalibration object (subclass)
    
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
	virtual DCalibration* MakeMySQLCalibration(const std::string & connectionString, int run, const std::string& context); ///< Instantiate an JCalibration object (subclass)
	DCalibrationGenerator(const DCalibrationGenerator& rhs);
	DCalibrationGenerator& operator=(const DCalibrationGenerator& rhs);
	std::vector<DCalibration *> mCalibrations;					///Created Calibrations
	std::map<std::string, DCalibration*> mCalibrationsByHash;    ///map of connection string => DCallibration
	std::map<std::string, DDataProvider*> mProvidersByUrl;      ///map of connection string => DCallibration
};
}

#endif // DCallibrationGenerator_h