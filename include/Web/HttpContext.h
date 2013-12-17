#ifndef HttpContext_h__
#define HttpContext_h__


#include <string>
#include <stdlib.h>
#include <map>
#include <new>
using namespace std;
namespace ccdb
{



class HttpContext
{
public:
/** @brief Singleton instance of console context
	 *
	 * @return   DConsoleContext* instance
	 */
	static HttpContext* Instance();
	void ProcessRequest();
	
	void PrintVariables();
	static string UrlDecode(const string& str);

	static void InitializeGet(std::map <std::string, std::string> &values);

	static void InitializePost(std::map <std::string, std::string> &Post);
	
	void OpAjaxDirectoryList();
protected:
private:
	HttpContext();									// Private so that it can  not be called
	HttpContext(HttpContext const&){}				// copy constructor is private
	HttpContext& operator=(HttpContext const&);		// assignment operator is private

	string mHeader; //Header definitions
	void ProcessOperation();//processes request set variables;
	void WriteResponse(const string &content);
	void RenderResponse();
	std::map <std::string, std::string> mGet;
	std::map <std::string, std::string> mPost;
	string mConnectionString;
	static HttpContext* mInstance;					//Main and only singleton instance
};
}
#endif // HttpContext_h__


