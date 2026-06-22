# Python CLI-like API

Automating the **ccdb** command for scripting purposes is easy with Python — you don't have to call
subprocess. You can use CCDB directly from Python using the `CliManager` class.

> **Note:** earlier versions of CCDB called this class `ConsoleContext`. In CCDB v2 it is
> `CliManager`, located in `ccdb.cmd.cli_manager`.

If you work from a source checkout, add `$CCDB_HOME/python` to your `PYTHONPATH`. It is automatically
adjusted when `environment.bash` is sourced, but you can also add it manually:

```bash
export PYTHONPATH="$CCDB_HOME/python":"$PYTHONPATH"
```

If you installed CCDB with `pip install ccdb`, the package is already importable.

## Usage example

```python
import os

import ccdb.cmd.themes
from ccdb import get_ccdb_home_path
from ccdb.cmd.cli_manager import CliManager, CCDB_EXCEPTIONS_THROW

# Initialization
# =============================

# connection strings:
ccdb_path = get_ccdb_home_path()
sqlite_connection_str = "sqlite:///" + os.path.join(ccdb_path, "sql", "ccdb.sqlite")
mysql_connection_str = "mysql://ccdb_user@127.0.0.1:3306/ccdb"

# create the CLI manager, this is the main class
cli = CliManager()

# make exceptions be raised and propagated instead of just going to the log,
# so you can try/except them
cli.exception_handling = CCDB_EXCEPTIONS_THROW

# disable colored output
cli.theme = ccdb.cmd.themes.NoColorTheme()

# set the connection string
cli.connection_string = sqlite_connection_str

# your username for logging
cli.context.user_name = "python_tests"

# register all commands (ls, rm, mktbl, etc.)
# you can use the manager after calling this function
cli.register_utilities()

# now you can run ccdb commands
cli.process_command_line("mkdir /test/testable2 x y z #Some comment")
# ...
```

There are many examples of how to use `CliManager` in
[python/tests/integ_test_cli_manager.py](https://github.com/JeffersonLab/ccdb/blob/v2-main/python/tests/integ_test_cli_manager.py).
