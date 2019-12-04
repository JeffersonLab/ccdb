# This file contains a list of specialized exceptions


class AuthVerificationError(Exception):
    """
    Exception raised when wrong pair login,password is obtained by authentication
    """
    pass


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

    pass


class UserNotFoundError(Exception):
    """ Exception raised if user not found in the database"""

    def __init__(self, message="", username=""):
        self.username = username
        Exception.__init__(self, message)


class UserExistsError(Exception):
    def __init__(self, message="", username=""):
        self.message = message,
        self.username = username


class AnonymousUserForbiddenError(Exception):
    """ Exception raised when an Anonymous user is trying to perform actions that they are forbidden from doing."""
    def __init__(self, message="This action is forbidden for an Anonymous user."):
        self.message = message


class AllowDefaultsError(Exception):
    """Exception when allow_defaults is not set to true but other fields are"""
    pass


class MissingArgumentError(Exception):
    """Exception raised if allow_defaults is true and an arguement is missing"""
    pass


class MissingVariation(Exception):
    """Exception raised Variation is not specified"""
    pass

