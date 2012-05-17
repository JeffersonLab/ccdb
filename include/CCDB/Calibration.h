#ifndef DCallibration_h
#define DCallibration_h

#include <string>
#include <map>
#include <vector>

#include "CCDB/Globals.h"
#include "CCDB/Providers/DataProvider.h"
#include "CCDB/PthreadMutex.h"
#include "CCDB/PthreadSyncObject.h"

using namespace std;

namespace ccdb
{

class Calibration {

public:
    Calibration(); ///< Default constructor
    Calibration(int defaultRun, string defaultVariation="default");
    virtual ~Calibration();

    /**
     * @brief Connects to database using connection string
     *
     * Connects to database using connection string
     * the Connection String generally has form:
     * <type>://<needed information to access data>
     *
     * The examples of the Connection Strings are:
     *
     * @see DMySQLCalibration
     * mysql://<username>:<password>@<mysql.address>:<port> <database>
     *
     * @see DFileCalibration
     * file://<path to the Calib parent directory>
     *
     * @param connectionString the Connection String
     * @return true if connected
     */
    virtual bool Connect(std::string connectionString) = 0;

    /**
     * @brief closes connection to data
     * Closes connection to data.
     * If underlayed @see DProvider* object is "locked"
     * (user could check this by
     *
     */
    virtual void Disconnect() = 0;

    /**
     * @brief indicates ether the connection is open or not
     *
     * @return true if  connection is open
     */
    virtual bool IsConnected() = 0;

    /** @brief gets DDataProvider* object used for specified DCalibration
    *@returns provider used for specified DCalibration
    */
    DataProvider * GetProvider() const { return mProvider; }


    /** @brief set provider to use.
     * if lockProvider==true, than @see Connect, @see Disconnect and @see SetConnectionString
     * will not affect connection of provider. The provider will not be deleted in destruction.
     * @parameter [in] DDataProvider * provider
     * @parameter [in] bool lockProvider
     * @return   void
     */
    void UseProvider(DataProvider * provider, bool lockProvider=true);

    /** @brief Get constants by namepath
     *
     * This version of function fills values as a Table,
     * vector<map<string, string>> - is vector of rows, each row is a map<header_name, string_cell_value>
     *
     * Namepath is usually is just the data path, like
     * /path/to/data
     * but the full form of request is
     * /path/to/data:run:variation:time
     * request might be shortened. One may skip
     * /path/to/data - just path to date, no run, variation and timestamp specified
     * /path/to/data::mc - no run or date specified.
     * /path/to/data:::2029 - only path and date
     *
     *
     * @parameter [out] values - vector of rows, each row is a map<header_name, string_cell_value>
     * @parameter [in]  namepath - data path. Short /path/to/data .Full format is /path/to/data:run:variation:time
     * @return true if constants were found and filled. false if namepath was not found. raises std::exception if any other error acured.
     */
    virtual bool GetCalib(vector< map<string, string> > &values, const string & namepath);
    virtual bool GetCalib(vector< map<string, double> > &values, const string & namepath);
    virtual bool GetCalib(vector< map<string, int> > &values, const string & namepath);

    /** @brief Get constants by namepath
     *
     * this version of function fills values as a table represented as
     * vector< vector<string> > = vector of rows where each row is a vector of cells
     *
     * @parameter [out] values - vector of rows, each row is a map<header_name, string_cell_value>
     * @parameter [in]  namepath - data path
     * @return true if constants were found and filled. false if namepath was not found. raises std::exception if any other error acured.
     */
    virtual bool GetCalib(vector< vector<string> > &values, const string & namepath);
    virtual bool GetCalib(vector< vector<double> > &values, const string & namepath);
    virtual bool GetCalib(vector< vector<int> >   &values, const string & namepath);

