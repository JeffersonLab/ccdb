#ifndef DHttpContext_h__
#define DHttpContext_h__


#include <string>
#include <stdlib.h>
#include <map>
#include <new>
using namespace std;
namespace ccdb
{



class DHttpContext
{
public:
/** @brief Singleton instance of console context
	 *
	 * @return   DConsoleContext* instance
	 */
	static DHttpContext* Instance();
	void ProcessRequest();
	
	void PrintVariables();
	static string UrlDecode(const string& str);

	static void InitializeGet(std::map <std::string, std::string> &values);

	static void InitializePost(std::map <std::string, std::string> &Post);
	
	void OpAjaxDirectoryList();
protected:
private:
	DHttpContext();										// Private so that it can  not be called
	DHttpContext(DHttpContext const&){};				// copy constructor is private
	DHttpContext& operator=(DHttpContext const&);		// assignment operator is private
	
	string mHeader; //Header definitions
	void ProcessOperation();//processes request set variables;
	void WriteResponse(const string &content);
	void RenderResponse();
	std::map <std::string, std::string> mGet;
	std::map <std::string, std::string> mPost;
	string mConnectionString;
	static DHttpContext* mInstance;						//Main and only singleton instance
	
};
}
#endif // DHttpContext_h__


