#ifndef DCallibration_h
#define DCallibration_h
#include "Providers/DDataProvider.h"

namespace ccdb
{

class DCallibration {

public:
	DCallibration();
	DCallibration(string url, int run, string context="default");
	virtual ~DCallibration();
	
	/**
	 * @brief Connects to database using connection string
	 * 
	 * Connects to database using connection string
	 * connection string might be in form: 
	 * mysql://<username>:<password>@<mysql.address>:<port> <database>
	 * file://<path to the calib parent directory>
	 * 
	 * @param connectionString "mysql://<username>:<password>@<mysql.address>:<port> <database>"
	 * @return true if connected
	 */
	virtual bool Connect(std::string connectionString) = 0;

	/**
	 * @brief closes connection to data
	 */
	virtual void Disconnect()=0;

	/**
	 * @brief indicates ether the connection is open or not
	 * 
	 * @return true if  connection is open
	 */
	virtual bool IsConnected()=0;
	
	/** @brief gets DDataProvider* object used for specified DCalibration
	*@returns provider used for specified DCalibration
	*/
	DDataProvider * GetProvider() const { return mProvider; }
	
	
	/** @brief set provider to use. 
	 * if lockProvider==true, than @see Connect, @see Disconnect and @see SetConnectionString 
	 * will not affect connection of provider. The provider will not be deleted in destruction. 
	 * @parameter [in] DDataProvider * provider
	 * @parameter [in] bool lockProvider
	 * @return   void
	 */
	void UseProvider(DDataProvider * provider, bool lockProvider=true);

	/** @brief Get constants by namepath
	 * @parameter [out] map<string,string> & values
	 * @parameter [in] string namepath
	 * @return true if constants were found and filled. false if namepath was not found. raises std::exception if any other error acured.
	 */
	virtual bool GetCalib(map<string, string> &values, const string & namepath)=0;	
	virtual bool GetCalib(map<string, double> &values, const string & namepath);
	virtual bool GetCalib(map<string, int> &values, const string & namepath);
	virtual bool GetCalib(vector<string> &values, const string & namepath)=0;
	virtual bool GetCalib(vector<double> &values, const string & namepath);
	virtual bool GetCalib(vector<int> &values, const string & namepath);
	virtual bool GetCalib(vector< vector<string> > &values, const string & namepath)=0;
	virtual bool GetCalib(vector< vector<double> > &values, const string & namepath);
	virtual bool GetCalib(vector< vector<int> >   &values, const string & namepath);
	virtual bool GetCalib(vector< map<string, string> > &values, const string & namepath)=0;
	virtual bool GetCalib(vector< map<string, double> > &values, const string & namepath);
	virtual bool GetCalib(vector< map<string, int> > &values, const string & namepath);
	
	/** @brief gets connection string which is used for current provider
	*@return mConnectionString
	*/
	virtual string GetConnectionString() const;
	
private:
	DCallibration(const DCallibration& rhs);
	DCallibration& operator=(const DCallibration& rhs);
	
protected:
	DDataProvider *mProvider;
		
	bool mPoviderIsLocked;     ///If provider 
	int mRunNumber;            ///Default run number
	string mVariation;         ///Default variation

};

}

#endif // DCallibration_h
