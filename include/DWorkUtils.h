#ifndef DWorkUtils_h__
#define DWorkUtils_h__
#include <vector>
#include "Model/DDirectory.h"
#include "Model/DConstantsTypeTable.h"
#include "Model/DAssignment.h"
#include "DConsole.h"

using namespace std;
using namespace ccdb;

void PrintDirectoryTree(DDirectory *dir,  bool printFullPath=false,int level=0);

void PrintConstantTypeTable(DConstantsTypeTable *table );

void PrintAssignmentVertical(DConsole & console, DAssignment *assignment, bool printHeader=true, bool displayBorders=true, DConsole::ConsoleColors headColor=DConsole::cGray, DConsole::ConsoleColors typeColor=DConsole::cBrightBlue, DConsole::ConsoleColors valueColor=DConsole::cBrightMagenta, DConsole::ConsoleColors borderColor=DConsole::cGray);
void PrintAssignmentHorisontal(DAssignment *assignment);
void PrintConstantsTypeTable(DConstantsTypeTable *table);
#endif // DWorkUtils_h__
