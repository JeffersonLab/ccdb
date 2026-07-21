import unittest

from ccdb.errors import (AuthVerificationError, ObjectIsNotFoundInDbError, DatabaseStructureError,
                         UserNotFoundError, UserExistsError, AnonymousUserForbiddenError)


class PathUtilsTest(unittest.TestCase):

    def test_representations(self):
        msg = str(AuthVerificationError())
        self.assertTrue(msg)
        msg = str(ObjectIsNotFoundInDbError(int, "my-message"))
        self.assertTrue(msg)
        msg = str(DatabaseStructureError())
        self.assertTrue(msg)
        msg = str(UserNotFoundError("User-Name"))
        self.assertTrue(msg)
        msg = str(UserExistsError("", "User-Name"))
        self.assertTrue(msg)
        msg = str(AnonymousUserForbiddenError())
        self.assertTrue(msg)

        # AuthVerificationError()
        # ObjectIsNotFoundInDbError()
        # DatabaseStructureError()
        # UserNotFoundError()
        # UserExistsError(self, message="", username="")
        # AnonymousUserForbiddenError()
        # AllowDefaultsError()
        # MissingArgumentError()
        # MissingVariation()
