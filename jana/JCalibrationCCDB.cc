#include "JCalibrationCCDB.h"

//______________________________________________________________________________
jana::JCalibrationCCDB::JCalibrationCCDB( string url, int run, string context/*="default"*/ )
{
    //constructor 

    mCalibration = new DMySQLCalibration(run, context);
    try
    {
        mCalibration->Connect(url);
    }
    catch (...)
    {
    	throw;
    }
}

//______________________________________________________________________________
bool jana::JCalibrationCCDB::GetCalib( string namepath, map<string, string> &svals, int event_number/*=0*/ )
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

//______________________________________________________________________________
bool jana::JCalibrationCCDB::GetCalib( string namepath, vector< map<string, string> > &vsvals, int event_number/*=0*/ )
{
    //
    mCalibration->GetCalib(svals, namepath);
}
