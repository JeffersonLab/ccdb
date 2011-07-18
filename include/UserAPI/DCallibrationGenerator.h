#ifndef DCallibrationGenerator_h
#define DCallibrationGenerator_h
#include "UserAPI/DCallibration.h"
#include <vector>
#include <map>

namespace ccdb
{
class DCalibration;

class DCallibrationGenerator {

public:
	DCallibrationGenerator();
	virtual ~DCallibrationGenerator();
	virtual DCalibration* MakeCalibration(const std::string & connectionString, int run, const std::string& context); ///< Instantiate an JCalibration object (subclass)
	virtual bool CheckOpenable(const std::string &); ///< Instantiate an JCalibration object (subclass)
	 

private:
	virtual DCalibration* MakeMySQLCalibration(const std::string & connectionString, int run, const std::string& context); ///< Instantiate an JCalibration object (subclass)
	DCallibrationGenerator(const DCallibrationGenerator& rhs);
	DCallibrationGenerator& operator=(const DCallibrationGenerator& rhs);
	std::vector<DCallibration *> mCalibrations;					///Created Calibrations
	std::map<std::string, DCallibration*> mCalibrationsByUrl;  ///map of connection string => DCallibration
	std::map<std::string, DDataProvider*> mProvidersByUrl;  ///map of connection string => DCallibration
};

}

#endif // DCallibrationGenerator_h
