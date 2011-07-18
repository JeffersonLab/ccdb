#include "DConsole.h"
#ifdef WIN32
#include <Windows.h>
#endif
#ifndef _WIN32
#include <unistd.h>
#endif
#include <stdarg.h>
#include <stdio.h>
#ifndef _WIN32
#include <sys/time.h>
#endif
#include <stdlib.h>
#ifdef _WIN32
#define vsnprintf _vsnprintf
#endif
#include "DStringUtils.h"


//All C++ programmers must Love such macros crap =)
#ifndef va_copy
#  ifdef __va_copy
#    define va_copy(dest, src) __va_copy(dest, src)
#  else
#    define va_copy(dest, src) (dest) = (src)
#  endif
#endif

ccdb::DConsole::DConsole(ostream *out):
	mOutStream(out)
{
#ifdef WIN32
	mConsoleHandle=GetStdHandle(STD_OUTPUT_HANDLE);
	PCONSOLE_SCREEN_BUFFER_INFO info = 0;

	if(GetConsoleScreenBufferInfo(mConsoleHandle,info))
	{
		mDefultAttributes =info->wAttributes;
	}
	else
	{
		mDefultAttributes = DConsole::cGray;
	}

	mForeground = static_cast<ConsoleColors>(mDefultAttributes&3 + (mDefultAttributes&FOREGROUND_INTENSITY)?8:0 );
	mBackground = static_cast<ConsoleColors>((mDefultAttributes>>4)&3);

#endif //#ifdef WIN32
}

ccdb::DConsole::~DConsole()
{
	//Looks like nothing to do here!
}

void ccdb::DConsole::ResetTextProperties()
{
	//TODO:actually we have to do something here with fForeground and fBackground when we reset
	mAttributes = cReset;
	mBackground = cBlack;
	mForeground = cWhite;

	//W I N D O W S implementation
#ifdef WIN32
	//This is how the text is written in windows
	SetConsoleTextAttribute(mConsoleHandle, mDefultAttributes);

	//nothing to do more
	return;
#endif //#ifdef WIN32

	//L I N U X implementation
	*mOutStream<<"\033[0;m";
}


void ccdb::DConsole::SetTextAttribute( int attr)
{
	mAttributes = attr;
	if(mUseColors)
	{
	//W I N D O W S implementation
#ifdef WIN32
		//A way to do an intensity in windows
		if(attr & DConsole::cBright) SetConsoleTextAttribute(mConsoleHandle, FOREGROUND_INTENSITY);
		return; //nothing to do more
#endif //#ifdef WIN32
		//Begin to process our pattern
		string pattern = "\033[";
		if(attr == 0)					pattern.append("00;");	//Reset All Attributes (return to normal mode)
		if(attr & DConsole::cBright)	pattern.append("01;");	//Bright (Usually turns on BOLD)
		if(attr & DConsole::cDim)		pattern.append("02;");	//Dim
		if(attr & DConsole::cUnderline)	pattern.append("03;");	//Underline
		if(attr & DConsole::cBlink)		pattern.append("04;");	//Blink
		if(attr & DConsole::cReverse)	pattern.append("05;");	//Reverse
		if(attr & DConsole::cHidden)	pattern.append("06;");	//unknown =)
		pattern.append("m");	//Now we finalize the pattern
		*mOutStream<<pattern;	//Write pattern to disk
	}
}

