# Python API

The CCDB CLI is written in Python, so there are at least two ways to interact with CCDB from Python:

1. Using the **CLI-like API**, which resembles using the `ccdb` command.
2. Using the so-called **low-level API**.

> Install the library with `pip install ccdb` (see [Installation](../get-started/installation.md)), or
> add `$CCDB_HOME/python` to your `PYTHONPATH` when working from a source checkout.

## CLI-like API

The code looks like this:

```python
cli.process_command_line("mkdir /test/testable2 x y z #Some comment")
```

This is the Python API that is actually under the hood of the `ccdb` command.

Why use it? — If you ever wanted to create ccdb CLI commands programmatically and run them using
*subprocess*, you can skip subprocess and use this API directly.

**Pros:**

- Almost the same as the ccdb CLI, but you get exceptions directly and you don't have to use
  subprocess.
- The documentation for the ccdb CLI is valid for this API.
- It is as safe in terms of DB integrity as the ccdb CLI.

**Cons:**

- You don't get results as Python objects (so, for example, you can't read table names and iterate
  over them).

See [CLI-like API](python-cli-like.md) for a full example.

## Low-level API

The code looks like this:

```python
tables = provider.get_type_tables("/test/test_vars")
for table in tables:
    print(table.name)
```

It is called "low-level" to highlight that it becomes possible to break DB integrity using this API.
Still, if you only read data, you can't break anything; and if you follow the examples for writing to
the DB, it is relatively safe too.

Why use it? — You work directly with Python objects that represent the CCDB structure. You can iterate
over them, go from one to another through the hierarchy, etc. You can also add custom data, massively
change or delete data, and so on.

**Pros:**

- Full access to CCDB data through Python.
- Working with Python objects.
- SQLAlchemy queries to the DB are possible.

**Cons:**

- One can break the data layout, especially with delete operations (so please follow the instructions
  and examples, and make backups!).
- More complex.

See [low-level API](python-low-level.md) for examples.

## Where things live

The data class model, where you can find classes for tables or directories, is in
[python/ccdb/model.py](https://github.com/JeffersonLab/ccdb/blob/v2-main/python/ccdb/model.py).

The core API functions are in
[python/ccdb/provider.py](https://github.com/JeffersonLab/ccdb/blob/v2-main/python/ccdb/provider.py).

More examples of using the API are in
[python/tests/provider_fixture.py](https://github.com/JeffersonLab/ccdb/blob/v2-main/python/tests/provider_fixture.py)
and the [python/examples/](https://github.com/JeffersonLab/ccdb/tree/v2-main/python/examples) folder.

Read next: [CLI-like API](python-cli-like.md) | [Low-level API](python-low-level.md)
