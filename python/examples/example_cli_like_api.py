"""
Running ccdb commands from Python with CliManager, the class behind the `ccdb` command (docs/apis/python-cli-like.md)

    CCDB_CONNECTION=sqlite:////full/path/to/ccdb.sqlite python example_cli_like_api.py

Create a demo database first:  ccdb -c sqlite:////full/path/to/ccdb.sqlite db init --init-i-am-sure
"""
import contextlib
import io
import os
import tempfile

import ccdb.cmd.themes
from ccdb.cmd.cli_manager import CliManager, CCDB_EXCEPTIONS_THROW

# The manager, set up once
cli = CliManager()
cli.exception_handling = CCDB_EXCEPTIONS_THROW         # raise errors instead of only logging them
cli.theme = ccdb.cmd.themes.NoColorTheme()              # plain text, no terminal colors
cli.connection_string = os.environ["CCDB_CONNECTION"]
cli.context.user_name = "test_user"                     # the author of every change, as CCDB_USER
cli.register_utilities()                                # ls, mkdir, mktbl, add, cat, ...


def ccdb_command(command_line):
    """Runs one ccdb command and returns what it printed"""
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        cli.process_command_line(command_line)
    return output.getvalue()


# Commands as on the command line
ccdb_command("mkdir /cli_example #Tables of the CLI-like API example")
ccdb_command("mktbl /cli_example/gains -r 2 element=string gain=double #Gain per module")

with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as data_file:
    data_file.write("module_1 1.10\nmodule_2 1.20\n")
ccdb_command("add /cli_example/gains -r 0- {0} #First calibration".format(data_file.name))
os.remove(data_file.name)

# What a command prints is a string to parse or show
print(ccdb_command("vers /cli_example/gains"))
rows = [line.split() for line in ccdb_command("dump /cli_example/gains:100").splitlines()
        if line.strip() and not line.startswith("#")]       # dump starts with the version's comment line
print(rows)                                             # [['module_1', '1.10'], ['module_2', '1.20']]

# An error is an exception
try:
    ccdb_command("cat /cli_example/no_such_table")
except Exception as error:
    print("as expected:", type(error).__name__)

# Clean up, so the example runs again on the same database: versions, then the table, then the directory
for line in ccdb_command("vers /cli_example/gains").splitlines()[1:]:
    if line.strip():
        ccdb_command("rm -f -a " + line.split()[0])
ccdb_command("rm -f /cli_example/gains")
ccdb_command("rm -f -d /cli_example")
