#ifndef DEventRange_h__
#define DEventRange_h__

#include "CCDB/Model/StoredObject.h"
#include "CCDB/Providers/DataProvider.h"
#include "CCDB/Model/ObjectsOwner.h"

namespace ccdb
{
class EventRange : public StoredObject
{
public:
	EventRange(ObjectsOwner * owner=NULL, DataProvider *provider=NULL);

	virtual ~EventRange(void);
		dbkey_t GetId() const { return mId; }				//get database table uniq id;
	void SetId(	dbkey_t val) { mId = val; }				//set database table uniq id;

	std::string GetName() const { return mName; }			//get name
	void SetName(std::string val) { mName = val; }			//set name

	std::string GetComment() const { return mComment; }		//get comment
	void SetComment(std::string val) { mComment = val; }	//set comment

	time_t GetCreatedTime() const { return mCreatedTime; }			//get creation time
	void SetCreatedTime(time_t val) { mCreatedTime = val;}			//set creation time

	time_t GetUpdateTime() const { return mUpdateTime; }	//get mUpdateTime time
	void SetUpdateTime(time_t val) { mUpdateTime = val; }//set mUpdateTime time
protected:

private:
	dbkey_t mId;		//database table uniq id;
	string mName;			//name	
	string mComment;		//comment
	time_t mCreatedTime;	//creationTime time
	time_t mUpdateTime;		//mUpdateTime time
	string mDescription;	//description
	EventRange(const EventRange& rhs);	
	EventRange& operator=(const EventRange& rhs);
};


}
#endif // DEventRange_h__

