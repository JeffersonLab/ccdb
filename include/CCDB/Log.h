#ifndef _Log_
#define _Log_
/** ****************************************************
 * @file 
 *
 * @author Dmitry A Romanov
 * @date november 2010
 *
 * *****************************************************
 */ 

#include <string>
#include <iostream>
#include <queue>

#include "CCDB/Console.h"

namespace ccdb
{

/**
 * Log class. Write errors, love children...
 */
class Log {
public:
    /** @brief writes status
     *
     * @param     bool status
     * @param     const string& description
     * @return   void
     */
    static void Status(bool status, const string& description);

    /** @brief Logs error to stream
     *
     * @param errorCode Error codes see DCCDBGlobals.h
     * @param module    Caller should specify method name here
     * @param message   Message of the error
     * @return   void
     */
    static void Error(int errorCode, const string& module, const string& message);

    /** @brief Logs Warning to stream
     *
     * @param errorCode Error codes see DCCDBGlobals.h
     * @param module    Caller should specify method name here
     * @param message   Message of the Warning
     * @return   void
     */
    static void Warning(int errorCode, const string& module, const string& message);

    /** @brief Logs Warning to stream
     *
     * @param message   Message
     * @return   void
     */
    static void Message(const string& message);

    /** @brief Logs Verbose message to stream
     *
     * Probably this function should handle debug info
     *
     * @param module    Caller should specify method name here
     * @param message   Message of the error
     * @return   void
     */
    static void Verbose(const string& module, const string& message);

    /** @brief
     * SetStream
     *
     * @param     ostream * val
     * @return   void
     */
    static void SetStream(ostream * val);

    /** @brief Returns pointer to current stream
     * GetStream
     *
     * @return   ostream *
     */
    static ostream *GetStream();

    /** @brief return last error code
     *
     * @return   int
     */
    static int  GetLastError();
    
    static void SetUseColors(bool useIt);

    static void SetErrorLevel(int level)
    {
        //0-fatal, 1 - error, 2 - warning, 3 - message, 4 - verbose
        if(level<-1 || level>4) return;
        mErrorLevel = level;
    }
protected:

private:
    Log() {}                               /// Private it can  not be called
    Log(Log const&) {}                     /// copy constructor is private
    Log& operator=(Log const&);            /// assignment operator is private
    static Console msConsole;              /// standard output console
    static Console msErrorConsole;         /// output for error reporting
    static Console msMessageConsole;       /// Console for messages
    static Console msVerboseConsole;       /// console for verbose messages
    static int msLastError;
    static int mErrorLevel; //0-fatal, 1 - error, 2 - warning, 3 - message, 4 - verbose
};
}
#endif // _Log_
