#ifndef DWorkUtils_h__
#define DWorkUtils_h__
#include <vector>
#include "CCDB/Model/Directory.h"
#include "CCDB/Model/ConstantsTypeTable.h"
#include "CCDB/Model/Assignment.h"
#include "CCDB/Console.h"

using namespace std;
using namespace ccdb;

void PrintDirectoryTree(Directory *dir,  bool printFullPath=false,int level=0);

void PrintConstantTypeTable(ConstantsTypeTable *table );

void PrintAssignmentVertical(Console & console, Assignment *assignment, bool printHeader=true, bool displayBorders=true, Console::ConsoleColors headColor=Console::cGray, Console::ConsoleColors typeColor=Console::cBrightBlue, Console::ConsoleColors valueColor=Console::cBrightMagenta, Console::ConsoleColors borderColor=Console::cGray);
void PrintAssignmentHorisontal(Assignment *assignment);
void PrintConstantsTypeTable(ConstantsTypeTable *table);
#endif // DWorkUtils_h__
