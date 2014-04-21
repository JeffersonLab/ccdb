/*
 * TableHeader.h
 *
 * Created on: Sep 15, 2010
 *      Author: romanov
 */

#ifndef TABLEHEADER_H_
#define TABLEHEADER_H_

#include <string>

#include "CCDB/Model/Directory.h"
#include "CCDB/Model/StoredObject.h"
#include "CCDB/Model/ConstantsTypeColumn.h"
#include "CCDB/Model/ObjectsOwner.h"
#include "CCDB/Model/ConstantsTypeColumn.h"

using namespace std;

namespace ccdb {

	//class ConstantsTypeColumn;

class ConstantsTypeTable: public ObjectsOwner, public StoredObject 
{
	friend class DataProvider;
public:
	ConstantsTypeTable(ObjectsOwner * owner=NULL, DataProvider *provider=NULL);
	virtual ~ConstantsTypeTable();
      
    void			SetDirectory(Directory *directory); /// Parent directory	reference
	Directory *	GetDirectory() const;				 /// Parent directory	reference

    void			SetDirectoryId(int directoryId);/// Parent directory id
	int 			GetDirectoryId() const;			/// Parent directory id

    void			SetFullPath(string fFullPath);	/// full path
	string 			GetFullPath() const;			/// full path
    
	void			SetId(dbkey_t id);					/// database Id
	int 			GetId() const;					/// database Id

	void			SetName(const string& name);			/// name 
	string 			GetName() const;				/// name 

	std::string		GetComment() const;				///set comment
	
	void			SetComment(const string& val);	///get comment

	time_t			GetCreatedTime() const;			/// Time when was created
	void			SetCreatedTime(time_t val);		/// Time when was created

	time_t			GetModifiedTime() const;		/// Time when last updated
	void			SetModifiedTime(time_t val);	/// Time when last updated
	
	int				GetRowsCount() const;				///Number of rows
	void			SetNRows(int val);				///Number of rows

	/** @brief GetNColumns
	 * The function check if the table contains columns objects (mColumns.count() >0) and return 
	 * the number of stored columns objects. 
	 * If the table was loaded form DB AND(!) columns objects == 0, it return GetNColumnsFromDB
	 *
	 * This behavior made in assumption that there are only two cases possible: 
	 * 1) The table is loaded from DB (may be without columns)
	 * 2) The table is created to add to DB. 
	 * because no updates with adding a column is possible. 
	 * @return   int
	 */
	int				GetColumnsCount() const;

	int				GetNColumnsFromDB() const;	/// Value of nColumns of constantType table in DB
	void 			SetNColumnsFromDB(int val);	/// Value of nColumns of constantType table in DB

	/** @brief Gets vector containing all columns
	 *
	 * @return   const vector<ConstantsTypeColumn *>&
	 */
	const vector<ConstantsTypeColumn *>& GetColumns() const;

	/** @brief Adds Column to array
	 *
	 * @param     ConstantsTypeColumn * col
	 * @param     int order
	 * @return   void
	 */
	void	AddColumn(ConstantsTypeColumn *col, int order);
	
	/** @brief Adds Column to array and sets order to it as in array
	 *
	 * @warning it DOES change column mOrder member
	 *
	 * @param     ConstantsTypeColumn * col
	 * @param     int order
	 * @return   void
	 */
	void	AddColumn(ConstantsTypeColumn *col);
	
	
	/**
	 * @brief Adds Column to array and sets order to it as in array
	 * @param name
	 * @param type
	 */
	void	AddColumn(const string& name, ConstantsTypeColumn::ColumnTypes type=ConstantsTypeColumn::cDoubleColumn);

	/**
	 * @brief Adds Column to array and sets order to it as in array
	 * @param [in] name
	 * @param [in] type
	 */
	void	AddColumn(const std::string& name, const std::string& type);

	/** @brief RemoveColumn with order
	 *
	 * @param     int order
	 * @return   void
	 */
	ConstantsTypeColumn * 	RemoveColumn(int order);

	/** @brief clear columns
	 *
	 * @return void
	 */
	void				 	ClearColumns();

	vector<string>			GetColumnNames() const;
	vector<string>			GetColumnTypeStrings() const;

	/** @brief gets map of pointer to columns by name of columns*/
	map<string, ConstantsTypeColumn *> &GetColumnsByName();
private:
	string		mName;			//Name of the table of constants
	string		mFullPath;		//Full path of the constant
    Directory *mDirectory;		//Link to the directory that holds this constant
    int			mDirectoryId;	//Parent directory ID in the DB
    dbkey_t mId;			//db id
	string		mComment;		//comment
	time_t		mCreatedTime;	//creation time
	time_t		mUpdateTime;	//update time
	string		mDescription;	//description
	int			mNRows;			// Number of rows
	int			mNColumnsFromDB;// Value of nColumns of constantType table in DB
								
	map<string, ConstantsTypeColumn *> mColumnsByName;
	
	vector<ConstantsTypeColumn *> mColumns; //Columns object
	ConstantsTypeTable(const ConstantsTypeTable& rhs);	
	ConstantsTypeTable& operator=(const ConstantsTypeTable& rhs);
};

} //namespace ccdb

#endif /* TABLEHEADER_H_ */
