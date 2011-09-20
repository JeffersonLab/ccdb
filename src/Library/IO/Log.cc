#include "DLog.h"
#include "DCCDBGlobals.h"
#include <string>
#include <map>

using namespace std;
namespace ccdb
{

	DConsole DLog::msConsole;
	DConsole DLog::msErrorConsole;		//output for error reporting
	DConsole DLog::msMessageConsole;
	DConsole DLog::msVerboseConsole;
	int DLog::msLastError = CCDB_NO_ERRORS;
	int DLog::mLevel = 3;
	
int DLog::GetLastError()
{
	return msLastError;
}

ostream*  DLog::GetStream()
{
	return msConsole.GetOutStream();
}

void DLog::SetStream(ostream* val)
{
	msConsole.SetOutStream(val);
}

void DLog::Status(bool status, const string& description)
{
}

void DLog::Error(int errorCode, const string& module, const string& message)
{
	msLastError=errorCode;
	msConsole.Write(DConsole::cBrightRed, "Error [%i]: ", errorCode);
	msConsole.Write(DConsole::cBrightWhite, "in [");
	msConsole.Write(DConsole::cCyan, "%s", module.c_str());
	msConsole.Write(DConsole::cBrightWhite, "] ");
	msConsole.WriteLine("%s ", message.c_str());
}

void DLog::Warning( int errorCode, const string& module, const string& message )
{
	msConsole.Write(DConsole::cBrightRed, "Error [%i]: ", errorCode);
	msConsole.Write(DConsole::cBrightWhite, "in [");
	msConsole.Write(DConsole::cCyan, "%s", module.c_str());
	msConsole.Write(DConsole::cBrightWhite, "] ");
	msConsole.WriteLine("%s ", message.c_str());
}

void DLog::Message( const string& message )
{
	msConsole.WriteLine("%s ", message.c_str());
}

void DLog::Verbose( const string& module, const string& message )
{
	if(mLevel < 4) return;
	
	msConsole.Write("Verbose ");
	msConsole.Write(DConsole::cBrightWhite, "[");
	msConsole.Write(DConsole::cCyan, "%s", module.c_str());
	msConsole.Write(DConsole::cBrightWhite, "] ");
	msConsole.WriteLine("%s ", message.c_str());

}

}
void ccdb::DLog::SetUseColors(bool useIt)
{
	DLog::msConsole.SetUseColors(useIt);
	DLog::msErrorConsole.SetUseColors(useIt);		//output for error reporting
	DLog::msMessageConsole.SetUseColors(useIt);
	DLog::msVerboseConsole.SetUseColors(useIt);
}

map<int, string> gCCDBErrorCodes;
