#ifndef EnvironmentAuthentication_h__
#define EnvironmentAuthentication_h__

#include <string>

#include "CCDB/Providers/IAuthentication.h"

using namespace std;

namespace ccdb
{

#define CCDB_ENV_CCDB_USER "CCDB_USER"
#define CCDB_ENV_USER "USER"

    /** 
    * This is an interface to user authentication procedure
    * 
    * The idea of the authentication is ot bringing the sequrity reasons
    * but fail proof and logging advanced.
    */
    class EnvironmentAuthentication : public IAuthentication
    {
    public:
        EnvironmentAuthentication();
        ~EnvironmentAuthentication();
        virtual string GetLogin();

        /** @brief  Gets current user Name
         *
         * @return string user name
         */
        //virtual int GetUserName() {return 0;}

        /** @brief Check if user is authenticated
         *
         * @return true if is authenticated
         */
        virtual bool IsAuthenticated();

    protected:

        /** @brief Tries to Authenticate the user. 
         *
         * @parameter [in] userName - login
         * @parameter [in] password - password
         * @return true if sucsessfully authenticated
         */
        virtual bool Authenticate(const std::string& userName, const std::string& password);

        /**
         * Check environment variables to authenticate
         */
        virtual bool Authenticate();

    private:
        std::string mUserName;   /// The user name
        bool mIsAuthenticated;   /// Is user connected?
    };
}

#endif // EnvironmentAuthentication_h__
