%{

#include "Model/DConstantsTypeTable.h"
using namespace ccdb;
using namespace std;
%}



class DConstantsTypeTable
{

public:
	DConstantsTypeTable();
	virtual ~DConstantsTypeTable();
      
    void			SetDirectory(DDirectory *directory); /// Parent directory	reference
	DDirectory *	GetDirectory() const;				 /// Parent directory	reference

    void			SetDirectoryId(int directoryId);/// Parent directory id
	int 			GetDirectoryId() const;			/// Parent directory id

    void			SetFullPath(string fFullPath);	/// full path
	std::string 			GetFullPath() const;			/// full path
    
	void			SetId(dbkey_t id);					/// database Id
	int 			GetId() const;					/// database Id

	void			SetName(const std::string& name);			/// name 
	std::string 			GetName() const;				/// name 

	std::string		GetComment() const;				///set comment
	
	void			SetComment(const std::string& val);	///get comment

	time_t			GetCreatedTime() const;			/// Time when was created
	void			SetCreatedTime(time_t val);		/// Time when was created

	time_t			GetModifiedTime() const;		/// Time when last updated
	void			SetModifiedTime(time_t val);	/// Time when last updated
	
	int				GetNRows() const;				///Number of rows
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
	int				GetNColumns() const;

	int				GetNColumnsFromDB() const;	/// Value of nColumns of constantType table in DB
	void 			SetNColumnsFromDB(int val);	/// Value of nColumns of constantType table in DB

	/** @brief Gets vector containing all columns
	 *
	 * @return   const vector<DConstantsTypeColumn *>&
	 */
	const vector<DConstantsTypeColumn *>& GetColumns() const;

	/** @brief Adds Column to array
	 *
	 * @param     DConstantsTypeColumn * col
	 * @param     int order
	 * @return   void
	 */
	void	AddColumn(DConstantsTypeColumn *col, int order);
	
	/** @brief Adds Column to array and sets order to it as in array
	 *
	 * @warning it DOES change column mOrder member
	 *
	 * @param     DConstantsTypeColumn * col
	 * @param     int order
	 * @return   void
	 */
	void	AddColumn(DConstantsTypeColumn *col);
	
	/**
	 * @brief Adds Column to array and sets order to it as in array
	 * @param name
	 * @param type
	 */
	void	AddColumn(const std::string& name, DConstantsTypeColumn::DColumnTypes type=DConstantsTypeColumn::cDoubleColumn);

	/** @brief RemoveColumn with order
	 *
	 * @param     int order
	 * @return   void
	 */
	DConstantsTypeColumn * 	RemoveColumn(int order);

	/** @brief clear columns
	 *
	 * @return void
	 */
	void				 	ClearColumns();

	vector<string>			GetColumnNames() const;
	vector<string>			GetColumnTypeStrings() const;

private:
	
	DConstantsTypeTable(const DConstantsTypeTable& rhs);	
	DConstantsTypeTable& operator=(const DConstantsTypeTable& rhs);
};

