# This file contains a list of specialized exceptions


class AuthVerificationError(Exception):
    """
    Exception raised when wrong pair login,password is obtained by authentication
    """
    def __init__(self, message="Wrong login and password (if passwords are used) are obtained by authentication"):
        Exception.__init__(self, message)


class ObjectIsNotFoundInDbError(Exception):

    def __init__(self, db_obj_type, message="", **kwargs):
        self.__dict__.update(kwargs)
        self.db_obj_type = db_obj_type
        Exception.__init__(self, message)



class DatabaseStructureError(Exception):
    """
    Exception raised if No database structure found.
    Possibly because of connecting to wrong SQLite file or to MySQL database without schema.
    """

    def __init__(self, message=""):
        if not message:
            message = ("No database structure found. "
                       "Possibly because of connecting to wrong SQLite file or to MySQL database without schema")
        Exception.__init__(self, message)


class UserNotFoundError(Exception):
    """ Exception raised if user not found in the database"""

    def __init__(self, message="", username=""):
        self.username = username
        if not message:
            message = f"Username '{username}' is not found"
        Exception.__init__(self, message)


class UserExistsError(Exception):
    def __init__(self, message="", username=""):
        self.message = message,
        self.username = username
        if not message:
            message = f"Username '{username}' already exists"
        Exception.__init__(self, message, username)


class AnonymousUserForbiddenError(Exception):
    """ Exception raised when an Anonymous user is trying to perform actions that they are forbidden from doing."""

    def __init__(self, message="This action is forbidden for an Anonymous user."):
        Exception.__init__(self, message)

