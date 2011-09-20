#include <string>
#include <map>

#include "CCDB/IO/Log.h"
#include "CCDB/CCDBGlobals.h"

using namespace std;
namespace ccdb
{

	Console Log::msConsole;
	Console Log::msErrorConsole;		//output for error reporting
	Console Log::msMessageConsole;
	Console Log::msVerboseConsole;
	int Log::msLastError = CCDB_NO_ERRORS;
	int Log::mLevel = 3;
	
int Log::GetLastError()
{
	return msLastError;
}

ostream*  Log::GetStream()
{
	return msConsole.GetOutStream();
}

void Log::SetStream(ostream* val)
{
	msConsole.SetOutStream(val);
}

void Log::Status(bool status, const string& description)
{
}

void Log::Error(int errorCode, const string& module, const string& message)
{
	msLastError=errorCode;
	msConsole.Write(Console::cBrightRed, "Error [%i]: ", errorCode);
	msConsole.Write(Console::cBrightWhite, "in [");
	msConsole.Write(Console::cCyan, "%s", module.c_str());
	msConsole.Write(Console::cBrightWhite, "] ");
	msConsole.WriteLine("%s ", message.c_str());
}

void Log::Warning( int errorCode, const string& module, const string& message )
{
	msConsole.Write(Console::cBrightRed, "Error [%i]: ", errorCode);
	msConsole.Write(Console::cBrightWhite, "in [");
	msConsole.Write(Console::cCyan, "%s", module.c_str());
	msConsole.Write(Console::cBrightWhite, "] ");
	msConsole.WriteLine("%s ", message.c_str());
}

void Log::Message( const string& message )
{
	msConsole.WriteLine("%s ", message.c_str());
}

void Log::Verbose( const string& module, const string& message )
{
	if(mLevel < 4) return;
	
	msConsole.Write("Verbose ");
	msConsole.Write(Console::cBrightWhite, "[");
	msConsole.Write(Console::cCyan, "%s", module.c_str());
	msConsole.Write(Console::cBrightWhite, "] ");
	msConsole.WriteLine("%s ", message.c_str());

}

}
void ccdb::Log::SetUseColors(bool useIt)
{
	Log::msConsole.SetUseColors(useIt);
	Log::msErrorConsole.SetUseColors(useIt);		//output for error reporting
	Log::msMessageConsole.SetUseColors(useIt);
	Log::msVerboseConsole.SetUseColors(useIt);
}

map<int, string> gCCDBErrorCodes;
