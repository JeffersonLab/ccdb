/*
 * RunRange.h
 *
 *  Created on: Sep 28, 2010
 *      Author: romanov
 */

#ifndef _DRunRange_
#define _DRunRange_

#include <string>
#include "DStoredObject.h"
using namespace std;

namespace ccdb {

class DRunRange: public DStoredObject
{
public:
	DRunRange();
	DRunRange(DObjectsOwner * owner, DDataProvider *provider=NULL);

	virtual ~DRunRange();
	
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
	
	DRunRange(const DRunRange& rhs);	
	DRunRange& operator=(const DRunRange& rhs);
};

}

#endif /* _DRunRange_ */
