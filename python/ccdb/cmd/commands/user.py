import logging

from ccdb.cmd.cli_context import CliContext
from ccdb.path_utils import validate_name
from ccdb.cmd import CliCommandBase, UtilityArgumentParser

log = logging.getLogger("ccdb.cmd.commands.user")

# ********************************************************************
#   Class User - Create user                                         *
# ********************************************************************
class User(CliCommandBase):
    """ Create variation """

    # ccdb utility class descr part
    #------------------------------
    command = "user"
    name = "User"
    short_descr = "Manage users"
    uses_db = True

    def execute(self, args):
        log.debug("User module gained control")
        log.debug("Arguments: \n " + "     ".join(args))

        if not len(args):
            # print current user
            print(self.context.provider.authentication.current_user_name)
            return self.context.provider.authentication.current_user_name

        # utility argument parser is argparse which raises errors instead of exiting app
        parser = UtilityArgumentParser()
        parser.add_argument("--create", default="")
        parser.add_argument("--list", default="", action="store_true")
        result = parser.parse_args(args)

        if result.list:
            users = self.context.provider.get_users()
            for user in users:
                print(user.name)
            return users

        if result.create:
            if not validate_name(result.create):
                raise ValueError("Invalid user name. Only [a-z A-Z 0-9 _] symbols are allowed for user name")
            user = self.context.provider.create_user(result.create)
            print("{0} was created.".format(result.create))
            return user

    def print_help(self):
        """prints help to user"""

        print("""
User or user - manages users

usage:

    user --create <name>  - creates a new user with the given username. 
    user --list           - lists all the users in the database. 
    user                  - prints the current user of the database.

    name           - is the username of the new user. [a-z A-Z 0-9 _] are allowed symbols
            """)
