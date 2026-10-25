#include <iostream>
#include <sstream>
#include <memory>
#include <algorithm>

#include "CalibrationGenerator.h"
#include "SQLiteCalibration.h"
#include "Providers/SQLiteDataProvider.h"
#include "Helpers/TimeProvider.h"
#include "Helpers/StringUtils.h"
#ifdef CCDB_MYSQL
#include "CCDB/MySQLCalibration.h"
#include "CCDB/Providers/MySQLDataProvider.h"
#endif //CCDB_MYSQL

using namespace std;

namespace ccdb
{
    //______________________________________________________________________________
    Calibration* CalibrationGenerator::CreateCalibration(const std::string & connectionString, int run, const std::string& variation, const time_t time )
    {
        /** @brief Creates @see Calibration by run number and desirable variation
         *
         * @parameter [in] connectionString - Connection string to the data source
         * @parameter [in] int run - run number
         * @parameter [in] variation - desirable variation
         * @parameter [in] time - default time of constants
         * @return Calibration*
         */


        //is it sqlite or mysql
        bool isMySql = false; //if false SQlite provider is used
        if(connectionString.find("mysql://")==0)
        {
            isMySql = true;  //It is mysql

            #ifndef CCDB_MYSQL
            throw std::logic_error("Cannot be used with MySQL database. CCDB was compiled without MySQL support! Recompile CCDB using with-mysql=true flag. The connection string: " + StringUtils::MaskPassword(connectionString));
            #endif //CCDB_MYSQL
        }
        else
        {
            //It should be sqlite, but lets check then...
            if(connectionString.find("sqlite://")!=0)
            {
                //something wrong here!!!
                throw std::logic_error("Unknown connection string type. mysql:// and sqlite:// are only known types now. The connection string: " + StringUtils::MaskPassword(connectionString));
            }
        }

        //now we create calibration
        std::unique_ptr<Calibration> calib(CreateCalibration(isMySql, run, variation, time));

        //Connect! (throws on failure, unique_ptr then deletes the object)
        if(!calib->Connect(connectionString))
        {
            string message = GetConnectionErrorMessage(calib.get());
            throw std::logic_error(message);
        }

        return calib.release();
    }

    //______________________________________________________________________________
    bool CalibrationGenerator::CheckOpenable( const std::string & str)
    {
        //Check through known connections
        #ifdef CCDB_MYSQL
        if(str.find("mysql://")== 0) return true;
        #endif

        if(str.find("sqlite://")== 0) return true;
        return false;
    }


    //______________________________________________________________________________
    CalibrationGenerator::CalibrationGenerator()
    {
        mMaxInactiveTime = 0; //Disable inactive check
        mInactivityCheckInterval = 100;
        time_t now = ccdb::TimeProvider::GetUnixTimeStamp(ccdb::ClockSources::Monotonic);
        mLastInactivityCheckTime = now;
    }


    //______________________________________________________________________________
    CalibrationGenerator::~CalibrationGenerator()
    {
        // Calibrations may be owned and deleted by the users of MakeCalibration (e.g. JANA wrappers),
        // so they are not deleted here. Only their connections are closed.
        std::lock_guard<std::mutex> lock(mMutex);
        for (auto calib : mCalibrations)
        {
            calib->mGenerator = nullptr;
            try {
                if(!calib->GetProviderIsLocked() && calib->IsConnected()) calib->Disconnect();
            }
            catch (const std::exception& ex) {
                std::cerr << "CCDB warning: failed to disconnect calibration: " << ex.what() << std::endl;
            }
        }
        mCalibrations.clear();
        mCalibrationsByHash.clear();
    }


    //______________________________________________________________________________
    void CalibrationGenerator::DeleteCalibrations()
    {
        std::vector<Calibration *> calibrations;
        {
            std::lock_guard<std::mutex> lock(mMutex);
            calibrations.swap(mCalibrations);
            mCalibrationsByHash.clear();
            for (auto calib : calibrations) calib->mGenerator = nullptr;
        }

        for (auto calib : calibrations) delete calib;
    }


    //______________________________________________________________________________
    void CalibrationGenerator::ForgetCalibration(Calibration* calib)
    {
        std::lock_guard<std::mutex> lock(mMutex);
        mCalibrations.erase(std::remove(mCalibrations.begin(), mCalibrations.end(), calib), mCalibrations.end());
        for (auto it = mCalibrationsByHash.begin(); it != mCalibrationsByHash.end(); )
        {
            if (it->second == calib) it = mCalibrationsByHash.erase(it);
            else ++it;
        }
    }


