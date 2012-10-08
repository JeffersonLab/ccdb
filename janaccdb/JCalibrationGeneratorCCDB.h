#ifndef JCalibrationGeneratorCCDB_h__
#define JCalibrationGeneratorCCDB_h__

#include <string>
#include <iostream>
#include <memory>

#include <JANA/jerror.h>
#include <JANA/JCalibrationGenerator.h>
#include <CCDB/CalibrationGenerator.h>
#include "JCalibrationCCDB.h"


// Place everything in JANA namespace
namespace jana
{

    class JCalibrationGeneratorCCDB: public JCalibrationGenerator
    {
    public:
        
        /** @brief default ctor */
        JCalibrationGeneratorCCDB():
			mGenerator(new ccdb::CalibrationGenerator())
		{	
		}

        
		/** @brief destructor */
        virtual ~JCalibrationGeneratorCCDB(){}

        
		/** @brief Get string indicating type of calibration this handles
         *
         * @return string with desctiption
         */
        const char* Description(){return "JCalibration using CCDB for MySQL and SQLite databases";}

        
		/** @brief  Test probability of opening the given calibration
         *
         * @parameter [in] url in form "mysql://username@pass:host:port database_name"
         * @parameter [in] run number
         * @parameter [in] name of the variation
         * @return 0.0 - not openable, 0.99 if openable
         */
        double CheckOpenable(std::string url, int run, std::string context)
        {
			#ifdef CCDB_DEBUG_OUTPUT
			jout<<"CCDB::janaccdb CheckOpenable "<<"url: '"<<url<<"' run: "<<run<< " context: "<<context<<std::endl;
			#endif

			if(ccdb::CalibrationGenerator::CheckOpenable(url)) return 0.99;
            return 0.0;
        }


        /** @brief MakeJCalibration
         *
         * @parameter [in] url in form "mysql://username@pass:host:port database_name"
         * @parameter [in] run number
         * @parameter [in] name of the variation
         * @return JCalibration pointer or null if error
         */
        JCalibration* MakeJCalibration(std::string url, int run, std::string context) ///< Instantiate an JCalibration object
        {
			#ifdef CCDB_DEBUG_OUTPUT
			jout<<"CCDB::janaccdb MakeJCalibration "<<"url: '"<<url<<"' run: "<<run<< " context: "<<context<<std::endl;
			#endif

            return new JCalibrationCCDB(mGenerator->MakeCalibration(url,run,context), url,run,context);
        }

	private:
		std::auto_ptr<ccdb::CalibrationGenerator> mGenerator; ///CCDB calibration generator object
    };
	

} // Close JANA namespace
#endif // JCalibrationGeneratorCCDB_h__