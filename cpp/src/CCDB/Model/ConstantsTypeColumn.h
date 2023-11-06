/*
 *  Created on: Sep 15, 2010 by Dmitry Romanov
 */

#ifndef COLUMN_H_
#define COLUMN_H_

#include <time.h>
#include <string>
#include "CCDB/Globals.h"

using namespace std;

namespace ccdb {
class ConstantsTypeTable;

class ConstantsTypeColumn {
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
     * int       => cIntColumn
     * uint       => cUIntColumn
     * long    => cLongColumn
     * ulong   => cULongColumn
     * double  => cDoubleColumn
     * bool       => cBoolColumn
     * string  => cStringColumn
     *
     * @param     val
     * @return   ccdb::ConstantsTypeColumn::DColumnTypes
     */
    static ColumnTypes StringToType(std::string val);

    /** @brief Converts  DColumnTypes to string
     *
     * cIntColumn     => int
     * cUIntColumn     => uint
     * cLongColumn     => long
     * cULongColumn     => ulong
     * cDoubleColumn =>    double
     * cBoolColumn     => bool
     * cStringColumn => string
     * @param     val
     * @return   ccdb::ConstantsTypeColumn::DColumnTypes
     */
    static std::string TypeToString(ColumnTypes val);

    ConstantsTypeColumn();    ///Constructor
    virtual ~ConstantsTypeColumn();                      /// Destructor

    dbkey_t         GetId() const;                       /// get database table uniq id;
    void            SetId(dbkey_t val);                  /// set database table uniq id;

    std::string     GetName() const;                    /// get name
    void            SetName(std::string val);           /// set name

    std::string     GetComment() const;                 /// get comment
    void            SetComment(std::string val);        /// set comment

    time_t          GetCreatedTime() const;             /// get mCreatedTime time
    void            SetCreatedTime(time_t val);         /// set mCreatedTime time

    time_t          GetModifiedTime() const;            /// get mModifiedTime time
    void            SetModifiedTime(time_t val);        /// set mModifiedTime time



    /** @brief Set DB key Id of TypeTable
     *
     * To retrive the Id one should use @see GetTypeTableId() function
     * To see what value was set by this function one could use @ see GetDBTypeTableId()
     *
     * @param     val
     * @return   void
     */
    void        SetDBTypeTableId(dbkey_t val);

    ColumnTypes GetType() const;                    ///Gets type of column
    void        SetType(std::string val);           ///Sets type of column
    void        SetType(ColumnTypes val);           ///Sets type of column
    std::string GetTypeString() const;              ///Gets type of column by string

    ConstantsTypeTable * GetTypeTable() const;
    void SetTypeTable(ConstantsTypeTable * val);
    unsigned int GetOrder() const { return mOrder; }
    //The compare operations must be predefined to use the std::sort function
    bool operator<(ConstantsTypeColumn rhs) { return mOrder < rhs.mOrder; }
    bool operator>(ConstantsTypeColumn rhs) { return mOrder > rhs.mOrder; }
protected:

    void SetOrder(unsigned int val) { mOrder = val; }
private:
    dbkey_t      mId;                //database table uniq id;
    std::string  mName;              //name
    std::string  mComment;           //comment
    time_t       mCreatedTime;       //mCreatedTime time
    time_t       mModifiedTime;      //mModifiedTime time
    dbkey_t      mDBTypeTableId;     //gets Type table Id
    unsigned int mOrder;             //order of the column
    ColumnTypes  mType;              //column type


    ConstantsTypeColumn(const ConstantsTypeColumn& rhs);
    ConstantsTypeColumn& operator=(const ConstantsTypeColumn& rhs);
};

}

#endif /* COLUMN_H_ */
