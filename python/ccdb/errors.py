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


class DataCollisionError(Exception):
    """
    Exception raised when new data has the sha256 of a stored constant set of the same table, but other bytes.

    Two different texts with one SHA-256 means corrupt data or a broken hash, never a real coincidence,
    so nothing is written and a human decides.
    """

    def __init__(self, table_path, sha256, set_ids):
        self.table_path = table_path
        self.sha256 = sha256
        self.set_ids = list(set_ids)
        ids_text = ", ".join(str(set_id) for set_id in self.set_ids)
        message = (f"Data collision in table '{table_path}': constant set(s) {ids_text} have sha256 {sha256} "
                   f"but other bytes than the new data. Nothing was written")
        Exception.__init__(self, message)


class ConstantSetIsImmutableError(Exception):
    """
    Exception raised on an attempt to change the data of a stored constant set.

    A stored set may be shared by several assignments, so changing it in place would change all of them.
    Data changes by adding a new assignment.
    """

    def __init__(self, set_id):
        self.set_id = set_id
        Exception.__init__(self, f"Constant set {set_id} is stored and cannot change")


class SessionHasPendingChangesError(Exception):
    """
    Exception raised when a write method starts while the session holds changes that are not committed.

    The method commits its own work in one transaction; it would commit the caller's changes with it.
    The caller commits or discards them first.
    """

    def __init__(self, message="The session has uncommitted changes. Commit or discard them before this call"):
        Exception.__init__(self, message)
