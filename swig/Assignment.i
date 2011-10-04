/*
 * Assignment.h
 *
 *  Created on: Sep 15, 2010
 *      Author: romanov
 */
%{
#include "CCDB/Model/Assignment.h"
using namespace ccdb;
using namespace std;
%}

class Assignment{

    %rename(get_db_variation_id) GetVariationId() const;
    %rename(set_db_variation_id) SetVariationId(unsigned int);

    %rename(get_db_run_range_id) GetRunRangeId() const;
    %rename(set_db_run_range_id) SetRunRangeId(unsigned int);

    %rename(get_db_data_vault_id) GetDataVaultId() const;
    %rename(set_db_data_vault_id) SetDataVaultId(unsigned int);

    %rename(get_db_event_range_id) GetEventRangeId() const;
    %rename(set_db_event_range_id) SetEventRangeId(unsigned int);

    %rename(get_db_requested_run) GetRequestedRun() const;
    %rename(set_db_requested_run) SetRequestedRun(int);

    %rename(_GetRunRange) GetRunRange() const;
    %rename(_SetRunRange) SetRunRange(RunRange *);

    %rename(_GetEventRange) GetEventRange() const;
    %rename(_SetEventRange) SetEventRange(EventRange *);

    %rename(_GetVariation) GetVariation() const;
    %rename(_SetVariation) SetVariation(Variation *);

    %rename(_GetTypeTable) GetTypeTable() const;
    %rename(_SetTypeTable) SetTypeTable(ConstantsTypeTable*);

    %rename(_GetId) GetId() const;
    %rename(_SetId) SetId(int);

    %rename(_GetCreatedTime) GetCreatedTime() const;
    %rename(_SetCreatedTime) SetCreatedTime(time_t);

    %rename(_GetModifiedTime) GetModifiedTime() const;
    %rename(_SetModifiedTime) SetModifiedTime(time_t);

    %rename(_GetRawData) GetRawData() const;
    %rename(_SetRawData) SetRawData(std::string);

    %rename(_GetMappedData) GetMappedData() const;

    %rename(_GetVectorData) GetVectorData() const;
    
	%rename(_GetData) GetData() const;

    %rename(_GetComment) GetComment() const;
    %rename(_SetComment) SetComment(std::string);
	
	
public:
    Assignment(ObjectsOwner * owner=NULL, DataProvider *provider=NULL);
    virtual ~Assignment();



    unsigned int GetVariationId() const;    /// database ID of variation
    void SetVariationId(unsigned int val);  /// database ID of variation

    unsigned int GetRunRangeId() const;     /// database ID of run range
    void SetRunRangeId(unsigned int val);   /// database ID of run range

    unsigned int GetDataVaultId() const;    /// database ID of data blob
    void SetDataVaultId(unsigned int val);  /// database ID of data blob

    unsigned int GetEventRangeId() const;   /// event range ID
    void SetEventRangeId(unsigned int val); /// event range ID

    int     GetRequestedRun() const;        /// Run than was requested for user
    void SetRequestedRun(int val);          /// Run than was requested for user

    RunRange *    GetRunRange() const;     /// Run range object, is NULL if not set
    void SetRunRange(RunRange * val);      /// Run range object, is NULL if not set

    EventRange * GetEventRange() const;    /// Event range object, is NULL if not set
    void SetEventRange(EventRange * val);  /// Event range object, is NULL if not set

    Variation * GetVariation() const;      /// Variation object, is NULL if not set
    void SetVariation(Variation * val);    /// Variation object, is NULL if not set

    int    GetId() const;
    void SetId(int val);

    time_t GetCreatedTime() const;
    void   SetCreatedTime(time_t val);

    time_t GetModifiedTime() const;
    void   SetModifiedTime(time_t val);

    std::string GetRawData() const;
    void   SetRawData(std::string val);

	std::string GetComment() const;
    void SetComment(std::string val);

    std::vector<std::map<std::string,std::string> > GetMappedData() const;                    ///Mapped data
    
    std::vector<std::string> GetVectorData() const;                        ///Vector data
    		
	std::vector<std::vector<std::string> > GetData() const; 
    
    
    void SetTypeTable(ConstantsTypeTable* typeTable);
    ConstantsTypeTable* GetTypeTable() const;
    
    %pythoncode%{
    __swig_getmethods__["run_range"] = _GetRunRange
    __swig_setmethods__["run_range"] = _SetRunRange
    run_range  = property(_GetRunRange, _SetRunRange)

    __swig_getmethods__["event_range"] = _GetEventRange
    __swig_setmethods__["event_range"] = _SetEventRange
    event_range  = property(_GetEventRange, _SetEventRange)

    __swig_getmethods__["variation"] = _GetVariation
    __swig_setmethods__["variation"] = _SetVariation
    variation  = property(_GetVariation, _SetVariation)

    __swig_getmethods__["type_table"] = _GetTypeTable
    __swig_setmethods__["type_table"] = _SetTypeTable
    type_table  = property(_GetTypeTable, _SetTypeTable)

    __swig_getmethods__["db_id"] = _GetId
    __swig_setmethods__["db_id"] = _SetId
    db_id  = property(_GetId, _SetId)

    __swig_getmethods__["created_time"] = _GetCreatedTime
    __swig_setmethods__["created_time"] = _SetCreatedTime
    created_time  = property(_GetCreatedTime, _SetCreatedTime)

    __swig_getmethods__["modified_time"] = _GetModifiedTime
    __swig_setmethods__["modified_time"] = _SetModifiedTime
    modified_time  = property(_GetModifiedTime, _SetModifiedTime)

    __swig_getmethods__["raw_data"] = _GetRawData
    __swig_setmethods__["raw_data"] = _SetRawData
    raw_data  = property(_GetRawData, _SetRawData)

    __swig_getmethods__["comment"] = _GetComment
    __swig_setmethods__["comment"] = _SetComment
    comment  = property(_GetComment, _SetComment)

   
    def _get_data(self):
        rows_vector = self._GetData()
        result = []
        for row in rows_vector:
            result.append([cell for cell in row])
        return result
	
    __swig_getmethods__["data"] = _get_data
    data  = property(_get_data)

    def _get_data_list(self):
        return [cell for cell in self._GetVectorData()]
    __swig_getmethods__["data_list"] = _get_data_list
    data_list  = property(_get_data_list)

	
    def _get_data_by_columns(self):
        rows_vector = self._GetMappedData()
        result = []
        for row in rows_vector:
            line = {}
            for col_name, value in row.items():
                line[col_name]=value
            result.append(line)
        return result

    __swig_getmethods__["data_by_columns"] = _get_data_by_columns
    data_by_columns  = property(_get_data_by_columns)


	%}
};