void ccdb::DConsole::SetForegroundColor( ConsoleColors foreground)
{
	if(mUseColors)
	{
		//W I N D O W S implementation
	#ifdef WIN32
		WORD colorSetup=0;
		//if(  8 < static_cast<int>(foreground) ) colorSetup|=FOREGROUND_INTENSITY;

		//A way to do an intensity in windows
		if(mAttributes & DConsole::cBright) colorSetup|=FOREGROUND_INTENSITY;
		colorSetup |= foreground;
		colorSetup |= mBackground <<4;
		//This is how the text is written in windows
		SetConsoleTextAttribute(mConsoleHandle, colorSetup);

		return; //nothing to do more
	#endif //#ifdef WIN32
		mForeground = foreground;

		//Begin to process our pattern
		string pattern = "\033[";

		//process bright color for foreground
		int intForeground = static_cast<int>(foreground);
		if( intForeground > 8  )
		{
			//bright colors in linux...
			pattern.append("01;");
			foreground = static_cast<DConsole::ConsoleColors> (intForeground - 8);
		}
		//Now we finalize the pattern
		pattern.append("%dm");

		//Command is the control command to the terminal
		char command[32];
		sprintf(command, pattern.c_str(), foreground + 30);
		*mOutStream<<command;
	}
}

void ccdb::DConsole::SetBackgroundColor( ConsoleColors background)
{
	if (mUseColors)
	{

		//W I N D O W S implementation
	#ifdef WIN32
		WORD colorSetup=0;
		if(  8 < static_cast<int>(background) ) colorSetup|=FOREGROUND_INTENSITY;

		//A way to do an intensity in windows
		if(mAttributes & DConsole::cBright) colorSetup|=FOREGROUND_INTENSITY;
		colorSetup |= mForeground;
		colorSetup |= background <<4;
		//This is how the text is written in windows
		SetConsoleTextAttribute(mConsoleHandle, colorSetup);

		return; //nothing to do more
	#endif //#ifdef WIN32

		mBackground = background;

		string pattern = "\033[%dm";
		//There is no bright backgrounds (it assumes!) so we correct it
		int intBackground = static_cast<int>(background);
		if( intBackground > 8  )
		{
			background = static_cast<DConsole::ConsoleColors> (intBackground - 8);
		}

		//Command is the control command to the terminal
		char command[32];
		sprintf(command, pattern.c_str(), background + 40);
		*mOutStream<<command;
	}
}

void ccdb::DConsole::SetTextParams( int attr, ConsoleColors foreground, ConsoleColors background)
{
	//If we need we store the attributes
	mForeground = foreground;
	mBackground = background;
	mAttributes = attr;

	if(mUseColors)
	{
		//W I N D O W S implementation
#ifdef WIN32
		WORD colorSetup=0;
		if(  8 < static_cast<int>(foreground) )
			colorSetup|=FOREGROUND_INTENSITY;

		//A way to do an intensity in windows
		if(attr & DConsole::cBright) colorSetup|=FOREGROUND_INTENSITY;
		colorSetup |= foreground;
		colorSetup |= background <<4;
		//This is how the text is written in windows
		SetConsoleTextAttribute(mConsoleHandle, colorSetup);

		return; //nothing to do more
#endif //#ifdef WIN32

		//Linux implementation

		//Begin to process our pattern
		string pattern = "\033[";

		//process bright color for foreground
		int intForeground = static_cast<int>(foreground);
		if( intForeground > 8  )
		{
			//bright colors in linux...
			pattern.append("01;");
			foreground = static_cast<DConsole::ConsoleColors> (intForeground - 8);
		}

		//There is no bright backgrounds (it assumes!) so we correct it
		int intBackground = static_cast<int>(background);
		if( intBackground > 8  )
		{
			background = static_cast<DConsole::ConsoleColors> (intBackground - 8);
		}

		if(attr == 0)					pattern.append("00;");	//Reset All Attributes (return to normal mode)
		if(attr & DConsole::cBright)	pattern.append("01;");	//Bright (Usually turns on BOLD)
		if(attr & DConsole::cDim)		pattern.append("02;");	//Dim
		if(attr & DConsole::cUnderline)	pattern.append("03;");	//Underline
		if(attr & DConsole::cBlink)		pattern.append("04;");	//Blink
		if(attr & DConsole::cReverse)	pattern.append("05;");	//Reverse
		if(attr & DConsole::cHidden)	pattern.append("06;");	//unknown =)

		//Now we finalize the pattern
		pattern.append("%d;%dm");

		//Command is the control command to the terminal
		char command[32];
		sprintf(command, pattern.c_str(), foreground + 30, background + 40);
		*mOutStream<<command;
	}
}

