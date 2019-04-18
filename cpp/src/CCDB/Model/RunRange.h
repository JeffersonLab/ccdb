/*
 * RunRange.h
 *
 *  Created on: Sep 28, 2010
 *      Author: romanov
 */

#ifndef _DRunRange_
#define _DRunRange_

#include <string>
#include "CCDB/Model/StoredObject.h"
using namespace std;

namespace ccdb {

class RunRange: public StoredObject
{
public:
	RunRange();
	RunRange(ObjectsOwner * owner, DataProvider *provider=NULL);

	virtual ~RunRange();
	
	int			GetId() const;		//! Database id
	int			GetMax() const;		///
	int			GetMin() const;
	std::string GetName() const;
	std::string GetComment() const;

	void		SetId(int val);
	void		SetMax(int val);
	void		SetMin(int val);
	void		SetName(std::string val);
	void		SetComment(std::string val);
	void		SetRange(int min, int max);

	time_t GetCreatedTime() const { return mCreatedTime; }
	void SetCreatedTime(time_t val) { mCreatedTime = val; }
	time_t GetModifiedTime() const { return mModifiedTime; }
	void SetModifiedTime(time_t val) { mModifiedTime = val; }
protected:

private:
	int mMin;
	int mMax;
	string mName;
	string mComment;
	time_t mCreatedTime;
	time_t mModifiedTime;
	
	int mId;	//Database ID of the object
	
	RunRange(const RunRange& rhs);	
	RunRange& operator=(const RunRange& rhs);
};

}

#endif /* _DRunRange_ */
