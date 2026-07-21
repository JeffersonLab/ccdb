# There are a number of tools and configs for unit testing which is convenient to have in ccdb package.
# The unit tests and integration tests are located outside of the package

import inspect
import os
import sys
import ccdb
from contextlib import contextmanager
from io import StringIO

from ccdb import CCDB_EXCEPTIONS_THROW
from ccdb.cmd import CliManager

# path to CCDB_HOME
ccdb_path = ccdb.get_ccdb_home_path()

# path of the tests folder
ccdb_test_path = os.path.join(ccdb_path, 'python', 'tests')

# Name of environment variable that holds MySql and SQLite connection strings
ENV_TEST_MYSQL = "CCDB_TEST_MYSQL_CONNECTION"
ENV_TEST_SQLITE = "CCDB_TEST_SQLITE_CONNECTION"

# MySql connection string for tests
if ENV_TEST_MYSQL in os.environ:
    mysql_test_connection_str = os.environ[ENV_TEST_MYSQL]
else:
    if os.name == 'nt':
        mysql_test_connection_str = "mysql://ccdb_user@127.0.0.1:3306/ccdb_test"
    else:
        mysql_test_connection_str = "mysql://ccdb_user@localhost/ccdb_test"


# Default SQLite test database file (created fresh by recreate_test_sqlite_db)
sqlite_test_file_path = os.path.join(os.getcwd(), 'test.sqlite')

# SQLite connection string for tests. Never points at a committed file:
# tests create their own database via recreate_test_sqlite_db()
if ENV_TEST_SQLITE in os.environ:
    sqlite_test_connection_str = os.environ[ENV_TEST_SQLITE]
else:
    sqlite_test_connection_str = "sqlite:///" + sqlite_test_file_path


def recreate_mysql_db(connection_str):
    """ Erases the test database and put it to default conditions """

    # create console context
    cli = CliManager()
    cli.exception_handling = CCDB_EXCEPTIONS_THROW
    cli.force_exceptions = True
    cli.theme = ccdb.cmd.themes.NoColorTheme()
    cli.connection_string = connection_str
    cli.context.user_name = "test_user"
    cli.register_utilities()
    cli.process_command_line("db init --init-i-am-sure")


def recreate_mysql_db2(connection_string):
    from sqlalchemy import create_engine, text

    # Create an engine that connects to the MySQL server
    engine = create_engine(connection_string)

    # Path to the file containing SQL queries
    sql_file_path = os.path.join(ccdb_path, 'sql', 'ccdb.mysql.sql')

    # Function to determine if a line is a valid SQL command
    def is_executable_line(line):
        line = line.strip()
        if line.startswith('SET') and 'FOREIGN_KEY_CHECKS' in line:
            return False  # Skip setting FOREIGN_KEY_CHECKS
        return not (line.startswith('--') or line.startswith('/*') or line == '')

    # Read the SQL file and execute each statement
    try:
        with engine.begin() as conn:
            with open(sql_file_path, 'r') as file:
                # Split the script into separate statements on semicolons
                sql_statements = file.read().split(';')
                for statement in sql_statements:
                    # Skip any empty or whitespace-only statements
                    if statement.strip():

                        print("----------")
                        final_sql_query = statement.strip().replace("`ccdb`", "`ccdb_test`")
                        print(final_sql_query)
                        print("----------")
                        conn.execute(text(final_sql_query))
    except Exception as e:
        print(f"An error occurred: {e}")


def get_script_path(func, follow_symlinks=True):
    path = inspect.getabsfile(func)
    if follow_symlinks:
        path = os.path.realpath(path)
    return path


def recreate_test_sqlite_db():
    """Creates a fresh SQLite test database (schema v5 + standard test data)

    Uses sqlite_test_connection_str, so CCDB_TEST_SQLITE_CONNECTION env var
    can redirect where the database is created. Any existing data is erased.
    """
    from sqlalchemy import create_engine
    from ccdb.sql.sqlite_schema import init_sqlite_database

    engine = create_engine(sqlite_test_connection_str)
    init_sqlite_database(engine)
    engine.dispose()


def clean_test_sqlite_db():
    if os.path.exists(sqlite_test_file_path):
        os.remove(sqlite_test_file_path)


# In  sqlite DB connection string


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
        print("Recreate MySQL command. connection_string={}".format(mysql_test_connection_str))
        recreate_mysql_db2(mysql_test_connection_str)
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
