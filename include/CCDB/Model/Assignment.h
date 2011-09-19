/*
 * DAssignment.h
 *
 *  Created on: Sep 15, 2010
 *      Author: romanov
 */

#ifndef _DAssignment_
#define _DAssignment_
#include "DStoredObject.h"
#include "DObjectsOwner.h"
#include "Model/DConstantsTypeTable.h"

#include <vector>
#include <map>

using namespace std;

namespace ccdb {

class DEventRange;
class DVariation;
class DRunRange;
class DAssignment: public DObjectsOwner, public DStoredObject {
public:
	DAssignment(DObjectsOwner * owner=NULL, DDataProvider *provider=NULL);
	virtual ~DAssignment();

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

	/** @brief makes array of tokens from blob
	 * @param     string blob
	 * @return   const vector<string>&
	 */
	static void SplitData(vector<string>& outArray,string blob);

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

	unsigned int	GetVariationId() const;				/// database ID of variation
	void			SetVariationId(unsigned int val);	/// database ID of variation

	unsigned int	GetRunRangeId() const;				/// database ID of run range
	void			SetRunRangeId(unsigned int val);	/// database ID of run range

	unsigned int	GetDataVaultId() const;				/// database ID of data blob
	void			SetDataVaultId(unsigned int val);	/// database ID of data blob

	unsigned int	GetEventRangeId() const;			/// event range ID
	void			SetEventRangeId(unsigned int val);	/// event range ID

	int			GetRequestedRun() const;				/// Run than was requested for user
	void			SetRequestedRun(int val);			/// Run than was requested for user

	DRunRange *	GetRunRange() const;					/// Run range object, is NULL if not set
	void			SetRunRange(DRunRange * val);		/// Run range object, is NULL if not set

	DEventRange *	GetEventRange() const;				/// Event range object, is NULL if not set
	void			SetEventRange(DEventRange * val);	/// Event range object, is NULL if not set

	DVariation *	GetVariation() const;				/// Variation object, is NULL if not set
	void			SetVariation(DVariation * val);		/// Variation object, is NULL if not set

	int		GetId() const {
		return mId;    /// id in database
	}
	void		SetId(int val) {
		mId = val;    /// id in database
	}

	time_t	GetCreatedTime() const {
		return mCreatedTime;    ///Time of creation
	}
	void	SetCreatedTime(time_t val) {
		mCreatedTime = val;    ///Time of creation
	}

	time_t	GetModifiedTime() const {
		return mModifiedTime;    ///Time of last modification
	}
	void	SetModifiedTime(time_t val) {
		mModifiedTime = val;    ///Time of last modification
	}

	string	GetRawData() const {
		return mRawData;    ///Raw data blob
	}
	void		SetRawData(std::string val) {
		mRawData = val;    ///Raw data blob
	}

	
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
	
	std::string GetComment() const {
		return mComment;    ///Comment of assignment
	}
	void SetComment(std::string val) {
		mComment = val;    ///Comment of assignment
	}
	
	void SetTypeTable(DConstantsTypeTable* typeTable) {
		this->mTypeTable = typeTable;
	}
	DConstantsTypeTable* GetTypeTable() const {
		return mTypeTable;
	}
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
	int	mRequestedRun;					// Run than was requested for user
	DRunRange *mRunRange;				// Run range object, is NULL if not set
	DEventRange *mEventRange;			// Event range object, is NULL if not set
	DVariation *mVariation;				// Variation object, is NULL if not set
	DConstantsTypeTable * mTypeTable;	// Constants table
	
	time_t mCreatedTime;				// time of creation
	time_t mModifiedTime;				// time of last modification
	string mComment;					// Comment of assignment

	DAssignment(const DAssignment& rhs);	
	DAssignment& operator=(const DAssignment& rhs);
	
	
};

}

#endif /* _DAssignment_ */
