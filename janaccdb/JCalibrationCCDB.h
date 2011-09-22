#ifndef _JCalibrationCCDB_
#define _JCalibrationCCDB_

#include <exception>
#include <string>
#include <vector>
#include <map>

#include <JANA/jerror.h>
#include <JANA/JCalibration.h>
#include <UserAPI/MySQLCalibration.h>
#include <JANA/JStreamLog.h>

using namespace std;
using namespace jana;

// Place everything in JANA namespace
namespace jana
{

    class JCalibrationCCDB : public JCalibration
    {
    public:

        /** @brief    Constructor
         *
         * @parameter [in] url - connection string. like mysql://...
         * @parameter [in] run - run number
         * @parameter [in] context - variation
         */
        JCalibrationCCDB(string url, int run, string context="default"):
	        JCalibration(url, run, context)
	    {
		    mCalibration = new ccdb::MySQLCalibration(run, context);
		    try
            {
                if(!mCalibration->Connect(url))
                {
                    jerr<<"Cannot connect to MySQL Database"<<endl;
                }

            }
            catch (...)
            {
    	        throw;
            }
        }


        /** @brief   destructor
         */
        virtual ~JCalibrationCCDB()
        {
            if(mCalibration!=NULL) delete mCalibration;
        }
        

        /** @brief gets a className
         */
        virtual const char* className(void)
        {
            return static_className();
        }


        /** @brief gets a className static version of function
         */
        static const char* static_className(void)
        {
            return "JCalibrationCCDB";
        }


        /** @brief    get calibration constants
         *
         * @parameter [in]  namepath - full resource string
         * @parameter [out] svals - data to be returned
         * @parameter [in]  event_number - optional parameter of event number
         * @return true if constants were read
         */
        bool GetCalib(string namepath, map<string, string> &svals, int event_number=0)
        {
            //
            try
            {   
                return mCalibration->GetCalib(svals, namepath);
            }
            catch (std::exception)
            {
                return false;
            }
        }


         /** @brief    get calibration constants
         *
         * @parameter [in]  namepath - full resource string
         * @parameter [out] vsvals - data to be returned
         * @parameter [in]  event_number - optional parameter of event number
         * @return true if constants were read
         */
        bool GetCalib(string namepath, vector< map<string, string> > &vsvals, int event_number=0)
        {
            //
            try
            {   
                return mCalibration->GetCalib(vsvals, namepath);
            }
            catch (std::exception)
            {
                return false;
            }
        }


        /** @brief    GetListOfNamepaths
         *
         * @parameter [in] vector<string> & namepaths
         * @return   void
         */
        void GetListOfNamepaths(vector<string> &namepaths)
        {
            
            //
            try
            {  
                mCalibration->GetListOfNamepaths(namepaths);
            }
            catch (std::exception ex)
            {
                jerr<<ex.what()<<endl;
            }
        }


        
    private:
        JCalibrationCCDB(); // prevent use of default constructor

        ccdb::MySQLCalibration * mCalibration;  //Underlaying CCDB user api class 
        //std::string mConnectionString;           // connection string
    };

} // Close JANA namespace

#endif // _JCalibrationCCDB_
