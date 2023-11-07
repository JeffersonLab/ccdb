//
// Created by romanov on 4/27/19.
//

#ifndef CCDB_SQLITE_H
#define CCDB_SQLITE_H

#include <string>
#include <stdexcept>

#include <sqlite3.h>


namespace ccdb {
    class SQLiteStatement{
    public:
        /** Definition of function which is called each time to process a new row*/
        using RowProcessCallback = void (*)(uint64_t rowIndex);


        SQLiteStatement(sqlite3* database): mDatabase(database) {}

        /// Same as SQLiteStatement(db); Prepare(query)
        SQLiteStatement(sqlite3* database, const std::string& query): mDatabase(database) {Prepare(query);}

        ~SQLiteStatement() {
            sqlite3_finalize(mStatement);
        }

        void Prepare(const std::string& query) {
            int result = sqlite3_prepare_v2(mDatabase, query.c_str(), -1, &mStatement, nullptr);
            if( result ) {
                auto error = "Error in sqlite3_prepare_v2: {}" + std::string(sqlite3_errmsg(mDatabase));
                throw std::runtime_error(error);
            }

            mLastQuery = query;
            mLastQueryColumnCount = 0;  // Set it to 0 so if user tries
        }


        /// Checks if there is a value with this fieldNum index (reports error in such case)
        /// and if it is not null (just returns false in this case)
        void ValidateColumnIndex(int columnIndex) {
            if(mLastQueryColumnCount <= columnIndex) {
                //Add error, we have less fields than fieldNum
                auto error = "Requested column index doesn't correspond to the last query. "
                                   "Req. Index: " + std::to_string(columnIndex) + ", "
                                   "LastQueryColumnCount: " + std::to_string(mLastQueryColumnCount) + ","
                                   " Last Query: " + mLastQuery;
                throw std::runtime_error(error);
            }
        }

        void BindInt32(int32_t varId, int32_t value) {
            int result = sqlite3_bind_int(mStatement, varId, value);
            if( result ) {
                auto error = "sqlite3_bind_int error: " + std::string(sqlite3_errmsg(mDatabase)) + ". Query: " + mLastQuery;
                throw std::runtime_error(error);
            }
        }

        void BindInt64(int32_t varId, int64_t value) {
            int result = sqlite3_bind_int64(mStatement, varId, value);
            if( result ) {
                auto error = "sqlite3_bind_int64 error: " + std::string(sqlite3_errmsg(mDatabase)) + ". Query: " + mLastQuery;
                throw std::runtime_error(error);
            }
        }

        void BindString(int32_t varId,const std::string& str) {
            int result = sqlite3_bind_text(mStatement, varId, str.c_str(), -1, SQLITE_TRANSIENT); /*`name`*/
            if( result ) {
                auto error = "sqlite3_bind_text error: " + std::string(sqlite3_errmsg(mDatabase)) + ". Query: " + mLastQuery;
                throw std::runtime_error(error);
            }
        }


        template<typename Func>
        uint64_t Execute(Func onRow) {
            uint64_t rowsProcessed = 0;
            int result;
            mLastQueryColumnCount = sqlite3_column_count(mStatement);
            do
            {
                result = sqlite3_step(mStatement);
                switch( result )
                {
                    case SQLITE_DONE:
                        break;
                    case SQLITE_ROW:
                        //ok lets read the data...
                        onRow(rowsProcessed);
                        rowsProcessed++;
                        break;
                    default:
                        auto error = "sqlite3_step error: " + std::string(sqlite3_errmsg(mDatabase)) + ". Query: " + mLastQuery;
                        throw std::runtime_error(error);
                }
            }
            while(result==SQLITE_ROW );
            return rowsProcessed;
        }


        int32_t ReadInt32(int columnIndex) {
            ValidateColumnIndex(columnIndex);
            return sqlite3_column_int(mStatement, columnIndex);
        }

        uint32_t ReadUInt32(int columnIndex) {
            ValidateColumnIndex(columnIndex);
            return static_cast<uint32_t>(sqlite3_column_int(mStatement,columnIndex));
        }

        int64_t ReadInt64(int columnIndex) {
            ValidateColumnIndex(columnIndex);
            return sqlite3_column_int64(mStatement,columnIndex);
        }

        uint64_t ReadUInt64(int columnIndex) {
            ValidateColumnIndex(columnIndex);
            return static_cast<uint64_t>(sqlite3_column_int64(mStatement,columnIndex));
        }

        bool ReadBool(int columnIndex) {
            ValidateColumnIndex(columnIndex);
            return static_cast<bool>(sqlite3_column_int(mStatement,columnIndex));
        }

        double ReadDouble(int columnIndex) {
            ValidateColumnIndex(columnIndex);
            return sqlite3_column_double(mStatement, columnIndex);
        }

        std::string ReadString(int columnIndex) {
            ValidateColumnIndex(columnIndex);
            const char* str = (const char*)sqlite3_column_text(mStatement,columnIndex);
            if(!str) return std::string("");
            return std::string(str);
        }

        time_t ReadUnixTime(int columnIndex) {
            return static_cast<time_t>(ReadUInt64(columnIndex));
        }

    private:
        sqlite3_stmt *	mStatement;
        sqlite3 *		mDatabase;			//Handler to sqlite object
        uint64_t        mLastQueryColumnCount;
        std::string     mLastQuery;
    };
}

#endif //CCDB_SQLITE_H
