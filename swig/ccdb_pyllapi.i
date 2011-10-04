/* File : ccdb.i */
%module ccdb_pyllapi

%apply unsigned int { dbkey_t };
%apply unsigned long { time_t };

%include "std_string.i"
%apply const std::string& {std::string* foo};
/*%apply const string& {std::string* foo};*/
%include "std_map.i"

%include "std_vector.i"


%include "RunRange.i"
%include "Variation.i"
%include "Directory.i"
%include "ConstantsTypeTable.i"
%include "ConstantsTypeColumn.i"
%include "Assignment.i"
%include "DataProvider.i"
%include "MySQLDataProvider.i"


%{
#include "CCDB/Globals.h"
/*#define #define SWIG_FILE_WITH_INIT
#include "Model/RunRange.h"
using namespace ccdb;*/
%}


using namespace std;

%template(AssignmentVector) vector<Assignment *>;
%template(DirectoryVector) vector<Directory *>;
%template(ConstantsTypeTableVector) vector<ConstantsTypeTable *>;
%template(ConstantsTypeColumnVector) vector<ConstantsTypeColumn *>;
%template(StringVector) std::vector<std::string>;
%template(StringVectorVector) std::vector<std::vector<std::string> >;
%template(StringStringMap) std::map<std::string, std::string>;
%template(StringStringMapVector) std::vector<std::map<std::string,std::string> >;
/* Let's just grab the original header file here */

//%include "../source/Model/RunRange.h"
