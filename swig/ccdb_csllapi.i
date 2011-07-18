/* File : ccdb.i */
%module ccdb_csllapi

%apply unsigned int { dbkey_t };

%include "std_string.i"
%apply const std::string& {std::string* foo};

%include "std_vector.i"


%include "DRunRange.i"
%include "DDirectory.i"
%include "DDataProvider.i"
%include "DConstantTypeTable.i"

%{
#include "DCCDBGlobals.h"
/*#define #define SWIG_FILE_WITH_INIT
#include "Model/DRunRange.h"
using namespace ccdb;*/
	
%}


using namespace std;
%template(DDirectoryVector) vector<DDirectory *>;
/* Let's just grab the original header file here */

//%include "../source/Model/DRunRange.h"