    /** @brief Get constants by namepath
     *
     * this version of function fills values as one row
     * where map<header_name, string_cell_value>
     *
     * @parameter [out] values - as  map<header_name, string_cell_value>
     * @parameter [in]  namepath - data path
     * @return true if constants were found and filled. false if namepath was not found. raises std::exception if any other error acured.
     */
    virtual bool GetCalib(map<string, string> &values, const string & namepath);
    virtual bool GetCalib(map<string, double> &values, const string & namepath);
    virtual bool GetCalib(map<string, int> &values, const string & namepath);

    /** @brief Get constants by namepath
     *
     * this version of function fills values as one row as vector<string_values>
     *
     * @parameter [out] values - as vector<string_values>
     * @parameter [in]  namepath - data path
     * @return true if constants were found and filled. false if namepath was not found. raises std::exception if any other error acured.
     */
    virtual bool GetCalib(vector<string> &values, const string & namepath);
    virtual bool GetCalib(vector<double> &values, const string & namepath);
    virtual bool GetCalib(vector<int> &values, const string & namepath);

    /** @brief gets connection string which is used for current provider
    *@return mConnectionString
    */
    virtual string GetConnectionString() const;

    /** @brief gets flag that indicate that DProvider* is locked
    * For USER, If this function return true this means that
    * @see Connect and @see Disconnect and @see SetConnectionString functions will NOT work
    * because the connection to database managed by @see DCalibrationGenerator
    *
    * When this "ProviderIsLocked" happens?
    * - If DCallibration is generated by @see DCallibrationGenerator - it is locked.
    * Everything is managed by the generator. This is a recomended way of creating DCalibration.
    *
    * - If this DCalibration object is created by user, which is NOT recommended but possible,
    * then Underlaying @see DProvider is NOT locked and user can call Connect and Disconnect
    *
    * If user uses DCalibrationGenerator object to obtain DCalibration, this way IS RECOMMENDED,
    * DCalibrationGenerator may use one connection for several different DCalibration objects,
    * In this case "ProviderIsLocked" and user cannot call Connect and disconnet functions.
    *
    *
    *@return True if locked
    */
    bool GetProviderIsLocked() const { return mProviderIsLocked; }

    /** @brief  Gets Default Run
     *
     * @remark There is no SetDefaultRun because it assumed that one part of a program
     * should not change default run for another part of the program and get non determined situation
     *
     * If one need just one table of not default run he could specify it in namepath @see GetCalib
     * If one really need to change default run it the subject of a new DCalibration
     *
     * @return   int
     */
    int GetDefaultRun() const { return mDefaultRun; }

    /** @brief Gets the default variation
     *
     * @remark There is no GetDefaultVariation for the same
     *         reasons as described in @see GetDefaultRun
     * @return   std::string
     */
    std::string GetDefaultVariation() const { return mDefaultVariation; }

     /** @brief Get list of all type tables with full path
      *
      * @parameter [in] vector<string> & namepaths
      * @return   void
      */
     void GetListOfNamepaths(vector<string> &namepaths);

    /** @brief Gets the assignment from provider using namepath
     * namepath is the common ccdb request; @see GetCalib
     *
     * @remark the function is threadsafe
     *
     * @parameter [in] namepath -  full namepath is /path/to/data:run:variation:time but usually it is only /path/to/data
     * @param [in] loadColumns - optional, do we need to load table columns information (for column names and types) or not
     * @return   DAssignment *
     */
    virtual Assignment * GetAssignment(const string& namepath, bool loadColumns=true);

protected:


    virtual void Lock();   ///Thread mutex lock for multithreaded operations
    virtual void Unlock(); ///Thread mutex Unlock lock for multithreaded operations

private:
    Calibration(const Calibration& rhs);
    Calibration& operator=(const Calibration& rhs);

protected:

    DataProvider *mProvider;    ///<Underlayed DDataProvider object
    bool mProviderIsLocked;     ///If provider
    int mDefaultRun;            ///Default run number
    string mDefaultVariation;   ///Default variation
    PthreadMutex * mReadMutex;
};

}

#endif // DCallibration_h
