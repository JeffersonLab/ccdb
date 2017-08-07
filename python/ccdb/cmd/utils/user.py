import logging
from ccdb.path_utils import validate_name
from ccdb.cmd import ConsoleUtilBase, UtilityArgumentParser

log = logging.getLogger("ccdb.cmd.utils.user")

#ccdbcmd module interface
def create_util_instance():
    log.debug("      registering User")
    return User()

#*********************************************************************
#   Class User - Create user                                         *
#                                                                    *
#*********************************************************************
class User(ConsoleUtilBase):
    """ Create variation """

    # ccdb utility class descr part
    #------------------------------
    command = "user"
    name = "User"
    short_descr = "Manage users"
    uses_db = True

    def process(self, args):
        log.debug("User module gained control")
        log.debug("Arguments: \n " + "     ".join(args))

        if not len(args):
            # print current user
            print (self.context.provider.authentication.current_user_name)
            return


        #utility argument parser is argparse which raises errors instead of exiting app
        parser = UtilityArgumentParser()
        parser.add_argument("--create", default="")
        parser.add_argument("--list", default="", action="store_true")
        result = parser.parse_args(args)

        if result.list:
            users = self.context.provider.get_users()
            for user in users:
                print(user.name)
            return

        if result.create:
            if not validate_name(result.create):
                raise ValueError("Invalid user name. Only [a-z A-Z 0-9 _] symbols are allowed for user name")
            self.context.provider.create_user(result.create)
            print("{0} was created.".format(result.create))
            return

    #----------------------------------------------
    #   print_help - prints help
    #----------------------------------------------
    def print_help(self):
        """prints help to user"""

        print """
User or user - manages users

usage:

    user --create <name>  - creates a new user with the given username. 
    user --list           - lists all the users in the database. 
    user                  - prints the current user of the database.

    name           - is the username of the new user. [a-z A-Z 0-9 _] are allowed symbols
            """
