#ifndef _DObjectsOwner_
#define _DObjectsOwner_
#include "CCDB/Model/StoredObject.h"
#include <map>
using namespace std;

namespace ccdb
{

class ObjectsOwner {

public:
	ObjectsOwner();
	virtual ~ObjectsOwner();
	
	/** @brief Checks if this DObjectsOwner is owner of this object
	 *
	 * @param   object to check ownership
	 * @return  true if this provider is owner
	 */
	virtual bool IsOwner(StoredObject * object);

	/** @brief Stes ownship for this object
	 *
	 * @param     DStoredObject * object
	 * @return   void
	 */
	virtual void BeOwner(StoredObject * object);
	
	/** @brief Release ownship for this object
	 *
	 * @param     DStoredObject * object
	 * @return   void
	 */
	virtual void ReleaseOwnership(StoredObject * object);
private:
	
	std::map<unsigned long, StoredObject *> mOwnedObjects; //stored objects by id
};

}

#endif // _DObjectsOwner_
