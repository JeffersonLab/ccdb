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
