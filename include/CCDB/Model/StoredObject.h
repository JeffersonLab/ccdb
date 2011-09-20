#ifndef _DStoredObject_
#define _DStoredObject_

#include <stdlib.h>
#include <string>


using namespace std;

namespace ccdb {
class DataProvider; // provider class See DDataProvider.h
class ObjectsOwner; //owner
/** @brief Base class for "database (or file) stored" objects
*
* Objects derived from this class designed to be a "Object Model" of the Database records
* The idea of such "Model" object that each object represent some data record from some table.
* This objects act more than only as structs representing database tables,
* behaving more like things that this tables presents.
* I.E. Data blob can present its data in different ways. Directories have hierarchical structure. Etc.
* The objects are related to each other by pointers representing database structure.
*
* (!) But it is very important that each object of the model have such fields that it can be used
* to do UPDATE and DELETE operations same as SELECT operations
*
* @param     provider
* @param     isOwner
* @return
*/
class StoredObject {
	friend class DataProvider;
	friend class ObjectsOwner;
public:

	StoredObject(ObjectsOwner * owner=NULL, DataProvider *provider=NULL);
	virtual ~StoredObject(void);
	
	/** @brief GetNextUID
	 *
	 * @return   unsigned int
	 */
	static unsigned long GetNextUID() { return mLastTempId; }

	/** @brief Get provider that managed this object
	 *
	 * @return   DDataProvider *
	 */
	ObjectsOwner * GetOwner() const { return mOwner; }

	/** @brief Set provider that managed this object
	 *
	 * @param     val				provider
	 * @param     isOwner	provider is owner @see DStoredObject
	 */
	void			SetOwner(ObjectsOwner * val, bool isOwner = true);


	/** @brief If provider is not null, releases the owning of the provider
	 *
	 * @return   void
	 */
	virtual void ReleaseOwning();

	/** @brief Release provider owning of this object and all component objects holded by this provider
	 *
	 * I.E. Directories have subdirectories. Tables containers columns
	 * @return   void
	 */
	virtual void ReleaseOwningRecursive();


	/** @brief GetTempUID
	 *
	 * @return   unsigned int
	 */
	unsigned long GetTempUID() const;

	/** @brief GetIsProviderOwned
	 *
	 * @return   bool
	 */
	bool GetIsOwned() const {
		return mIsOwned;
	}

protected:
	
	
	bool IsNew() const {
		return mIsNew;
	}
	void SetIsNew(bool val) {
		mIsNew = val;
	}
	bool IsChanged() const {
		return mIsChanged;
	}
	void SetIsChanged(bool val=true) {
		mIsChanged = val;
	}
	bool IsLoaded() const {
		return mIsLoaded;
	}
	void SetIsLoaded(bool val) {
		mIsLoaded = val;
	}
private:
	bool mIsNew;				// NOT IMPLEMENTED
	bool mIsChanged;			// NOT IMPLEMENTED
	bool mIsOwned;			// indicates that provider owns deletion of this object
	bool mIsLoaded;			// Loaded by provider from persistent storage
	DataProvider * mProvider; //back hook to provider of the object
	
	ObjectsOwner* mOwner;		//owner of the object
	unsigned long mTempId;	// This is actually UID, The unique Id during a program run. It is called Temp to emphasise that it has no buisness to Id in database


	static unsigned long mLastTempId;	//Last given UID

};
}
#endif // _DStoredObject_
