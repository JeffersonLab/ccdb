%{

#include "CCDB/Model/Variation.h"
using namespace ccdb;
using namespace std;
%}

class Variation{

    %rename(_GetId) GetId();
    %rename(_SetId) SetId(dbkey_t);

    %rename(_GetName) GetName();
    %rename(_SetName) SetName(std::string);

    %rename(_GetComment) GetComment();
    %rename(_SetComment) SetComment(std::string);

    %rename(_GetCreatedTime) GetCreatedTime();
    %rename(_SetCreatedTime) SetCreatedTime(time_t);

    %rename(_GetModifiedTime) GetModifiedTime();
    %rename(_SetModifiedTime) SetModifiedTime(time_t);

    %rename(_GetDescription) GetDescription();
    %rename(_SetDescription) SetDescription(std::string);

public:
    Variation();
    virtual ~Variation();

    unsigned int GetId();
    void SetId(dbkey_t val);

    std::string GetName();
    void SetName(std::string val);

    std::string GetComment();
    void SetComment(std::string val);

    time_t GetCreatedTime();
    void SetCreatedTime(time_t val);

    time_t GetModifiedTime();
    void SetModifiedTime(time_t val);

    std::string GetDescription();
    void SetDescription(std::string val);

    
    %pythoncode%{
    
    __swig_getmethods__["db_id"] = _GetId
    __swig_setmethods__["db_id"] = _SetId
    db_id  = property(_GetId, _SetId)

    __swig_getmethods__["name"] = _GetName
    __swig_setmethods__["name"] = _SetName
    name = property(_GetName, _SetName)

    __swig_getmethods__["comment"] = _GetComment
    __swig_setmethods__["comment"] = _SetComment
    comment = property(_GetComment, _SetComment)

    __swig_getmethods__["created_time"] = _GetCreatedTime
    __swig_setmethods__["created_time"] = _SetCreatedTime
    created_time  = property(_GetCreatedTime, _SetCreatedTime)

    __swig_getmethods__["modified_time"] = _GetModifiedTime 
    __swig_setmethods__["modified_time"] = _SetModifiedTime
    modified_time  = property(_GetModifiedTime, _SetModifiedTime)

    __swig_getmethods__["description"] = _GetDescription
    __swig_setmethods__["description"] = _SetDescription
    description = property(_GetDescription, _SetDescription)
    
    %}
};