    //______________________________________________________________________________
    Calibration* CalibrationGenerator::MakeCalibration( const std::string & connectionString, int run, const std::string& variation, const time_t time )
    {
        /** @brief Creates @see Calibration by connectionString, run number and desirable variation
         *
         * @parameter [in] connectionString - Connection string to the data source
         * @parameter [in] int run - run number
         * @parameter [in] variation - desirable variation
         * @parameter [in] time - default time of constants
         * @return Calibration*
         */

        //hash of requested variation
        string calibHash = GetCalibrationHash(connectionString, run, variation, time);

        // Lookup, creation and registration must be atomic: concurrent callers would otherwise
        // corrupt the containers or open duplicate connections for the same key
        std::lock_guard<std::mutex> lock(mMutex);

        //first we look maybe we already have such a calibration
        if(mCalibrationsByHash.count(calibHash))
        {
            return mCalibrationsByHash[calibHash];
        }

        //is it sqlite or mysql
        bool isMySql = false; //if false SQlite provider is used
        if(connectionString.find("mysql://")==0)
        {
            isMySql = true;  //It is mysql

            #ifndef CCDB_MYSQL
            throw std::logic_error("Cannot be used with MySQL database. CCDB was compiled without MySQL support! Recompile CCDB using with-mysql=true flag. The connection string: " + StringUtils::MaskPassword(connectionString));
            #endif //CCDB_MYSQL
        }
        else
        {
            //It should be sqlite, but lets check then...
            if(connectionString.find("sqlite://")!=0)
            {
                //something wrong here!!!
                throw std::logic_error("Unknown connection string type. mysql:// and sqlite:// are only known types now. The connection string: " + StringUtils::MaskPassword(connectionString));
            }
        }

        //now we create calibration
        std::unique_ptr<Calibration> newCalib(CreateCalibration(isMySql, run, variation, time));

        //Connect! (throws on failure, unique_ptr then deletes the object)
        if(!newCalib->Connect(connectionString))
        {
            string message = GetConnectionErrorMessage(newCalib.get());
            throw std::logic_error(message);
        }

        //add it to arrays
        Calibration * calib = newCalib.release();
        calib->mGenerator = this;
        mCalibrationsByHash[calibHash] = calib;
        mCalibrations.push_back(calib);

        return calib;
    }


    //______________________________________________________________________________
    Calibration* CalibrationGenerator::CreateCalibration( bool isMySQL, int run, const std::string& variation, const time_t time )
    {

        if (isMySQL)
        {
            #ifdef CCDB_MYSQL
                return new MySQLCalibration(run, variation, time);
            #else
                return NULL;
            #endif //CCDB_MYSQL
        }
        else
        {
            return new SQLiteCalibration(run, variation, time);
        }
    }


    //______________________________________________________________________________
    string CalibrationGenerator::GetCalibrationHash( const std::string & connectionString, int run, const std::string& variation, const time_t time )
    {
         //gets string hash based on  connectionString, run, and variation
         //
         //The hash is used for storing Calibrations in calibrations hash table
         //so if user asks DCalibration which is already exists a new DCalibration
         //will not be created once again but already created DCalibration is returned;

        //right now our hash will be just a summ of strings

        // A separator that cannot appear in the parts keeps e.g. (run=12, variation="3x") and
        // (run=123, variation="x") apart
        const char separator = '\x1f';
        ostringstream strstrm;
        strstrm<<connectionString<<separator<<run<<separator<<variation<<separator<<time;
        return strstrm.str();
    }


    //______________________________________________________________________________
    void CalibrationGenerator::UpdateInactivity()
    {
        /** @brief Checks the time of last activity of Calibrations and disconnects
         *         and closes ones that have inactivity longer than @see SetMaxInactiveTime
         *
         *  If user would like to use his own timer (or event) to check for inactive connections
         *  He/she should set SetUseInactiveCheckTimer(false) and call UpdateInactivity manually
         */

        std::lock_guard<std::mutex> lock(mMutex);

        if(mMaxInactiveTime==0) return;

        time_t now = ccdb::TimeProvider::GetUnixTimeStamp(ccdb::ClockSources::Monotonic);

        //Maybe we may skip the current check
        if(mInactivityCheckInterval!=0)
        {
            if(now - mLastInactivityCheckTime < mInactivityCheckInterval) return;
            mLastInactivityCheckTime = now;
        }

        //Lets iterate all of them then
        for (size_t i=0; i<mCalibrations.size(); i++)
        {
            if(!mCalibrations[i]->IsConnected()) continue;
            if(now - mCalibrations[i]->GetLastActivityTime() > mMaxInactiveTime) mCalibrations[i]->Disconnect();
        }
    }

    std::string CalibrationGenerator::GetConnectionErrorMessage( Calibration * calib )
    {
        DataProvider* provider = calib->GetProvider();
        string message("CONNECTION ERROR. ");

        return message;
    }

}

