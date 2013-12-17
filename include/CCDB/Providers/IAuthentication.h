#ifndef IAuthentication_h__
#define IAuthentication_h__


#include <string>

using namespace std;

namespace ccdb
{
#define CCDB_ANONYMOUS_USERNAME "Anonymous"

    /** 
    * This is an interface to user authentication procedure
    * 
    * The idea of the authentication is ot bringing the sequrity reasons
    * but fail proof and logging advanced.
    */
    class IAuthentication
    {
    public:
        IAuthentication(){}
        virtual ~IAuthentication(){}
        virtual string GetLogin()=0;

        /** @brief  Gets current user Name
         *
         * @return string user name
         */
       // virtual int GetUserName()=0;

        /** @brief Check if user is authenticated
         *
         * @return true if is authenticated
         */
        virtual bool IsAuthenticated()=0;

    protected:

        /** @brief Tries to Authenticate the user. 
         *
         * @parameter [in] userName - login
         * @parameter [in] password - password
         * @return true if sucsessfully authenticated
         */
        virtual bool Authenticate(const std::string& userName, const std::string& password)=0;
    };

}
#endif // IAuthentication_h__
