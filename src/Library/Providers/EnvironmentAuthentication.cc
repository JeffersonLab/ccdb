#include "CCDB/Providers/EnvironmentAuthentication.h"
#include <stdlib.h>

using namespace std;


//______________________________________________________________________________
ccdb::EnvironmentAuthentication::EnvironmentAuthentication():
    mUserName(""),
    mIsAuthenticated(false)
{
    Authenticate();
}


//______________________________________________________________________________
ccdb::EnvironmentAuthentication::~EnvironmentAuthentication()
{
    //nothing to do...
}


//______________________________________________________________________________
std::string ccdb::EnvironmentAuthentication::GetLogin()
{
     /** @brief  Gets current user Name
      *
      * @return string user name
      */

    if(!IsAuthenticated()) Authenticate();
    return mUserName;
}


//______________________________________________________________________________
bool ccdb::EnvironmentAuthentication::IsAuthenticated()
{
    /** @brief Check if user is authenticated @return true if is authenticated */

    return mIsAuthenticated;
}


//______________________________________________________________________________
bool ccdb::EnvironmentAuthentication::Authenticate( const std::string& userName, const std::string& password )
{
    /** @brief Tries to Authenticate the user. 
    *
    * @parameter [in] userName - login
    * @parameter [in] password - password
    * @return true if sucsessfully authenticated
    */

    //No authentication is set for this provider
    return Authenticate();
}

//______________________________________________________________________________
bool ccdb::EnvironmentAuthentication::Authenticate()
{
    /** @brief Tries to Authenticate the user. 
    *
    * @parameter [in] userName - login
    * @parameter [in] password - password
    * @return true if sucsessfully authenticated
    */

    //No authentication is set for this provider
    
    //The first priority is CCDB_USER variable
    char * envName;
    envName = getenv (CCDB_ENV_CCDB_USER);
    if (envName!=NULL)
    {
        mUserName.assign(envName);
        return mIsAuthenticated=true;
    }

    //the second priority is "USER" variable
    envName = getenv (CCDB_ENV_USER);
    if (envName!=NULL)
    {
        mUserName.assign(envName);
        return mIsAuthenticated=true;
    }

    //If no such variables is set we use anonymous as a user
    mUserName.assign(CCDB_ANONYMOUS_USERNAME);
    return mIsAuthenticated=false;
}




