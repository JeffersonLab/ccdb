# Python low-level API

The low-level Python API allows you to work with CCDB using Python objects. The code looks like this:

```python
# read a directory
directory = provider.get_directory("/test/test_vars")
print(directory.name)           # name of this directory
print(directory.path)           # full path

for table in directory.type_tables:
    print(table.path)
    print(" ".join([column.name for column in table.columns]))

table = provider.get_type_table("/test/test_vars/test_table2")
# ...
```

The `provider` above is an instance of `AlchemyProvider`:

```python
from ccdb import AlchemyProvider

provider = AlchemyProvider()
provider.connect("sqlite:///path/to/ccdb.sqlite")
provider.authentication.current_user_name = "anonymous"
```

## Connecting

`connect(connection_string, check_version=True)` opens the database: it creates a SQLAlchemy engine
(a connection pool) and a session, and checks that the database has CCDB schema version 5. This is
the right call for scripts and for the CLI, where one provider lives for the whole program.

`attach(engine, session, check_version=True)` uses an engine and a session that you created. Use it
in programs that keep one engine per process and give each thread or request its own session, such
as a web server:

```python
import sqlalchemy
from sqlalchemy.orm import scoped_session, sessionmaker
from ccdb import AlchemyProvider

engine = sqlalchemy.create_engine("mysql+pymysql://ccdb_user@hallddb.jlab.org/ccdb", pool_pre_ping=True)
sessions = scoped_session(sessionmaker(bind=engine))

provider = AlchemyProvider()
provider.attach(engine, sessions)   # checks the schema version once
table = provider.get_type_table("/test/test_vars/test_table")
sessions.remove()                   # you own the session: close or remove it yourself
```

`attach()` validates its arguments:

- `TypeError` when `engine` is not a `sqlalchemy.engine.Engine` or `session` is not a
  `sqlalchemy.orm.Session` or `scoped_session`.
- `ValueError` when the session has no bind or is bound to another engine.
- `RuntimeError` when the provider is connected already; call `disconnect()` first.
- `DatabaseStructureError` when the database has no CCDB schema or another schema version. A failed
  check leaves the provider disconnected.

`disconnect()` marks the provider as disconnected and closes the session. After `attach()` the engine
stays open, because the caller owns it.

## Lookups by database id

`get_directory_by_id(id)` and `get_type_table_by_id(id)` return the object with its full path set.
Like `get_assignment_by_id(id)`, they raise `ObjectIsNotFoundInDbError` when no object has that id.

## Examples

The [python/examples/](https://github.com/JeffersonLab/ccdb/tree/v2-main/python/examples) folder
contains runnable examples:

- Read all kinds of data from CCDB:
  [example_llapi_readout.py](https://github.com/JeffersonLab/ccdb/blob/v2-main/python/examples/example_llapi_readout.py)
- Read constants, change a value, and save them back:
  [example_llapi_change_value.py](https://github.com/JeffersonLab/ccdb/blob/v2-main/python/examples/example_llapi_change_value.py)
- Add custom data:
  [example_llapi_add_custom_data.py](https://github.com/JeffersonLab/ccdb/blob/v2-main/python/examples/example_llapi_add_custom_data.py)
- Manage variations (create, read, update, delete):
  [example_llapi_variations.py](https://github.com/JeffersonLab/ccdb/blob/v2-main/python/examples/example_llapi_variations.py)

More examples (including modification and deletion) can be seen in the unit test fixtures:
[python/tests/provider_fixture.py](https://github.com/JeffersonLab/ccdb/blob/v2-main/python/tests/provider_fixture.py).

## Classes and functions

The data model (where you can see class fields and read comments) is in
[python/ccdb/model.py](https://github.com/JeffersonLab/ccdb/blob/v2-main/python/ccdb/model.py).

The API functions are collected in the provider class:
[python/ccdb/provider.py](https://github.com/JeffersonLab/ccdb/blob/v2-main/python/ccdb/provider.py).
