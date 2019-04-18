#ifndef __CCDB_CONSTANTS_TABLE_H__
#define __CCDB_CONSTANTS_TABLE_H__

#include <algorithm>
#include <string>
#include <sstream>
#include <stdexcept>

#include "CCDB/MySQLCalibration.h"

namespace ccdb
{

using std::string;
using std::stringstream;
using std::vector;

/** \brief ConstantsTable is a conatiner class for any constants
 *  set. It will connect to the database when load_constants()
 *  is called. Columns can be accessed (and converted to specific
 *  types) by the col(colname) method. Individual numbers can be
 *  obtained via the elem<typename>(colname, row_index) method.
 **/
class ConstantsTable
{
  private:
    /// the table as filled by MySQLCalibration::GetCalib()
    vector<vector<string> > values;

    /// the names of the columns
    vector<string> columns;

    /// the types of the columns in string form
    vector<string> column_types;

    /** \brief find the index of the column associated with the name
     *  colname.
     *
     * \return column index of the column identified by colname
     **/
    unsigned int find_column(const string& colname)
    {
        return distance(
            columns.begin(),
            find(columns.begin(), columns.end(), colname) );
    }

    /** \brief generic function to convert a string to any type (T)
     *
     **/
    template <typename T>
    T lexical_cast(const string& str)
    {
        T ret;
        if (!(stringstream(str) >> ret))
        {
            stringstream ss;
            ss << "Could not convert: '" << str << "' to a numeric type.";
            throw std::logic_error(ss.str());
        }
        return ret;
    }

  public:

    ConstantsTable() {}

    /** \brief combines the user, host and such into the MySQL connection
     * string used by MySQLCalibration::Connect().
     *
     * forms the string: "mysql://clasuser@clasdb.jlab.org:3306 clas12"
     * by default.
     *
     * \return the MySQL connection string
     **/
    string connection_string(
        const string& user = "clasuser",
        const string& host = "clasdb.jlab.org",
        const string& port = "3306",
        const string& db   = "clas12" )
    {
        /// forms the string: "mysql://clasuser@clasdb.jlab.org:3306 clas12"
        stringstream conn_ss;
        conn_ss << "mysql://" << user
            << "@" << host << ":" << port
            << " " << db;
        return conn_ss.str();
    }

    /** \brief clears all data in this set.
     *
     **/
    void clear()
    {
        values.clear();
        columns.clear();
        column_types.clear();
    }

    /** \brief connects to the MySQL (CCDB) database and obtains the
     * data, the column names, and their types.
     **/
    void load_constants(
        const string& constsetid_str,
        const string& conn_str = "" )
    {
        this->clear();

        string conn;
        if (conn_str == "")
        {
            /// get default connection string
            conn = this->connection_string();
        }
        else
        {
            /// use this one if specified
            conn = conn_str;
        }

        MySQLCalibration calib(100);
        calib.Connect(conn);

        calib.GetCalib(values, constsetid_str);
        columns = calib.GetAssignment(constsetid_str)->GetTypeTable()->GetColumnNames();
        column_types = calib.GetAssignment(constsetid_str)->GetTypeTable()->GetColumnTypeStrings();
    }

    /** \return number of rows in this data set.
     *
     **/
    unsigned int nrows()
    {
        return values.size();
    }

    /** \return number of columns in this data set.
     *
     **/
    unsigned int ncols()
    {
        if (this->nrows() > 0)
        {
            return values.at(0).size();
        }
        else
        {
            return 0;
        }
    }

    /** \return the column name of the ith column
     *
     **/
    string colname(const unsigned int& i)
    {
        return columns.at(i);
    }

    /** \return the column type of the ith column
     *
     **/
    string coltype(const unsigned int& i)
    {
        return column_types.at(i);
    }

    /** \return the column type of the column identified by colname
     *
     **/
    string coltype(const string& colname)
    {
        return coltype(find_column(colname));
    }

    /** \brief specialization of coltype() for const char*
     *
     * \return the column type of the column identified by colname
     **/
    string coltype(const char* colname)
    {
        return coltype(string(colname));
    }

    /** \return vector<T=double> of a column identified by the
     *  colname.
     **/
    template <typename T=double>
    vector<T> col(const string& colname)
    {
        vector<T> ret;

        unsigned int col_index = find_column(colname);

        for (int row_index=0; row_index<nrows(); row_index++)
        {
            ret.push_back(lexical_cast<T>(values.at(row_index).at(col_index)));
        }

        return ret;
    }

    /** \brief finds the element in the table associated with column
     * identified by colname and row specified (default row: 0)
     *
     *  typical usage:
     * for example, to get the xdist for region 2, we could get the
     * row index from the method row() and use that as in a call
     * elem() to get the element "xdist" at that row.
     *
     * ConstantsTable table;
     * table.load_constants("/geometry/dc/region");
     * table.elem( "xdist", table.row("region",2) );
     *
     * Equivalently, if we already know that the table is ordered
     * properly and the index associated with region 2 is 2-1 = 1,
     * then we could do this to get the same number as above:
     *
     * table.elem("xdist", 1);
     *
     *  \return element of the table cast to type T (default: double)
     **/
    template <typename T=double>
    T elem(const string& colname, const unsigned int& row=0)
    {
        return lexical_cast<T>(
            values.at(row).at(find_column(colname)) );
    }

    /** \brief find the first row of a specified column that has a
     * value that equals val.
     *
     * NOTE: getting the row index works for integers but
     * not for floats!!! Use only integers or strings. The
     * "string for floats" usage is OK, but not recommended.
     *
     * example:
     *   table.row("dist2tgt", "348.09")
     *
     * \return row index associated with the value val
     **/
    template <typename T>
    unsigned int row(const string& colname, const T& val)
    {
        for (unsigned int i=0; i<nrows(); i++)
        {
            if (elem<T>(colname,i) == val)
            {
                return i;
            }
        }
        stringstream ss;
        ss << "No such value: " << val << " in column " << colname;
        throw std::logic_error(ss.str());
    }

    /** \brief specialization for char* (converting to string)
     *
     **/
    unsigned int row(const string& colname, const char* val)
    {
        return row<string>(colname, string(val));
    }

};

} /* namespace ccdb */

#endif /* __CCDB_CONSTANTS_TABLE_H__ */
