%{

#include "CCDB/Model/ConstantsTypeTable.h"
using namespace ccdb;
using namespace std;
%}



class ConstantsTypeTable
{   
    %rename(_GetDirectory) GetDirectory() const;
    %rename(_SetDirectory) SetDirectory(Directory *);

    %rename(set_directory_id) SetDirectoryId(int);
    %rename(get_directory_id) GetDirectoryId() const;
        
    %rename(_GetFullPath) GetFullPath() const;
    %rename(_SetFullPath) SetFullPath(std::string);

	%rename(_GetId) GetId() const;
    %rename(_SetId) SetId(dbkey_t);
    
    %rename(_GetName) GetName() const;
    %rename(_SetName) SetName(const std::string&);

    %rename(_GetComment) GetComment() const;
    %rename(_SetComment) SetComment(const std::string&);

    %rename(_GetCreatedTime) GetCreatedTime() const;
    %rename(_SetCreatedTime) SetCreatedTime(time_t);

    %rename(_GetModifiedTime) GetModifiedTime() const;
    %rename(_SetModifiedTime) SetModifiedTime(time_t);
    
    %rename(_GetNRows) GetNRows() const;
    %rename(_SetNRows) SetNRows(int);

    %rename(_GetNColumns) GetNColumns() const;

    %rename(get_db_num_columns) GetNColumnsFromDB() const;
    %rename(set_db_num_columns) SetNColumnsFromDB(int val);

    %rename(_GetColumns) GetColumns() const;

    %rename(add_column_in_order) AddColumn(ConstantsTypeColumn*, int);
    %rename(add_column) AddColumn(ConstantsTypeColumn*);
    %rename(add_column) AddColumn(const std::string&, const std::string&);

    %rename(remove_column) RemoveColumn(int);

    %rename(clear_columns) ClearColumns();
    %rename(_GetColumnNames) GetColumnNames() const;
    %rename(_GetColumnTypeStrings) GetColumnTypeStrings() const;
	 
public:
    ConstantsTypeTable();
    virtual ~ConstantsTypeTable();
      
    void            SetDirectory(Directory *directory); /// Parent directory    reference
    Directory *    GetDirectory() const;                 /// Parent directory    reference

    void            SetDirectoryId(int directoryId);     /// Parent directory id
    int             GetDirectoryId() const;              /// Parent directory id

    void            SetFullPath(std::string fFullPath);  /// full path
    std::string     GetFullPath() const;                 /// full path
    
    void            SetId(dbkey_t id);                    /// database Id
    int             GetId() const;                    /// database Id

    void            SetName(const std::string& name);            /// name 
    std::string             GetName() const;                /// name 

    std::string        GetComment() const;                ///set comment
    
    void            SetComment(const std::string& val);    ///get comment

    time_t            GetCreatedTime() const;            /// Time when was created
    void            SetCreatedTime(time_t val);        /// Time when was created

    time_t            GetModifiedTime() const;        /// Time when last updated
    void            SetModifiedTime(time_t val);    /// Time when last updated
    
    int                GetNRows() const;                ///Number of rows
    void            SetNRows(int val);                ///Number of rows

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
    int                GetNColumns() const;

    int                GetNColumnsFromDB() const;    /// Value of nColumns of constantType table in DB
    void             SetNColumnsFromDB(int val);    /// Value of nColumns of constantType table in DB

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
    void    AddColumn(ConstantsTypeColumn *col, int order);
    
    /** @brief Adds Column to array and sets order to it as in array
     *
     * @warning it DOES change column mOrder member
     *
     * @param     ConstantsTypeColumn * col
     * @param     int order
     * @return   void
     */
    void    AddColumn(ConstantsTypeColumn *col);
    
    /**
     * @brief Adds Column to array and sets order to it as in array
     * @param name
     * @param type
     */
    void ConstantsTypeTable::AddColumn( const std::string& name, const std::string& type );

    /** @brief RemoveColumn with order
     *
     * @param     int order
     * @return   void
     */
    ConstantsTypeColumn *     RemoveColumn(int order);

    /** @brief clear columns
     *
     * @return void
     */
    void                     ClearColumns();

    vector<string>            GetColumnNames() const;
    vector<string>            GetColumnTypeStrings() const;

	%pythoncode%{
    def get_column_names(self):
        return [n for n in self._GetColumnNames()]

    def get_column_types(self):
        return [t for t in self._GetColumnTypeStrings()];

    __swig_getmethods__["parent_dir"] = _GetDirectory
    __swig_setmethods__["parent_dir"] = _SetDirectory
    parent_dir  = property(_GetDirectory, _SetDirectory)
  
    __swig_getmethods__["full_path"] = _GetFullPath
    __swig_setmethods__["full_path"] = _SetFullPath
    full_path  = property(_GetFullPath, _SetFullPath)
    
    __swig_getmethods__["db_id"] = _GetId
    __swig_setmethods__["db_id"] = _SetId
    db_id  = property(_GetId, _SetId)
    
    __swig_getmethods__["name"] = _GetName
    __swig_setmethods__["name"] = _SetName
    name  = property(_GetName, _SetName)

    __swig_getmethods__["comment"] = _GetComment
    __swig_setmethods__["comment"] = _SetComment
    comment  = property(_GetComment, _SetComment)

    __swig_getmethods__["created_time"] = _GetCreatedTime
    __swig_setmethods__["created_time"] = _SetCreatedTime
    created_time  = property(_GetCreatedTime, _SetCreatedTime)

    __swig_getmethods__["modified_time"] = _GetModifiedTime
    __swig_setmethods__["modified_time"] = _SetModifiedTime
    modified_time  = property(_GetModifiedTime, _SetModifiedTime)
    
    __swig_getmethods__["nrows"] = _GetNRows
    __swig_setmethods__["nrows"] = _SetNRows
    nrows  = property(_GetNRows, _SetNRows)

    __swig_getmethods__["ncolumns"] = _GetNColumns
    ncolumns  = property(_GetNColumns)
    
    def _get_columns_list(self):
        return [col for col in self._GetColumns()]

    __swig_getmethods__["columns"] = _get_columns_list
    columns  = property(_get_columns_list)
	%}

private:
    
    ConstantsTypeTable(const ConstantsTypeTable& rhs);    
    ConstantsTypeTable& operator=(const ConstantsTypeTable& rhs);
};

