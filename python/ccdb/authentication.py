import os
import getpass

from .errors import AuthVerificationError


#----------------------------------------------------------------------------------------
#
#   A U T H E N T I C A T I O N   P R O V I D E R
#
#----------------------------------------------------------------------------------------
class Authentication(object):
    """
        This is a base class for CCDB authentication.

        It provides:
        1. current_user_name -  property which returns user name
        2. validate_current_user - checks that current user_name corresponds to DB records. Checks database, etc.
        2. getting_username_is_implicit

        **Remark 1:**
        get_current_user_name may involve asking a username or even password, i.e. bugging a user.
        (It is a good idea to cache the username for such provider and not to ask a password further).
        Some other authentication providers may obtain username implicitly without bugging a user.

        If getting_username_is_implicit() returns:
          True  - this means that CCDB may use username without bugging a user. CCDB will use it for information reasons
          False - This means that some additional action user will be required to do when get_current_user_name() is
                  called. In this case CCDB will avoid calling get_current_user_name without a reason.

        **Remark 2:**
        Tips for inheriting the class and implementing get_current_user_name:
        1. If it is impossible to determine user name, 'anonymous' should be returned
        2. If there is something wrong (like database records mismatch) some error should be raised
        3. For systems that using passwords or something that verifies username (certificates?),
           if there is a problem with proving username (wrong password given),  AuthVerificationError should be raised
    """


    #------------------------------------------------------------------------------------
    #   Init
    #------------------------------------------------------------------------------------
    def __init__(self, prov):
        #assert(isinstance(prov, provider.AlchemyProvider))
        self._provider = prov
        self._username = ""

    #------------------------------------------------------------------------------------
    #   getting_username_is_implicit
    #------------------------------------------------------------------------------------
    def getting_username_is_implicit(self):
        """
        Return True if user name is already available.

        Some AuthenticationProvider may have username available all the time,
        other providers may have it available after first use of get_current_username.

         If getting_username_is_implicit() returns:
          True  - this means that CCDB may use username without bugging a user. CCDB will use it for information reasons
          False - This means that some additional action user will be required to do when get_current_user_name() is
                  called. In this case CCDB will avoid calling get_current_user_name without a reason.

        :return: True if user name is already available
        :rtype: basestring
        """
        return True


    #------------------------------------------------------------------------------------
    #   current_user_name
    #------------------------------------------------------------------------------------
    @property
    def current_user_name(self):
        """
        Get the current user name.

        The responsibility of the function:
        1. Obtain user name if self._username was not set explicitly
        2. If it is impossible to determine user name, 'anonymous' should be returned

        :return: verified user name
        :rtype: basestring
        """
        return self._username

    @current_user_name.setter
    def current_user_name(self, username):
        try:
            assert isinstance(username, basestring)
        except NameError:
            assert isinstance(username, str)
        self._username = username


    #------------------------------------------------------------------------------------
    #   validate_current_user
    #------------------------------------------------------------------------------------
    def validate_current_user(self):
        """
        Returns True if user passes current policies of current authentication
        (exists in the database, correct password, certificate, etc...).

        :raises AuthVerificationError: if policies are
        :raise AuthVerificationError: If there is something wrong (like database records mismatch) some error should be raised
        3. For systems that using passwords or something that verifies username (certificates?),
           if there is a problem with proving username (wrong password given),  AuthVerificationError should be raised
        :return:
        """
        return True



#----------------------------------------------------------------------------------------
#
#   E N V I R O N M E N T   A U T H E N T I C A T I O N
#
#----------------------------------------------------------------------------------------
class EnvironmentAuthentication(Authentication, object):
    """
    Authentication provided by CCDB_USER or USER environment variables.
    if current_user_name is externally SET, this name is used regardless to environment variables

    validate_current_user
    """

    #------------------------------------------------------------------------------------
    #   validate_current_user
    #------------------------------------------------------------------------------------
    def __init__(self, prov):
        #assert(isinstance(prov, provider.AlchemyProvider))
        super(EnvironmentAuthentication,self).__init__(prov)
        self._username = ""
        self._env_variable = ""
        self._is_validated = False

    #------------------------------------------------------------------------------------
    #   validate_current_user
    #------------------------------------------------------------------------------------
    @Authentication.current_user_name.getter
    def current_user_name(self):

        #check username is set
        if len(self._username): return self._username

        #now we have to obtain user
        if "CCDB_USER" in os.environ:
            #CCDB username is set explicitly
            self._username = os.environ["CCDB_USER"]
            self._env_variable = "CCDB_USER"
            return self._username

        if "USER" in os.environ:
            self._username = os.environ["USER"]
            self._env_variable = "USER"
            return self._username

        self._username = "anonymous"
        return "anonymous"

    #------------------------------------------------------------------------------------
    #   validate_current_user
    #------------------------------------------------------------------------------------
    def validate_current_user(self):
        #check validation result is cached
        if self._is_validated: return True

        #try to validate
        try:
            self._provider.get_user(self._username)
            self._is_validated = True
            return True
        except Exception:
            message = "User name '{0}' is set by '{1}' environment variable. "\
                      "The user with username doesn't exist in the database. " \
                      "Set user name explicitly by CCDB_USER environment var".format(self._username, self._env_variable)
            raise AuthVerificationError(message)



#----------------------------------------------------------------------------------------
#
#   S H E L L   P A S S W O R D   A U T H E N T I C A T I O N
#
#----------------------------------------------------------------------------------------
class ShellPasswordAuthentication(EnvironmentAuthentication):
    """
        Authentication that uses CCDB_USER or USER to identify username and
    """

    #------------------------------------------------------------------------------------
    #   Init
    #------------------------------------------------------------------------------------
    def __init__(self, prov):
        #assert(isinstance(prov, provider.AlchemyProvider))
        EnvironmentAuthentication.__init__( self, prov )
        self._username = ""


    #------------------------------------------------------------------------------------
    #   validate_current_user
    #------------------------------------------------------------------------------------
    def validate_current_user(self):
        #check validation result is cached
        if self._is_validated: return True

        #try to validate
        try:
            user = self._provider.get_user(self._username)
        except Exception:
            message = "User name '{0}' is set by '{1}' environment variable. "\
                      "The user with username doesn't exist in the database. "\
                      "Set user name explicitly by CCDB_USER environment var.".format(self._username, self._env_variable)
            raise AuthVerificationError(message)

        pw = getpass.getpass()
        if user.password != pw:
            message = "User '{0}' password is incorrect".format(self._username)
            raise AuthVerificationError(message)

        self._is_validated = True
        return True




