#ifndef _DMySQLConnectionInfo_
#define _DMySQLConnectionInfo_
#include <string>

using namespace std;

namespace ccdb
{
	///Internal temporary class to pass connection info to mysql provider
class DMySQLConnectionInfo
{
	public:
	DMySQLConnectionInfo()
	:UserName(""),
	Password(""),
	HostName(""),
	Database(""),
	Port(0)
	{
	}
	~DMySQLConnectionInfo(){};
	string	UserName;
	string	Password;
	string 	Database;
	string	HostName;
	int		Port;
	
};

}

#endif // _DMySQLConnectionInfo_
