
/*
 * Variation.h
 *
 *  Created on: Sep 15, 2010
 *      Author: romanov
 */

#ifndef VARIATION_H_
#define VARIATION_H_
#include "DStoredObject.h"
#include <string>
#include <time.h>
using namespace std;

namespace ccdb {

class DVariation: public DStoredObject {
public:
	DVariation(DObjectsOwner * owner=NULL, DDataProvider *provider=NULL);

	virtual ~DVariation();
	unsigned int GetId() const { return mId; }					//get database table uniq id;
	void SetId(unsigned int val) { mId = val; }				//set database table uniq id;
	std::string GetName() const { return mName; }				//get name
	void SetName(std::string val) { mName = val; }				//set name
	std::string GetComment() const { return mComment; }			//get comment
	void SetComment(std::string val) { mComment = val; }			//set comment
	time_t GetCreatedTime() const { return mCreatedTime; }		//get mCreatedTime time
	void SetCreatedTime(time_t val) { mCreatedTime = val;}		//set mCreatedTime time
	time_t GetModifiedTime() const { return mUpdateTime; }		//get mUpdateTime time
	void SetModifiedTime(time_t val) { mUpdateTime = val; }		//set mUpdateTime time
	std::string GetDescription() const { return mDescription; }	//get description
	void SetDescription(std::string val) { mDescription = val; }	//get description
protected:
	
private:
	unsigned int		mId;			//! database table uniq id;
	string			mName;		//! name	
	string			mComment;		//! comment
	time_t			mCreatedTime;	//! Creation Time 
	time_t			mUpdateTime;	//! Update Time 
	string			mDescription;	//! description
	DVariation(const DVariation& rhs);	
	DVariation& operator=(const DVariation& rhs);
};

}

#endif /* VARIATION_H_ */
