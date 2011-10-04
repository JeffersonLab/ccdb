
%{
#ifdef WIN32
#include <Windows.h>
#endif
#ifndef _WIN32
#include <unistd.h>
#endif
#include <stdarg.h>
#include <stdio.h>
#ifndef _WIN32
#include <sys/time.h>
#else
#include <time.h>
#endif
#include "CCDB/Model/Directory.h"
using namespace ccdb;
%}

%typemap(csclassmodifiers) Directory "public partial class"



class Directory
{
    
    %rename(_GetParentDirectory) GetParentDirectory();    
    %rename(_GetSubdirectories) GetSubdirectories();    
    %rename(add_subdirectory) AddSubdirectory(Directory *);    
    %rename(dispose_subdirectories) DisposeSubdirectories();

    %rename(_GetId) GetId() const;            
    %rename(_SetId) SetId(dbkey_t );        

    %rename(get_parent_db_id) GetParentId() const;
    %rename(set_parent_db_id) SetParentId(dbkey_t);
    
    %rename(_GetName) GetName() const;
    %rename(_SetName) SetName(std::string);

    %rename(_GetFullPath) GetFullPath() const;
    %rename(_SetFullPath) SetFullPath(std::string);

    %rename(_GetCreatedTime) GetCreatedTime() const;
    %rename(_SetCreatedTime) SetCreatedTime(time_t);

    %rename(_GetModifiedTime) GetModifiedTime() const;
    %rename(_SetModifiedTime) SetModifiedTime(time_t);

    %rename(_GetComment) GetComment() const;
    %rename(_SetComment) SetComment(std::string);



	 

public:

    Directory(); ///Default constructor

    virtual ~Directory(); ///Destructor
    
    /**
     * @brief Get
     * @return pointer to parent directory. NULL if there is no parent directory
     */
    Directory* GetParentDirectory();
    
    /**
     * @brief Gets the vector of pointers to subdirectories
     * @return vector of pointers to subdirectories
     */
    const std::vector<Directory*>& GetSubdirectories();
    
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

    dbkey_t    GetId() const;            ///DB id
    void    SetId(dbkey_t val);        ///DB id

    dbkey_t    GetParentId() const;        ///DB id of parent directory. Id=0 - root directory
    void    SetParentId(dbkey_t val);    ///DB id of parent directory. Id=0 - root directory
    
    std::string    GetName() const;            ///Name of the directory
    void    SetName(std::string val);        ///Name of the directory

    std::string    GetFullPath() const;        ///Full path (including self name) of the directory
    void    SetFullPath(std::string val);    ///Full path (including self name) of the directory

    time_t    GetCreatedTime() const;        ///Creation time
    void    SetCreatedTime(time_t val);    ///Creation time

    time_t    GetModifiedTime() const;    ///Last modification time
    void    SetModifiedTime(time_t val);///Last modification time

    std::string    GetComment() const;            ///Full description of the directory
    void    SetComment(std::string val);        ///Full description of the directory

	%pythoncode%{
    __swig_getmethods__["parent_dir"] = _GetParentDirectory
    parent_dir  = property(_GetParentDirectory)
    
    __swig_getmethods__["subdirs"] = _GetSubdirectories
    subdirs  = property(_GetSubdirectories)
        
    __swig_getmethods__["db_id"] = _GetId
    __swig_setmethods__["db_id"] = _SetId
    db_id  = property(_GetId, _SetId)

    __swig_getmethods__["name"] = _GetName
    __swig_setmethods__["name"] = _SetName
    name  = property(_GetName, _SetName)

    __swig_getmethods__["full_path"] = _GetFullPath
    __swig_setmethods__["full_path"] = _SetFullPath
    full_path  = property(_GetFullPath, _SetFullPath)

    __swig_getmethods__["created_time"] = _GetCreatedTime
    __swig_setmethods__["created_time"] = _SetCreatedTime
    created_time  = property(_GetCreatedTime, _SetCreatedTime)

    __swig_getmethods__["modified_time"] = _GetModifiedTime
    __swig_setmethods__["modified_time"] = _SetModifiedTime
    modified_time  = property(_GetModifiedTime, _SetModifiedTime)

    __swig_getmethods__["comment"] = _GetComment
    __swig_setmethods__["comment"] = _SetComment
    comment  = property(_GetComment, _SetComment)
	%}
protected:
    
    /**
     * @brief Sets parent directory of this directory
     * 
     * Sets parent directory of this directory.
     * The function should not be used unless from @link AddSubdirecrory method
     * So one uses only AddSubdirecrory to generate directories structure
     * @param parent Parent directory. Might be NULL if No parent is present
     */
    void SetParent(Directory *parent);
    
};
