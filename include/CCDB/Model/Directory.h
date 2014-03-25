/*
 * Directory.h
 *
 *  Created on: Sep 15, 2010
 *      Author: romanov
 */

#ifndef CONSTANTDIRECTORY_H_
#define CONSTANTDIRECTORY_H_
#include <vector>
#include <string>
#include <time.h>

#include "CCDB/Model/StoredObject.h"
#include "CCDB/Model/ObjectsOwner.h"
#include "CCDB/Globals.h"

using namespace std;

namespace ccdb{

class Directory : public StoredObject
{

public:
	
	/** @brief Stored object constructor
	 *
	 * @param  [in] owner
	 * @param  [in] provider
	 * @return 
	 */
	Directory(ObjectsOwner * owner, DataProvider *provider=NULL);
	
	Directory(); ///Default constructor

	virtual ~Directory(); ///Destructor
	
	/**
	 * @brief Get
	 * @return pointer to parent directory. NULL if there is no parent directory
	 */
	Directory* GetParentDirectory();
	
	/**
	 * @brief Gets the vector of pointers to subdirectories
	 * @return vector of pointers to subdirectories
	 */
	const vector<Directory*>& GetSubdirectories();
	
	/**
	 * @brief Adds a subdirectory of this directory
	 * 
	 * Adds a subdirectory of this directory
	 * Automatically adds "this" as mParent for child
	 * 
	 * @param subDirectory Child directory to be added
	 */
	void AddSubdirectory(Directory *subdirectory);
	
	/**
	 * @brief deletes all subdirectories recursively
	 */
	void DisposeSubdirectories();

	dbkey_t	GetId() const;			///DB id
	void	SetId(dbkey_t val);		///DB id

	dbkey_t	GetParentId() const;		///DB id of parent directory. Id=0 - root directory
	void	SetParentId(dbkey_t val);	///DB id of parent directory. Id=0 - root directory
	
	string	GetName() const;			///Name of the directory
	void	SetName(string val);		///Name of the directory

	string	GetFullPath() const;		///Full path (including self name) of the directory
	void	SetFullPath(string val);	///Full path (including self name) of the directory

	time_t	GetCreatedTime() const;		///Creation time
	void	SetCreatedTime(time_t val);	///Creation time

	time_t	GetModifiedTime() const;	///Last modification time
	void	SetModifiedTime(time_t val);///Last modification time

	string	GetComment() const;			///Full description of the directory
	void	SetComment(string val);		///Full description of the directory
protected:
	
	/**
	 * @brief Sets parent directory of this directory
	 * 
	 * Sets parent directory of this directory.
	 * The function should not be used unless from @link AddSubdirecrory method
	 * So one uses only AddSubdirecrory to generate directories structure
	 * @param parent Parent directory. Might be NULL if No parent is present
	 */
	void SetParent(Directory *parent); //TODO delete this and check everything works
	
private:
	string mName;		///Name of directorey like in db
	string mFullPath;	///full path
	string mComment;	///Comment like in db
	Directory *mParent;
	vector<Directory *> mSubDirectories;
	dbkey_t mParentId;
	dbkey_t mId;
	time_t mCreatedTime;
	time_t mModifiedTime;
	

	Directory(const Directory& rhs){}	
	Directory& operator=(const Directory& rhs);
};

}
#endif /* CONSTANTDIRECTORY_H_ */
