import os

class AuthVerificationError(Exception):
    """
    Exception raised when wrong pair login,password is obtained by authentication
    """
    pass


class DirectoryNotFound(Exception):
    """
    Exception raised if directory path is wrong
    """
    pass


class TypeTableNotFound(Exception):
    """
    Exception raised if type table is not found
    """
    pass


class RunRangeNotFound(Exception):
    """
    Exception raised if run range is not found
    """
    pass


class VariationNotFound(Exception):
    """
    Variation is not found in the database
    """
    pass


class DatabaseStructureError(Exception):
    """
    Exception raised if No database structure found.
    Possibly because of connecting to wrong SQLite file or to MySQL database without schema.
    """

    pass

class UserNotFoundError(Exception):
    """ Exception raised if user not found in the database"""

    def __init__(self, message="", username=""):
        self.message = message,
        self.username = username

class UserExistsError(Exception):
    def __init__(self, message="", username=""):
        self.message = message,
        self.username = username

class AnonymousUserForbiddenError(Exception):
    """ Exception raised when an Anonymous user is trying to perform actions that they are forbidden from doing."""
    def __init__(self, message="This action is forbidden for an Anonymous user."):
        self.message = message