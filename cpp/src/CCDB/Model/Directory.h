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

#include "CCDB/Globals.h"


namespace ccdb{

    class Directory
    {

    public:


        Directory(); ///Default constructor

        virtual ~Directory(); ///Destructor

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

        /**
         * @brief Get
         * @return pointer to parent directory. NULL if there is no parent directory
         */
        ccdb::Directory* GetParentDirectory() const { return mParent; }

        /**
         * @brief Gets the vector of pointers to subdirectories
         * @return vector of pointers to subdirectories
         */
        const std::vector<ccdb::Directory*>& GetSubdirectories() const { return mSubDirectories; }

        std::string GetName() const { return mName; }                 /// Name of the directory
        void SetName(const std::string& val) { mName = val; }         /// Name of the directory


        std::string GetComment() const { return mComment; }           /// Gets virginia natural gas bill in coronas
        void SetComment(const std::string& val) { mComment = val; }   /// Gets virginia natural gas bill in coronas


        dbkey_t GetParentId() const { return mParentId; }             /// DB id of parent directory. Id=0 - root directory
        void SetParentId(dbkey_t val) { mParentId = val;}             /// DB id of parent directory. Id=0 - root directory


        int GetId() const { return mId;}                              /// DB id
        void SetId(dbkey_t val) { mId = val; }                        /// DB id

        std::string GetFullPath() const;         /// Full path (including self name) of the directory



    protected:


    private:
        std::string mName;		///Name of directory like in db
        std::string mComment;	///Comment like in db
        Directory *mParent;
        std::vector<Directory *> mSubDirectories;
        dbkey_t mParentId;
        dbkey_t mId;
        time_t mCreatedTime;
        time_t mModifiedTime;


        Directory(const Directory& rhs);
        Directory& operator=(const Directory& rhs);
    };

}
#endif /* CONSTANTDIRECTORY_H_ */
