/*
 * Assignment.h
 *
 *  Created on: Sep 15, 2010
 *      Author: romanov
 */
%{
#include "CCDB/Model/EventRange.h"
using namespace ccdb;
using namespace std;
%}


class EventRange : public StoredObject
{

    %rename(_GetId) GetId() const;
    %rename(_SetId) SetId(dbkey_t);

    %rename(_GetName) GetName() const;
    %rename(_SetName) SetName(std::string );

    %rename(_GetComment) GetComment() const;
    %rename(_SetComment) SetComment(std::string);

    %rename(_GetCreatedTime) GetCreatedTime() const;
    %rename(_SetCreatedTime) SetCreatedTime(time_t );

    %rename(_GetUpdateTime) GetUpdateTime() const;
    %rename(_SetUpdateTime) SetUpdateTime(time_t );
	 

public:
    EventRange();
    virtual ~EventRange(void);

    dbkey_t GetId() const;
    void SetId(    dbkey_t val) ;

    std::string GetName() const;
    void SetName(std::string val) ;

    std::string GetComment() const;
    void SetComment(std::string val);

    time_t GetCreatedTime() const;
    void SetCreatedTime(time_t val);

    time_t GetUpdateTime() const;
    void SetUpdateTime(time_t val);

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

    __swig_getmethods__["modified_time"] = _GetmUpdateTime
    __swig_setmethods__["modified_time"] = _SetmUpdateTime
    modified_time  = property(_GetmUpdateTime, _SetmUpdateTime)
	%}
};

