import sys
from ccdb.model import User
from ccdb.provider import AlchemyProvider, hide_password
from ccdb.errors import UserExistsError
import shlex
import sys
import select
import argparse

script_help = """
This utility can add users to ccdb database by user names.
The idea behind this utility is to recreate users list from cronjob.

Usage:
    <comma separated user names> | python users_create.py --recreate mysql://ccdb_user@localhost/ccdb

Flags:
    --recreate - delete all users before create users.
    User deletion doesn't affect logs. The script does not delete system users: "anonymous", "test_user"
    
    --groupid - POSIX Group ID to get users from. E.g. on ifarm halld is 267
    
    --test - Don't do real changes in DB if this flag is given. To be used for scripts and cronjob testing purposes 
    

Examples:
    #recreate user list from halld group
    python3 users_create.py --recreate --groupid=267 mysql://ccdb_user@localhost/ccdb

    python users_create.py mysql://ccdb_user@localhost/ccdb

The scripts fails if no '--recreate' flag is given and a user exists.
    """


def get_provider(con_str):
    """Gets alchemy provider connected with this connection string

    @return AlchemyProvider()"""
    provider = AlchemyProvider()
    provider.logging_enabled = False
    provider.connect(con_str)
    return provider


def delete_users(provider, is_test):
    god_list = ["anonymous", "test_user"]
    assert isinstance(provider, AlchemyProvider)

    users = provider.get_users()
    deleted_count = 0
    for user in users:
        if not user.name in god_list:
            if is_test:
                print(f"Should have deleted: {user.name} (--test flag is given, user won't be deleted) ")
            else:
                provider.delete_user(user.name)
            deleted_count += 1
    print("Users deleted {}".format(deleted_count))


def get_names(groupid):
    import subprocess
    group_count = 0
    output = []

    # Execute the 'getent group' command
    # we do str(int(groupid)) to be sure we are safe of wrong input type
    proc = subprocess.Popen(['getent', 'group', str(int(groupid))], stdout=subprocess.PIPE, text=True)
    output, _ = proc.communicate()

    # The result will be something like halld:*:267:user1,user2,... so we split by ':'
    members_str = output.strip().split(':')[-1].strip()

    print(f"Parsing members list for GroupID={groupid}:")
    print(members_str)

    members = members_str.split(',')
    # Join the output list into a single string and print
    print(f"Total members of GroupID={groupid}: {len(members)}")
    return members


def get_user_names_from_ypmatch(ypstr):
    """
    ypmatch string is like "halld:*:267:marki,davidl,...,jrsteven". This function trim it and returns username as list

    @return: List of strings
    @rtype: [str]
    """

    line = ypstr
    assert isinstance(line,str)
    if ':' in line:
        line = line[line.rfind(':')+1:]

    if '\n' in line:
        line = line.replace('\n', '')

    lexer = shlex.shlex(line)
    lexer.whitespace += '.,'
    return [token for token in lexer]


def create_users(provider, user_names, is_test):
    """

    @param provider:Connected alchemy provider
    @param user_names: list of user names
    """
    count = 0
    for name in user_names:
        try:
            if is_test:
                print(f"Should have created: '{name}' (--test flag is given, user won't be created) ")
            else:
                provider.create_user(name)
            count += 1
        except UserExistsError as err:
            print(err.message)

    print("Users created: {}".format(len(user_names)))


def parse_arguments():
    parser = argparse.ArgumentParser(description="Utility to add users to the ccdb database from cronjobs.", add_help=script_help)
    parser.add_argument('connection_string', type=str, help='Connection string for the database, e.g., mysql://ccdb_user@localhost/ccdb')
    parser.add_argument('--recreate', action='store_true', help='Delete all users before creating new ones')
    parser.add_argument('--groupid', default=267, help='POSIX Group ID to get usernames from')
    parser.add_argument('--test', action='store_true', help="Don't do real changes in DB, allowing testing of this script ")
    args = parser.parse_args()
    return args.connection_string, args.recreate, args.groupid, args.test


def main():
    # Parse command line arguments
    connection_str, recreate, group_id, is_test = parse_arguments()

    # Check stdin for usernames
    names = get_names(group_id)
    if not names:
        print("No user names found. Script continues to delete somebody if --recreate flag is given...")
        exit(1)

    print("Connecting to '" + hide_password(connection_str) + "'")

    provider = get_provider(connection_str)
    provider.get_root_directory()   # this will load directories and ensure that ccdb structure is in place

    # delete old users if needed
    if recreate:
        print("Deleting users ...")
        try:
            delete_users(provider, is_test)
        except Exception as ex:
            print("User deletion failed with error of type {} : {}".format(type(ex), str(ex)))
            sys.exit(2)

    # create new users
    try:
        create_users(provider, names, is_test)
    except Exception as ex:
        print("User creation failed with error of type {} : {}".format(type(ex), str(ex)))
        sys.exit(3)


if __name__ == "__main__":
    main()

