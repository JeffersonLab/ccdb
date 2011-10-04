%{
#include "CCDBError.h"
%}
\

class CCDBError {
public:
	CCDBError();

	/** @brief gets source of an error 
	*@return mSource
	*/
	std::string GetSource() const;

	/** @brief sets source of an error 
	*@param [in] mSource
	*/
	void SetSource(std::string val);

	/** @brief gets error message 
	*@return mMessage
	*/
	std::string GetMessage() const;

	/** @brief sets error message 
	*@param [in] Message
	*/
	void SetMessage(std::string val);

	/** @brief gets error id @see CCDBGobals.h
	*@return mId
	*/
	int GetId() const;

	/** @brief sets error id @see CCDBGobals.h
	*@param [in] mId
	*/
	void SetId(int val);

	
	/** @brief gets thread sended the error
	*@return mThreadId
	*/
	unsigned int GetThreadId() const;

	/** @brief sets thread sended the error
	*@param [in] mThreadId
	*/
	void SetThreadId(unsigned int val);

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
	int GetLevel() const;

	/** @brief sets
	*0-fatal, 1 - error, 2 - warning, 3 - info, 4 - debug-verbose
	*@param [in] mLevel
	*/
	void SetLevel(int val);

protected:

private:
	
};

