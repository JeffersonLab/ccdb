#ifndef _JCalibrationCCDB_
#define _JCalibrationCCDB_

#include <exception>
#include <string>
#include <vector>
#include <map>

#include <JANA/jerror.h>
#include <JANA/JCalibration.h>
#include <UserAPI/DMySQLCalibration.h>
#include "DMySQLCalibration.h"

// Place everything in JANA namespace
namespace jana
{

    class JCalibrationCCDB : public JCalibration
    {
    public:
        JCalibrationCCDB(string url, int run, string context="default");
        virtual ~JCalibrationCCDB();
        virtual const char* className(void){return static_className();}
        static const char* static_className(void){return "JCalibrationCCDB";}

        bool GetCalib(string namepath, map<string, string> &svals, int event_number=0);
        bool GetCalib(string namepath, vector< map<string, string> > &vsvals, int event_number=0);
        void GetListOfNamepaths(vector<string> &namepaths);
        
    private:
        JCalibrationCCDB(); // prevent use of default constructor

        ccdb::DMySQLCalibration * mCalibration;
        std::string mConnectionString;
    };

} // Close JANA namespace

#endif // _JCalibrationCCDB_
