import os
import sys
import ccdb
import subprocess
from contextlib import contextmanager

# python 3 support
try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO


# path to CCDB_HOME
ccdb_path = ccdb.get_ccdb_home_path()

# path of the tests folder
ccdb_test_path = os.path.join(ccdb_path, 'python', 'tests')

# Name of environment variable that holds MySql connection string
ENV_TEST_MYSQL = "CCDB_TEST_MYSQL_CONNECTION"

# Name of environment variable that holds SQLite connection string
ENV_TEST_SQLITE = "CCDB_TEST_SQLITE_CONNECTION"


# MySql connection string for tests
mysql_test_connection_str = os.environ[ENV_TEST_MYSQL] \
    if ENV_TEST_MYSQL in os.environ \
    else "mysql://ccdb_user@127.0.0.1:3306/ccdb_test"

# SQLite connection string for tests
sqlite_test_connection_str = os.environ[ENV_TEST_SQLITE] \
    if ENV_TEST_SQLITE in os.environ \
    else "sqlite:///" + os.path.join(ccdb_path, "sql", "ccdb.sqlite")


def recreate_mysql_db(username="ccdb_user", password=""):
    """ Erases the test database and put it to default conditions """

    cmdline = ["mysql", "-u", username]
    if password:
        cmdline.extend(["-p", password])

    mysql_source_path = os.path.join(ccdb_path, 'sql', 'ccdb.mysql.sql')
    with open(mysql_source_path, 'r') as content_file:
        mysql_query = content_file.read()

    mysql_query = mysql_query.replace("`ccdb`", "`ccdb_test`")

    p = subprocess.Popen(cmdline, stdin=subprocess.PIPE)
    p.communicate(mysql_query)
    ret_code = p.wait()

    print("MySQL reacreation ended with retcode:", ret_code)


@contextmanager
def captured_output():
    new_out, new_err = StringIO(), StringIO()
    old_out, old_err = sys.stdout, sys.stderr
    try:
        sys.stdout, sys.stderr = new_out, new_err
        yield sys.stdout, sys.stderr
    finally:
        sys.stdout, sys.stderr = old_out, old_err


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--rmysql", help="Recreate test MySql database", action="store_true")
    parser.add_argument('-u', "--user", help="MySql database username", default="ccdb_user")

    args = parser.parse_args()
    if args.rmysql:
        print("Recreate MySQL command. username={}".format(args.user))
        recreate_mysql_db(args.user)
    else:
        print("# path to CCDB_HOME")
        print("ccdb_path = '{}'".format(ccdb_path))
        print("")
        print("# path of the tests folder")
        print("ccdb_test_path = '{}'".format(ccdb_test_path))
        print("")
        print("# Name of environment variable that holds MySql connection string")
        print("ENV_TEST_MYSQL = '{}'".format(ENV_TEST_MYSQL))
        print("")
        print("# Name of environment variable that holds SQLite connection string")
        print("ENV_TEST_SQLITE = '{}'".format(ENV_TEST_SQLITE))
        print("")
        print("# MySql connection string for tests")
        print("mysql_test_connection_str = '{}'".format(mysql_test_connection_str))
        print("")
        print("# SQLite connection string for tests")
        print("sqlite_test_connection_str = '{}'".format(sqlite_test_connection_str))
        parser.print_help()
