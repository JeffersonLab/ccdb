
/*
 * Variation.h
 *
 *  Created on: Sep 15, 2010
 *      Author: romanov
 */

#ifndef VARIATION_H_
#define VARIATION_H_

#include <string>
#include <time.h>

namespace ccdb
{
    class Variation
    {
    public:
        Variation(){
            mId=0;			//! database table uniq id;
            mParentDbId = 0;
            mParent = nullptr;
        }

        Variation(const Variation& rhs) = delete;
        Variation& operator=(const Variation& rhs) = delete;

        virtual ~Variation() = default;
        unsigned int GetId() const { return mId; }					//get database table uniq id;
        void SetId(unsigned int val) { mId = val; }	                //set database table uniq id;
        std::string GetName() const { return mName; }				//get name
        void SetName(std::string val) { mName = val; }				//set name
        std::string GetComment() const { return mComment; }			//get comment
        void SetComment(std::string val) { mComment = val; }		//set comment

        Variation * GetParent() const { return mParent; }
        void SetParent(Variation * val) { mParent = val; }

        unsigned int GetParentDbId() const { return mParentDbId; }
        void SetParentDbId(unsigned int val) { mParentDbId = val; }
    protected:

    private:
        unsigned int		mId;			//! database table uniq id;
        unsigned int        mParentDbId;      /// Database id of parent variation
        Variation *         mParent;      /// Get parent variation
        string			    mName;		//! name
        string			    mComment;		//! comment
    };
}

#endif /* VARIATION_H_ */
