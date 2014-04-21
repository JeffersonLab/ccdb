#include "CCDB/Helpers/WorkUtils.h"
#include "CCDB/Console.h"
#include "CCDB/Helpers/StringUtils.h"

#include <assert.h>

using namespace ccdb;

void PrintDirectoryTree( Directory *dir, bool printFullPath/*=false*/,int level/*=0*/ )
{
	//TODO: Implement method

	Console console;
	if(!printFullPath)
	{
		for (int i=0; i< level; i++)
		{
			console.Write(Console::cBrightBlue, "--");
		}
		if(level != 0)
		{
			console.Write(Console::cBrightBlue,"> ");
		}

		console.WriteLine(dir->GetName().c_str());
	}
	else
	{
		console.WriteLine(dir->GetFullPath().c_str());
	}

	const vector<Directory*>& subDirs=dir->GetSubdirectories();
	if(subDirs.size()>0)
	{
		for(vector<Directory *>::const_iterator it=subDirs.begin(); it<subDirs.end(); ++it)
		{
			PrintDirectoryTree(*it, printFullPath, level+1);
		}
	}
	
}

void PrintAssignmentVertical( Console & console, Assignment *assignment, bool printHeader/*=true*/, bool displayBorders/*=true*/, Console::ConsoleColors headColor/*=Console::cBrightBlue*/, Console::ConsoleColors typeColor/*=Console::cGray*/, Console::ConsoleColors valueColor/*=Console::cGray*/, Console::ConsoleColors borderColor/*=Console::cGreen*/ )
{
	const char * border = (displayBorders)? "|" : " ";
	
	
	ConstantsTypeTable *table = assignment->GetTypeTable(); 
	if(table == NULL) return;

	vector<string> columnNames = table->GetColumnNames();
	vector<string> columnTypes = table->GetColumnTypeStrings();
	vector<string> data = assignment->GetVectorData();
	int columnsNum = columnNames.size();
	assert(columnNames.size() == columnTypes.size());
	assert(data.size() % columnsNum == 0 );
	int minLength = 10;
	int *columnLengths = new int[columnsNum];
	int totalDataLength = 0;

	//determine column length
	for(int i=0; i<columnsNum; i++)
	{
		columnLengths[i] = (columnNames[i].length()>minLength)? columnNames[i].length() : minLength;
		totalDataLength += columnLengths[i];
	}

	//this is our cap, if we need it.... 
	string cap;
	cap.assign(totalDataLength + 3 * columnsNum + 1,'-');

	//print header if needed
	if(printHeader)
	{	
		//cap?
		if(displayBorders) console.WriteLine(borderColor, cap.c_str());
		
		//names line
		for(int i=0; i< columnsNum; i++)
		{
			console.Write(borderColor, "%s",border);
			console.Write(headColor, StringUtils::Format(" %%-%is ", columnLengths[i]).c_str(), columnNames[i].c_str());
		}
		console.WriteLine(borderColor, "%s",border);

		//types line
		for(int i=0; i< columnsNum; i++)
		{
			console.Write(borderColor, "%s",border);
			console.Write(typeColor, StringUtils::Format(" %%-%is ", columnLengths[i]).c_str(), columnTypes[i].c_str());
		}
		console.WriteLine(borderColor, "%s",border);
	}
	//cap?
	if(displayBorders) console.WriteLine(borderColor, cap.c_str());

	//data line by line
	vector<string>::iterator colIter = data.begin();
	int columnIter = 0;

	while(colIter<data.end())
	{
		//place data 
		console.Write(borderColor, "%s",border);
		console.Write(valueColor, StringUtils::Format(" %%-%is ", columnLengths[columnIter]).c_str(), (*colIter).c_str());
		columnIter++;
		colIter++;
				
		//new line?
		if(columnIter == columnsNum)
		{
			columnIter = 0;
			console.WriteLine(borderColor, "%s",border);
		}
	}

	//cap?
	if(displayBorders) console.WriteLine(borderColor, cap.c_str());
	delete[] columnLengths;
}

void PrintConstantsTypeTable( ConstantsTypeTable *table )
{
	Console console;
	console.WriteLine("Table : %s", table->GetName().c_str());
	console.WriteLine("Comment: %s", table->GetComment().c_str());
	console.WriteLine("Columns: %i Rows: %i", table->GetColumnsCount(), table->GetNColumnsFromDB(), table->GetRowsCount());

	vector<string> columnNames = table->GetColumnNames();
	vector<string> columnTypes = table->GetColumnTypeStrings();
	
	int columnsNum = columnNames.size();
	assert(columnNames.size() == columnTypes.size());
	int nameColumnLength = 10;

	//determine column length
	for(int i=0; i<columnsNum; i++)
	{
		if(columnNames[i].length() > nameColumnLength) nameColumnLength = columnNames[i].length();
	}
	//this strange structure is just to create 
	console.WriteLine(StringUtils::Format(" %%-%is           type", nameColumnLength).c_str(), "name");


	//names line
	for(int i=0; i< columnsNum; i++)
	{
		console.WriteLine(StringUtils::Format(" %%-%is           %%s", nameColumnLength).c_str(), columnNames[i].c_str(), columnTypes[i].c_str());
	}
}
