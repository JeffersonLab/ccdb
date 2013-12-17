

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


class DatabaseStructureError(Exception):
    """
    Exception raised if No database structure found.
    Possibly because of connecting to wrong SQLite file or to MySQL database without schema.
    """
    pass


