#ifndef _DMySQLConnectionInfo_
#define _DMySQLConnectionInfo_
#include <string>

namespace ccdb
{
    ///Internal temporary class to pass connection info to mysql provider
    class MySQLConnectionInfo
    {
        public:
        MySQLConnectionInfo()
            :UserName(""),
            Password(""),
            HostName(""),
            Database(""),
            Port(0)
        {}

        std::string UserName;
        std::string Password;
        std::string Database;
        std::string HostName;
        int Port;
    };
}

#endif // _DMySQLConnectionInfo_
