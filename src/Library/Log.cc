#include <string>
#include <map>

#include "CCDB/Log.h"
#include "CCDB/Globals.h"
#include "CCDB/GlobalMutex.h"

using namespace std;
namespace ccdb
{
	Console Log::msConsole;
	Console Log::msErrorConsole;		//output for error reporting
	Console Log::msMessageConsole;
	Console Log::msVerboseConsole;
	int Log::msLastError = CCDB_NO_ERRORS;
	int Log::mErrorLevel = 3;
	
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
    if(mErrorLevel<1)return;
    
    //CCDBGlobalMutex::Instance()->LogLock();
	msLastError=errorCode;
	msConsole.Write(Console::cBrightRed, "Error [%i]: ", errorCode);
	msConsole.Write(Console::cBrightWhite, "in [");
	msConsole.Write(Console::cCyan, "%s", module.c_str());
	msConsole.Write(Console::cBrightWhite, "] ");
	msConsole.WriteLine("%s ", message.c_str());
    // CCDBGlobalMutex::Instance()->LogRelease();
}

void Log::Warning( int errorCode, const string& module, const string& message )
{
    if(mErrorLevel<2) return;

    //CCDBGlobalMutex::Instance()->LogLock();
	msConsole.Write(Console::cBrightRed, "Error [%i]: ", errorCode);
	msConsole.Write(Console::cBrightWhite, "in [");
	msConsole.Write(Console::cCyan, "%s", module.c_str());
	msConsole.Write(Console::cBrightWhite, "] ");
	msConsole.WriteLine("%s ", message.c_str());
    //CCDBGlobalMutex::Instance()->LogRelease();
}

void Log::Message( const string& message )
{
    if(mErrorLevel<3) return;

   // CCDBGlobalMutex::Instance()->LogLock();
	msConsole.WriteLine("%s ", message.c_str());
    //CCDBGlobalMutex::Instance()->LogRelease();
}

void Log::Verbose( const string& module, const string& message )
{
	if(mErrorLevel < 4) return;
	
   // CCDBGlobalMutex::Instance()->LogLock();
	msConsole.Write("Verbose ");
	msConsole.Write(Console::cBrightWhite, "[");
	msConsole.Write(Console::cCyan, "%s", module.c_str());
	msConsole.Write(Console::cBrightWhite, "] ");
	msConsole.WriteLine("%s ", message.c_str());
   // CCDBGlobalMutex::Instance()->LogRelease();

}


void Log::SetUseColors(bool useIt)
{
	Log::msConsole.SetUseColors(useIt);
	Log::msErrorConsole.SetUseColors(useIt);		//output for error reporting
	Log::msMessageConsole.SetUseColors(useIt);
	Log::msVerboseConsole.SetUseColors(useIt);
}
}
map<int, string> gCCDBErrorCodes;
