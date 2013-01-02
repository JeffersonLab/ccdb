/*
 * DAssignment.h
 *
 *  Created on: Sep 15, 2010
 *      Author: romanov
 */

#ifndef _DAssignment_
#define _DAssignment_

#include <vector>
#include <map>

#include "CCDB/Model/StoredObject.h"
#include "CCDB/Model/ObjectsOwner.h"
#include "CCDB/Model/ConstantsTypeTable.h"

using namespace std;

namespace ccdb {

class EventRange;
class Variation;
class RunRange;

class Assignment: public ObjectsOwner, public StoredObject {
public:
	Assignment(ObjectsOwner * owner=NULL, DataProvider *provider=NULL);
	virtual ~Assignment();

	/** @brief creates mapped data by columns
	 *
	 * @param  mappedData
	 * @param  columns
	 * @return const vector<map<string,string> >
	 */
	static bool MapData(vector<map<string,string> > & mappedData, const vector<string>& data, const vector<string>& columns);
	
	/** @brief creates mapped data by columns
	 * 
	 * @param  mappedData   - result
	 * @param  data			- data to be mapped
	 * @param  columnsNum	- 
	 * @return bool
	 */
	static bool MapData( vector<vector<string> > & mappedData, const vector<string>& data, int columnsNum );


	/**
	 * @brief makes a string blob from tokens
	 * @param     const vector<string> & values
	 * @return   std::string
	 */
	static string VectorToBlob(const vector<string>& values);

	/** @brief Encodes blob separator
	 *
	 * if str contains '|' it will be replaced by '&pipe;'
	 * @param     string str
	 * @return   std::string
	 */
	static string EncodeBlobSeparator(string str);

	/** @brief Decodes blob separator
	 *
	 * if str contains '&pipe;'  it will be replaced by '|'
	 *
	 * @param     string str
	 * @return   std::string
	 */
	static string DecodeBlobSeparator(string str);

	unsigned int    GetVariationId() const;				/// database ID of variation
	void            SetVariationId(unsigned int val);	/// database ID of variation

	unsigned int    GetRunRangeId() const;				/// database ID of run range
	void            SetRunRangeId(unsigned int val);	/// database ID of run range

	unsigned int    GetDataVaultId() const;				/// database ID of data blob
	void            SetDataVaultId(unsigned int val);	/// database ID of data blob

	unsigned int    GetEventRangeId() const;			/// event range ID
	void            SetEventRangeId(unsigned int val);	/// event range ID

	int			    GetRequestedRun() const;			/// Run than was requested for user
	void			SetRequestedRun(int val);			/// Run than was requested for user

	RunRange *	    GetRunRange() const;		        /// Run range object, is NULL if not set
	void            SetRunRange(RunRange * val);		/// Run range object, is NULL if not set

	EventRange *	GetEventRange() const;			    /// Event range object, is NULL if not set
	void			SetEventRange(EventRange * val);    /// Event range object, is NULL if not set

	Variation *	    GetVariation() const;               /// Variation object, is NULL if not set
	void			SetVariation(Variation * val);		/// Variation object, is NULL if not set

	int		GetId() const { return mId;	} /// id in database
	void	SetId(int val) { mId = val; } /// id in database

	time_t	GetCreatedTime() const { return mCreatedTime; }    ///Time of creation
	void	SetCreatedTime(time_t val) { mCreatedTime = val;}  ///Time of creation

	time_t	GetModifiedTime() const { return mModifiedTime;}   ///Time of last modification
    void	SetModifiedTime(time_t val) {mModifiedTime = val;} ///Time of last modification

	string	GetRawData() const { return mRawData; }          ///Raw data blob
	void	SetRawData(std::string val) { mRawData = val; }  ///Raw data blob

	
	/** @brief GetMappedData returns rows vector of maps of column_name => data_value
	 * @return   vector<map<string,string> >
	 */
	vector<map<string,string> > GetMappedData() const;					
	void GetMappedData(vector<map<string,string> > & mappedData) const;	///Mapped data

	vector<string> GetVectorData() const;				    ///Vector data
	void GetVectorData(vector<string> & vectorData) const;	///Mapped data

	/** @brief return data as vector of rows that contain vectors of cells
	 * @return   std::vector<std::vector<std::string> >
	 */
	vector<vector<string> > GetData() const;
	void GetData(vector<vector<string> > &data) const;
	
	std::string GetComment() const { return mComment;} ///Comment of assignment
	void SetComment(std::string val) {mComment = val;} ///Comment of assignment
	
	void SetTypeTable(ConstantsTypeTable* typeTable) { this->mTypeTable = typeTable;}
	ConstantsTypeTable* GetTypeTable() const { return mTypeTable; }
private:

	vector<map<string,string> > mRows;	// cache for blob data by rows
	vector<string> mValues;				// cache for blob data by array of tokens
	string mRawData;					// data blob
	int mId;							// id in database
	int mDataBlobId;					// blob id in database
	unsigned int mVariationId;			// database ID of variation
	unsigned int mRunRangeId;			// database ID of run range
	unsigned int mDataVaultId;			// database ID of data blob
	unsigned int mEventRangeId;			// event range ID
    unsigned int mColumnCount;          // number of columns
	int	mRequestedRun;					// Run than was requested for user
	RunRange *mRunRange;				// Run range object, is NULL if not set
	EventRange *mEventRange;			// Event range object, is NULL if not set
	Variation *mVariation;				// Variation object, is NULL if not set
	ConstantsTypeTable * mTypeTable;	// Constants table
	
	time_t mCreatedTime;				// time of creation
	time_t mModifiedTime;				// time of last modification
	string mComment;					// Comment of assignment

	Assignment(const Assignment& rhs);	
	Assignment& operator=(const Assignment& rhs);
	
	
};

}

#endif /* _DAssignment_ */
