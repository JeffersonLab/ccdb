/*
 * Column.h
 *
 *  Created on: Sep 15, 2010
 *      Author: romanov
 */

#ifndef COLUMN_H_
#define COLUMN_H_

#include <time.h>
#include <string>
#include "CCDB/Globals.h"
#include "CCDB/Model/StoredObject.h"
//#include "Model/ConstantsTypeTable.h"

using namespace std;

namespace ccdb {
class ConstantsTypeTable;

class ConstantsTypeColumn: public StoredObject {
	friend class ConstantsTypeTable;
public:
	enum ColumnTypes
	{
		cIntColumn,
		cUIntColumn,
		cLongColumn,
		cULongColumn,
		cDoubleColumn,
		cBoolColumn,
		cStringColumn
	};

	/** @brief converts string to  DColumnTypes
	 * int	   => cIntColumn
	 * uint	   => cUIntColumn
	 * long    => cLongColumn
	 * ulong   => cULongColumn
	 * double  => cDoubleColumn
	 * bool	   => cBoolColumn
	 * string  => cStringColumn
	 * 
	 * @param     val
	 * @return   ccdb::ConstantsTypeColumn::DColumnTypes
	 */
	static ColumnTypes StringToType(string val);

	/** @brief Converts  DColumnTypes to string
	 *
	 * cIntColumn	 => int	   
	 * cUIntColumn	 => uint	   
	 * cLongColumn	 => long    
	 * cULongColumn	 => ulong   
	 * cDoubleColumn =>	double  
	 * cBoolColumn	 => bool	   
	 * cStringColumn => string  
	 * @param     val
	 * @return   ccdb::ConstantsTypeColumn::DColumnTypes
	 */
	static string  TypeToString(ColumnTypes val);

	ConstantsTypeColumn(ObjectsOwner * owner=NULL, DataProvider *provider=NULL);	///Constructor
	virtual ~ConstantsTypeColumn();					///Destructor

	dbkey_t			GetId() const;						///get database table uniq id;
	void			SetId(dbkey_t val);					///set database table uniq id;

	string			GetName() const;					///get name
	void			SetName(string val);				///set name

	string			GetComment() const;					///get comment
	void			SetComment(std::string val);		///set comment

	time_t			GetCreatedTime() const;				///get mCreatedTime time
	void			SetCreatedTime(time_t val);			///set mCreatedTime time 

	time_t			GetModifiedTime() const;			///get mModifiedTime time
	void			SetModifiedTime(time_t val);		///set mModifiedTime time

	/** @brief Gets id of constant type record this column is related to
	 *
	 * The function check the related ConstantsTypeTable referense and returns its Id
	 * if the ref is NULL, it will use mDBTypeTableId
	 * Use this function instead of @see GetDBTypeTableId() for most of the cases
	 * @return   DB Id of the database table
	 */
	dbkey_t			GetTypeTableId() const;

	/** @brief Get DB TypeTableId
	 *
	 * This is constantTypeTable id stored in the database
	 * @warning (!) Use @see GetTypeTableId() instead of this function (!)
	 * No one should use this function accept one who really knows what to do
	 * 
	 * The function is not set as private only for user to have a possibility 
	 * to explicitly check the value of mDBTypeTableId
	 *
	 * The reason this 
	 * @return   dbkey_t
	 */
	dbkey_t			GetDBTypeTableId() const;

	/** @brief Set DB key Id of TypeTable
	 *
	 * To retrive the Id one should use @see GetTypeTableId() function
	 * To see what value was set by this function one could use @ see GetDBTypeTableId()
	 *
	 * @param     val
	 * @return   void
	 */
	void			SetDBTypeTableId(dbkey_t val);

	ColumnTypes	GetType() const;					///Gets type of column
	string			GetTypeString() const;				///Gets type of column by string
	void			SetType(string val);				///Sets type of column
	void			SetType(ColumnTypes val);			///Sets type of column

	ConstantsTypeTable * GetTypeTable() const;
	void SetTypeTable(ConstantsTypeTable * val);
	unsigned int GetOrder() const { return mOrder; }
	//The compare operations must be predefined to use the std::sort function 
	bool operator<(ConstantsTypeColumn rhs) { return mOrder < rhs.mOrder; }
	bool operator>(ConstantsTypeColumn rhs) { return mOrder > rhs.mOrder; }
protected:
	
	void SetOrder(unsigned int val) { mOrder = val; }
private:
	dbkey_t			mId;			//database table uniq id;
	string			mName;			//name	
	string			mComment;		//comment
	time_t			mCreatedTime;	//mCreatedTime time
	time_t			mModifiedTime;	//mModifiedTime time
	dbkey_t			mDBTypeTableId; //gets Type table Id
	
	unsigned int	mOrder;			//order of the column
	ColumnTypes	mType;			//column type

	ConstantsTypeTable *mTypeTable; //ref to type table; 
	
	ConstantsTypeColumn(const ConstantsTypeColumn& rhs);
	ConstantsTypeColumn& operator=(const ConstantsTypeColumn& rhs);
};

}

#endif /* COLUMN_H_ */
