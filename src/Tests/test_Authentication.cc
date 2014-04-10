
#pragma warning(disable:4800)

#include "Tests/catch.hpp"

#include "CCDB/Providers/IAuthentication.h"
#include "CCDB/Providers/EnvironmentAuthentication.h"

#include <stdlib.h>

using namespace std;
using namespace ccdb;

TEST_CASE("CCDB/Providers/Authentication","Authentications tests")
{

    IAuthentication * auth = NULL;
    REQUIRE_NOTHROW(auth = new EnvironmentAuthentication());
    REQUIRE(auth->GetLogin() != "");
}
