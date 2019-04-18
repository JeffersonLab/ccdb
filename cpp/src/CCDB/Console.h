/*
 * DebugConsole.h
 *
 *  Created on: Sep 27, 2010
 *      Author: romanov
 */

#ifndef _Console_
#define _Console_

#ifdef WIN32
#define _CRT_SECURE_NO_WARNINGS
#include <Windows.h>
#endif

//#include <stdargs.h>
//#include <varargs.h>
#include <stdio.h>
#include <stdarg.h>
#include <string>


#include <iosfwd>
#include <iostream>
#include <ostream>

//color of [true] / [false]
#define CCDB_CONSOLE_PASSED_BRACES_COLOR cWhite
#define CCDB_CONSOLE_PASSED_TRUE_COLOR   cBrightGreen
#define CCDB_CONSOLE_PASSED_FALSE_COLOR  cBrightRed
using namespace std;

namespace ccdb {

class Console
{
public:
	/*
	 * The sequence to be printed or echoed to the terminal is

	 <ESC>[{attr};{fg};{bg}m
	 \033[{attr};{fg};{bg}m

	 <ESC> is ctrl+V or  \033 in Linux console or in xterm, konsole, kvt, etc.
	 Then {attr}, {fg}, {bg} have to be replaced with the correct value to get the corresponding effect.
	 attr is the attribute like blinking or underlined etc..
	 fg and bg are foreground and background colors respectively.
	 You don't have to put braces around the number. Just writing the number will suffice.
	 */

#ifdef WIN32
	enum ConsoleColors {
		cBlack		= 0,
		cBlue		= 1,
		cGreen		= 2,
		cCyan		= 3,
		cRed		= 4,
		cMagenta	= 5,
		cYellow		= 6,
		cWhite		= 7,
		cGray		= 8,
		cBrightBlue		= 9,
		cBrightGreen	= 10,
		cBrightCyan		= 11,
		cBrightRed		= 12,
		cBrightMagenta	= 13,
		cBrightYellow	= 14,
		cBrightWhite	= 15,
		cDefault		= 16
	};
#else	//!WIN32
	enum ConsoleColors {

		cBlack = 0,
		cRed = 1,
		cGreen = 2,
		cYellow = 3,
		cBlue = 4,
		cMagenta = 5,
		cCyan = 6,
		cWhite = 7,
		cGray = 8,
		cBrightRed = 9,
		cBrightGreen = 10,
		cBrightYellow = 11,
		cBrightBlue = 12,
		cBrightMagenta = 13,
		cBrightCyan = 14,
		cBrightWhite = 15,
		cDefault = 16
	};
#endif //WIN32

	enum ConsoleAttributes {
		cReset		= 0,	//Reset All Attributes (return to normal mode)
		cBright		= 1,	//Bright (Usually turns on BOLD)
		cDim		= 2,	//Dim
		cUnderline	= 4,	//Underline
		cBlink		= 8,	//Blink
		cReverse	= 16,	//Reverse
		cHidden		= 32
	//	Hidden
	};

	
	Console(ostream *out=&cout);	///Constructor

	virtual	~Console();			//! Destructor

	/** 
	 * Returns outstream that is used as the console output
	 *
	 * @returns   std::ostream*
	 */
	std::ostream*	GetOutStream() const { return mOutStream; }

	/** 
	 * Sets stream that will be used as the console output
	 *
	 * @param     ostream * val
	 * @returns   void
	 */
	void			SetOutStream(ostream * val) { mOutStream = val; }

	/** @brief resets text attributes
	 * 
	 * Sets the colors to the "default" - the colors that whas when the application was loaded
	 * @returns   void
	 */
	void	ResetTextProperties();

	/** @brief Sets attributes
	 * SetTextParams
	 *
	 * @param     int attr attributes
	 * @param     ConsoleColors foreground foreground color
	 * @param     ConsoleColors background background colors
	 * @returns   void
	 */
	void	SetTextParams(int attr, ConsoleColors foreground, ConsoleColors background);

	/** @brief
	 * SetTextParams
	 *
	 * @param foreground
	 * @param background
	 * @returns void
	 */
	void	SetTextParams(ConsoleColors foreground, ConsoleColors background);

	/** @brief
	 * SetTextAttribute
	 *
	 * @param     int attr
	 * @returns   void
	 */
	void	SetTextAttribute(int attr);
	/** @brief
	 * GetTextAttributes
	 *
	 * @returns   int
	 */
	int		GetTextAttributes() const {return mAttributes;}

	/** @brief
	 * SetForegroundColor
	 *
	 * @param     ConsoleColors foreground
	 * @returns   void
	 */
	void			SetForegroundColor(ConsoleColors foreground);
	/** @brief
	 * GetForegroundColor
	 *
	 * @returns   ccdb::Console::ConsoleColors
	 */
	ConsoleColors		GetForegroundColor() const {return mForeground;}

	/** @brief
	 * SetBackgroundColor
	 *
	 * @param     ConsoleColors background
	 * @returns   void
	 */
	void			SetBackgroundColor(ConsoleColors background);
	/** @brief
	 * GetBackgroundColor
	 *
	 * @returns   ccdb::Console::ConsoleColors
	 */
	ConsoleColors		GetBackgroundColor() const {return mBackground;}

	/** @brief
	 * Write
	 *
	 * @param     const char * fmt
	 * @param     ...
	 * @returns   int
	 */
	int			Write(const char *fmt, ...);
	/** @brief
	 * Write
	 *
	 * @param     ConsoleColors color
	 * @param     const char * fmt
	 * @param     ...
	 * @returns   int
	 */
	int			Write(ConsoleColors color, const char *fmt, ...);
	/** @brief
	 * WriteLine
	 *
	 * @param     const char * fmt
	 * @param     ...
	 * @returns   int
	 */
	int			WriteLine(const char *fmt, ...);
	/** @brief
	 * WriteLine
	 *
	 * @param     ConsoleColors color
	 * @param     const char * fmt
	 * @param     ...
	 * @returns   int
	 */
	int			WriteLine(ConsoleColors color, const char *fmt, ...);
	/** @brief
	 * WriteLine
	 *
	 * @returns   int
	 */
	int			WriteLine();

	/** @brief
	 * GetUseColors
	 *
	 * @returns   bool
	 */
	bool GetUseColors() const {	return mUseColors;}

	/** @brief
	 * SetUseColors
	 *
	 * @param     bool useColors
	 * @returns   void
	 */
	void SetUseColors(bool useColors) {	this->mUseColors = useColors;}
	
	/** @brief prints passed/ label depending on condition
	 *
	 * @param     bool condition
	 * @param     bool newLine
	 * @returns   void
	 */
	void PrintCondition(bool condition, bool newLine = true);

protected:

#ifdef WIN32
	HANDLE mConsoleHandle;			//This is console handle that
	WORD mDefultAttributes;
#endif
	std::ostream *mOutStream;		//This the stream we are putting all to

	bool		mUseColors;			//do we use colors for console output or not
	ConsoleColors	mForeground;	//current foreground color
	ConsoleColors	mBackground;	//current background
	int		mAttributes;			//current set of attributes (bits)

};
}
#endif /* _Console_ */
