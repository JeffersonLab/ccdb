#ifndef _DObjectsOwner_
#define _DObjectsOwner_
#include "DStoredObject.h"
#include <map>
using namespace std;

namespace ccdb
{

class DObjectsOwner {

public:
	DObjectsOwner();
	virtual ~DObjectsOwner();
	
	/** @brief Checks if this DObjectsOwner is owner of this object
	 *
	 * @param   object to check ownership
	 * @return  true if this provider is owner
	 */
	virtual bool IsOwner(DStoredObject * object);

	/** @brief Stes ownship for this object
	 *
	 * @param     DStoredObject * object
	 * @return   void
	 */
	virtual void BeOwner(DStoredObject * object);
	
	/** @brief Release ownship for this object
	 *
	 * @param     DStoredObject * object
	 * @return   void
	 */
	virtual void ReleaseOwnership(DStoredObject * object);
private:
	
	std::map<unsigned long, DStoredObject *> mOwnedObjects; //stored objects by id
};

}

#endif // _DObjectsOwner_
