%{

#include "CCDB/Model/RunRange.h"
using namespace ccdb;
%}


class RunRange
{
    
    %rename(_GetId) GetId() const;
    %rename(_SetId) SetId(int);

    %rename(_GetMax) GetMax() const;
    %rename(_SetMax) SetMax(int);

    %rename(_GetMin) GetMin() const;
    %rename(_SetMin) SetMin(int);

    %rename(_GetName) GetName() const;
    %rename(_SetName) SetName(std::string);

    %rename(_GetComment) GetComment() const;
    %rename(_SetComment) SetComment(std::string);

    %rename(set_range) SetRange(int, int);

    %rename(_GetCreatedTime)  GetCreatedTime() const;
    %rename(_SetCreatedTime)  SetCreatedTime(time_t);

    %rename(_GetModifiedTime) GetModifiedTime() const;
    %rename(_SetModifiedTime) SetModifiedTime(time_t);
    
public:
    RunRange();
    

    virtual ~RunRange();
    
    int            GetId() const;        //! Database id
    int            GetMax() const;        ///
    int            GetMin() const;
    std::string GetName() const;
    std::string GetComment() const;

    void        SetId(int val);
    void        SetMax(int val);
    void        SetMin(int val);
    void        SetName(std::string val);
    void        SetComment(std::string val);
    void        SetRange(int min, int max);

    time_t GetCreatedTime() const;
    void SetCreatedTime(time_t val);
    time_t GetModifiedTime() const;
    void SetModifiedTime(time_t val);

	%pythoncode%{  
    __swig_getmethods__["db_id"] = _GetId
    __swig_setmethods__["db_id"] = _SetId
    db_id  = property(_GetId, _SetId)

    __swig_getmethods__["max"] = _GetMax
    __swig_setmethods__["max"] = _SetMax
    max  = property(_GetMax, _SetMax)

    __swig_getmethods__["min"] = _GetMin
    __swig_setmethods__["min"] = _SetMin
    min  = property(_GetMin, _SetMin)

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
	%}
};