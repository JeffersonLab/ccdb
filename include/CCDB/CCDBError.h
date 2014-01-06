#ifndef _DCcdbError_
#define _DCcdbError_
#include <string>
#include <iostream>
#include <queue>
#include <map>

#include "CCDB/Console.h"

namespace ccdb {

class CCDBError {
public:
	CCDBError();

	/** @brief gets source of an error 
	*@return mSource
	*/
	std::string GetSource() const { return mSource; }

	/** @brief sets source of an error 
	*@param [in] mSource
	*/
	void SetSource(std::string val) { mSource = val; }

	/** @brief gets error message 
	*@return mMessage
	*/
	std::string GetMessage() const { return mMessage; }

	/** @brief sets error message 
	*@param [in] Message
	*/
	void SetMessage(std::string val) { mMessage = val; }

	/** @brief gets error id @see DCCDBGobals.h
	*@return mId
	*/
	int GetId() const { return mId; }

	/** @brief sets error id @see DCCDBGobals.h
	*@param [in] mId
	*/
	void SetId(int val) { mId = val; }

	
	/** @brief gets thread sent the error
	*@return mThreadId
	*/
	unsigned int GetThreadId() const { return mThreadId; }

	/** @brief sets thread sent the error
	*@param [in] mThreadId
	*/
	void SetThreadId(unsigned int val) { mThreadId = val; }

	/** @brief gets general error key
	*@return mDescription
	*/
	std::string GetDescription() const;

	/** @brief gets general error key
	*@return mDescription
	*/
	std::string GetErrorKey() const;

	/** @brief gets level of error
	* 0-fatal, 1 - error, 2 - warning
	*@return mLevel
	*/
	int GetLevel() const { return mLevel; }
	/** @brief sets
	*0-fatal, 1 - error, 2 - warning, 
	*@param [in] mLevel
	*/
	void SetLevel(int val) { mLevel = val; }

protected:

private:
	static void FillErrors(); ///Fills generic error descriptions

	std::string mMessage;	
	std::string mSource;	
	int mId;	
	int mLevel;  //0-fatal, 1 - error, 2 - warning
	
	static std::map<int, std::string > mDescriptions;
	static std::map<int, std::string > mKeys;
	unsigned int mThreadId;
	

	CCDBError(CCDBError const&);					    // copy constructor is private
	CCDBError& operator=(CCDBError const&);		// assignment operator is private
};
}
#endif // _DCcdbError_
