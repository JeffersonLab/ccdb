%{

#include "CCDB/Model/ConstantsTypeColumn.h"
using namespace ccdb;
using namespace std;
%}

class ConstantsTypeColumn{
    %rename(_GetId) GetId() const;
    %rename(_SetId) SetId(dbkey_t);

    %rename(_GetName) GetName() const;
    %rename(_SetName) SetName(string val);

    %rename(_GetComment) GetComment() const;
    %rename(_SetComment) SetComment(std::string);

    %rename(_GetCreatedTime) GetCreatedTime() const;
    %rename(_SetCreatedTime) SetCreatedTime(time_t);

    %rename(_GetModifiedTime) GetModifiedTime() const;
    %rename(_SetModifiedTime) SetModifiedTime(time_t);

    %rename(_GetTypeTableId) GetTypeTableId() const;

    %rename(get_dB_type_table_id) GetDBTypeTableId() const;
    %rename(aet_dB_type_table_id) SetDBTypeTableId(dbkey_t);
    
    %rename(_GetType) GetTypeString() const;
    %rename(_SetType) SetType(std::string);

    %rename(_GetTypeTable) GetTypeTable() const;
    %rename(_SetTypeTable) SetTypeTable(ConstantsTypeTable *);
    
    %rename(_GetOrder) GetOrder() const;
public:
    enum DColumnTypes
    {
        cIntColumn,
        cUIntColumn,
        cLongColumn,
        cULongColumn,
        cDoubleColumn,
        cBoolColumn,
        cStringColumn
    };

    /** @brief converts std::stringto  DColumnTypes
     * int       => cIntColumn
     * uint       => cUIntColumn
     * long    => cLongColumn
     * ulong   => cULongColumn
     * double  => cDoubleColumn
     * bool       => cBoolColumn
     * std::string => cStringColumn
     * 
     * @param     val
     * @return   ccdb::ConstantsTypeColumn::DColumnTypes
     */
    static DColumnTypes StringToType(string val);

    /** @brief Converts  DColumnTypes to string
     *
     * cIntColumn    => int       
     * cUIntColumn   => uint       
     * cLongColumn   => long    
     * cULongColumn  => ulong   
     * cDoubleColumn => double  
     * cBoolColumn   => bool       
     * cStringColumn => std::string 
     * @param     val
     * @return   ccdb::ConstantsTypeColumn::DColumnTypes
     */
    static std::string TypeToString(DColumnTypes val);

    ConstantsTypeColumn(ObjectsOwner * owner=NULL, DataProvider *provider=NULL);    ///Constructor
    virtual ~ConstantsTypeColumn();                  ///Destructor

    dbkey_t            GetId() const;                ///get database table uniq id;
    void            SetId(dbkey_t val);              ///set database table uniq id;

    std::string            GetName() const;          ///get name
    void            SetName(string val);             ///set name

    std::string            GetComment() const;       ///get comment
    void            SetComment(std::string val);     ///set comment

    time_t            GetCreatedTime() const;        ///get mCreatedTime time
    void            SetCreatedTime(time_t val);      ///set mCreatedTime time 

    time_t            GetModifiedTime() const;       ///get mModifiedTime time
    void            SetModifiedTime(time_t val);     ///set mModifiedTime time

    /** @brief Gets id of constant type record this column is related to
     *
     * The function check the related ConstantsTypeTable referense and returns its Id
     * if the ref is NULL, it will use mDBTypeTableId
     * Use this function instead of @see GetDBTypeTableId() for most of the cases
     * @return   DB Id of the database table
     */
    dbkey_t            GetTypeTableId() const;

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
    dbkey_t            GetDBTypeTableId() const;

    /** @brief Set DB key Id of TypeTable
     *
     * To retrive the Id one should use @see GetTypeTableId() function
     * To see what value was set by this function one could use @ see GetDBTypeTableId()
     *
     * @param     val
     * @return   void
     */
    void            SetDBTypeTableId(dbkey_t val);

    
    std::string        GetTypeString() const;                    ///Gets type of column by string
    void            SetType(std::string val);                ///Sets type of column
    

    ConstantsTypeTable * GetTypeTable() const;
    void SetTypeTable(ConstantsTypeTable * val);
    unsigned int GetOrder() const { return mOrder; }
    
	%pythoncode%{
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

    __swig_getmethods__["column_type"] = _GetType
    __swig_setmethods__["column_type"] = _SetType
    column_type  = property(_GetType, _SetType)
    

    __swig_getmethods__["type_table"] = _GetTypeTable
    __swig_setmethods__["type_table"] = _SetTypeTable
    type_table  = property(_GetTypeTable, _SetTypeTable)
    
    __swig_getmethods__["order"] = _GetOrder
    order  = property(_GetOrder)
    %}
protected:
    
    void SetOrder(unsigned int val) { mOrder = val; }

};



