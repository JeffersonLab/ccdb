/* File : ccdb.i */
%module ccdb_pyllapi

%apply unsigned int { dbkey_t };
%apply unsigned long { time_t };


%include "std_string.i"
%apply const std::string& {std::string* foo};
%include "std_map.i"

%include "std_vector.i"

/* renaming objects! */
%rename(RunRange) DRunRange;
%rename(Variation) DVariation;
%rename(Directory) DDirectory;
%rename(DataProvider) DDataProvider;
%rename(MySQLDataProvider) DMySQLDataProvider;
%rename(ConstantsTypeTable) DConstantsTypeTable;
%rename(ConstantsTypeColumn) DConstantsTypeColumn;
%rename(Assignment) DAssignment;


%include "DRunRange.i"
%include "DVariation.i"
%include "DDirectory.i"
%include "DDataProvider.i"
%include "DMySQLDataProvider.i"
%include "DConstantsTypeTable.i"
%include "DConstantsTypeColumn.i"
%include "DAssignment.i"


%{
#include "DCCDBGlobals.h"
/*#define #define SWIG_FILE_WITH_INIT
#include "Model/DRunRange.h"
using namespace ccdb;*/
	
%}


using namespace std;
%template(AssignmentVector) vector<DAssignment *>;
%template(DirectoryVector) vector<DDirectory *>;
%template(ConstantsTypeTableVector) vector<DConstantsTypeTable *>;
%template(ConstantsTypeColumnVector) vector<DConstantsTypeColumn *>;
%template(StringVector) std::vector<std::string>;
%template(StringVectorVector) std::vector<std::vector<std::string> >;
%template(StringStringMap) std::map<std::string, std::string>;
%template(StringStringMapVector) std::vector<std::map<std::string,std::string> >;
/* Let's just grab the original header file here */

//%include "../source/Model/DRunRange.h"