void ccdb::DConsole::SetTextParams( ConsoleColors foreground, ConsoleColors background)
{
	//If we need we store the colors
	mForeground = foreground;
	mBackground = background;

	if(mUseColors)
	{
		//W I N D O W S implementation
#ifdef WIN32

		//This is how the text is written in windows
		WORD format = foreground | (background<<4);
		if(mAttributes & DConsole::cBlink) format |= FOREGROUND_INTENSITY;

		SetConsoleTextAttribute(mConsoleHandle, format);

		//a little bit ugly implementation


		return; //nothing to do more
#endif //#ifdef WIN32

		//Linux implementation
		char command[13];

		// Command is the control command to the terminal
		sprintf(command, "\033[%d;%dm", foreground + 30, background + 40);
		*mOutStream<<command;
	}
}

int ccdb::DConsole::Write( const char *fmt, ... )
{
	//Formatting
	va_list ap;
	va_start(ap, fmt);
	string str = DStringUtils::vFormat(fmt, ap);
	va_end(ap);

	//Writing to stream
	*mOutStream<<str;
	return str.length();
}

int ccdb::DConsole::Write( ConsoleColors color, const char *fmt, ... )
{
	//set colors
	ConsoleColors fcBackup = GetForegroundColor();	// save color
	int backAttr = GetTextAttributes();
	SetForegroundColor(color);						// set color

	//format
	va_list ap;
	va_start(ap, fmt);
	string str = DStringUtils::vFormat(fmt, ap);
	va_end(ap);

	//output
	*mOutStream<<str;

	//finalize
	SetForegroundColor(fcBackup);	// restore color
	SetTextAttribute(backAttr);	//restore attribute
	/*#ifndef WIN32
	ResetTextProperties();
	#endif*/
	return str.length();			// return number of chars
}


int ccdb::DConsole::WriteLine( const char *fmt, ... )
{
	//format
	va_list ap;
	va_start(ap, fmt);
	string str = DStringUtils::vFormat(fmt, ap);
	va_end(ap);

	//output
	*mOutStream<<str<<endl;

	// return number of chars
	return str.length();
}


int ccdb::DConsole::WriteLine()
{
	//output
	*mOutStream<<endl;
	return 1;
}

int ccdb::DConsole::WriteLine( ConsoleColors color, const char *fmt, ... )
{
	//set colors
	ConsoleColors fcBackup = GetForegroundColor();	// save color
	int backAttr = GetTextAttributes();
	SetForegroundColor(color);						// set color

	//format
	va_list ap;
	va_start(ap, fmt);
	string str = DStringUtils::vFormat(fmt, ap);
	va_end(ap);

	//output
	try
	{
		*mOutStream<<str<<endl;
	}
	catch (std::exception ex)
	{
		fprintf(stderr, "Exception caught in ccdb::DConsole::WriteLine, the message exception is:\n%s", ex.what());
		SetForegroundColor(fcBackup);	// restore color
		throw;
	}

	//finalize
	SetForegroundColor(fcBackup);		// restore color
	#ifndef WIN32
	ResetTextProperties();
	#endif
	SetForegroundColor(fcBackup);	// restore color
	SetTextAttribute(backAttr);	//restore attribute
	return str.length()	;				// return number of chars
}

void ccdb::DConsole::PrintCondition( bool condition, bool newLine /*= true*/ )
{	
	//just puts [ true ] or [ false ] depending on condition
	Write(CCDB_CONSOLE_PASSED_BRACES_COLOR, "[ ");
	
	if(condition) 
	{
		Write(CCDB_CONSOLE_PASSED_TRUE_COLOR, "true");
	}
	else 
	{
		Write(CCDB_CONSOLE_PASSED_FALSE_COLOR, "false");
	}

	Write(CCDB_CONSOLE_PASSED_BRACES_COLOR, " ]");
	
	if(newLine) WriteLine();
}







