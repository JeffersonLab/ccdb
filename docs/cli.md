# Command Line Interface (CLI)

CCDB provides the `ccdb` command line interface for introspection and management of constants. It can
be used as an interactive shell or to execute single commands.

**Example. Single command:**

```
       (1)                           (2)  (3)
ccdb -c "mysql://john@localhost:999" ls /TOF/params
```

1. `-c "mysql://john@localhost"` is the global `ccdb` argument, which sets the
   [connection string](concepts/concepts.md#connection-strings).
2. `ls` is a ccdb command which (like a POSIX `ls`) prints a list of directories and tables belonging
   to `/TOF/params`.
3. `/TOF/params` is an argument of the `ls` command.

**Example. Interactive session:**

```
ccdb -c "mysql://john@localhost:999" -i                  (1)
> ls /TOF/params                                         (2)
> help                                                   (3)
> cd /TOF                                                (4)
> cd params
> ls
> pwd                                                    (5)
> q                                                      (6)
```

1. The flag `-i` starts `ccdb` in interactive mode.
2. `ls /TOF/params` — the result is exactly the same as in the example above.
3. `help` provides a list of commands and how to use each of them.
4. Interactive mode has a current working directory, with relative and absolute paths.
5. As in a POSIX shell, `pwd` shows the current directory.
6. To exit interactive mode enter `q`, `quit`, or press <kbd>Ctrl</kbd>+<kbd>D</kbd>.

Since ccdb objects have `/name/paths` and many other things that look like a POSIX file system, the
commands are very POSIX-shell-like.

## Connecting to DB

The `ccdb` command uses [connection strings](concepts/concepts.md#connection-strings) to connect to a
data source. The connection string can be provided by:

1. The `-c <connection string>` argument (see the example above), or
2. The `CCDB_CONNECTION` environment variable:
   ```bash
   export CCDB_CONNECTION=mysql://ccdb_user@hallddb.jlab.org/ccdb
   ```

If nothing is given by `-c` or `CCDB_CONNECTION`, then `mysql://ccdb_user@localhost/ccdb` is used.

> NOTE: the `-c` flag has higher priority than `CCDB_CONNECTION`.

## Help system

`ccdb` is designed to be self-descriptive. The `help` command lists all commands and how to use them.
For historical reasons `ccdb --help` or `ccdb command --help` will **not** work — use `ccdb help command`:

```bash
ccdb help        # List of existing commands and ccdb help
ccdb help cat    # Help for the `cat` command
ccdb --help      # <= will NOT work
ccdb cat --help  # <= will NOT work as expected
```

## Commands

### Commands consistency

Command arguments are chosen to be consistent between commands. Some flags and argument formats mean
the same thing across all commands. CCDB has several classes of objects: directories, type tables,
variations, run numbers, and assignments. Some commands may be applied to different classes — for
example, `info` may be executed against a directory, table, or variation. There are unified flags to
identify objects for all commands:

- `-v` — Variation
- `-t` — Data table
- `-r` — Run or run-range
- `-d` — Directory
- `-a` — Assignment (usually identified by request or db ID)

**Example. `info` command:**

```
ccdb -i
> info -v default                                          (1)
> info -d /TOF                                             (2)
> info -t /TOF/params                                      (3)
> info /TOF/params                                         (4)
> dump -a 2                                                (5)
```

1. Get information about the "default" variation.
2. Get information about the "/TOF" directory.
3. Get information about the "/TOF/params" type table.
4. By default `info` treats a non-flag argument as the name of a table.
5. Return the content of the table with assignment db ID = 2 (obtained by the `vers` command).

### Commands overview

This table is printed when you execute `ccdb help`:

| (command) | (name)          | (description)                                  |
|-----------|-----------------|------------------------------------------------|
| add       | AddData         | Add data constants                             |
| info      | Info            | Prints extended information about an object     |
| vers      | Versions        | Show versions of data for the specified table  |
| run       | CurrentRun      | Gets or sets current working run               |
| dump      | Dump            | Dumps data table to a file                      |
| show      | Show            | Shows type table data                          |
| mkdir     | MakeDirectory   | Create directory                               |
| pwd       | PrintWorkDir    | Prints working directory                       |
| cd        | ChangeDir       | Change current directory                       |
| mktbl     | MakeTable       | Create constants type table                    |
| cat       | Cat             | Show assignment data by ID                     |
| ls        | List            | List objects in a given directory              |
| log       | Log             | Get CCDB changes log                           |
| db        | DataBase        | Database management commands                    |

Assuming you are in interactive mode, the commands can be categorized:

**Navigate directories**

- `pwd` — prints the current directory
- `cd` — switch to the specified directory
- `ls` — list objects in the directory (wildcards are allowed)
- `mkdir` — creates a directory

```
> pwd
> cd /TOF
> ls
> mkdir constants
> ls con*
```

**Get information about objects**

- `info` — gets information about objects (use `-v -r -d` flags)
- `vers` — gets all versions of the table
- `cat` — displays values
- `dump` — same as `cat` but dumps files to disk
- `log` — see logs information

**Manage objects**

- `mkdir` — creates a directory
- `mktbl` — creates a data table
- `add` — adds data from a text file to a table (variation and run ranges are created automatically)

**Deleting objects**

CCDB discourages deleting anything: treat it as a calibration logbook, where a new assignment
supersedes the old one and the old one stays.

There are still cases when removing something might be required:

- It is possible to make a typo/mistake when creating a table/variation.
- At an early development stage it might be beneficial to recreate something (e.g. a table with a
  different set of rows).
- For all other cases deletion is highly **not** recommended. Treat CCDB as a logbook — a calibration
  data logbook. Removing things is still technically possible.

The `rm` command should be used with the common flags `-d`, `-t`, `-v`, `-a` to remove a directory,
table, variation, or assignment.

> A directory/table/variation must be empty to be removed. This means you have to first delete all
> assignments from a table to remove the table, remove all tables to remove a directory, etc.

Assignments of one table with the same data share one constant set. `rm -a` deletes the set together
with the last assignment that uses it, and removing a table removes its unused sets; see
[Constant sets and their hashes](concepts/constant-sets.md#deleting-assignments-and-tables).

### Versions of a table

`vers` lists the assignments of a table, newest first. `vers -l` adds `(data)`, the first 12 hex digits
of the SHA-256 of the assignment's data, and `(shared)`, the number of assignments that use the same
constant set:

```
$ ccdb vers -l /test/test_vars/test_table
(ID)     (created)              (user)           (variation)     (run range)      (data)        (shared)  (comments)
 6       2026-11-01 14-44-26    test_user        default         100-200         55d35b501c1a  2         Same values as assig
 5       2012-10-30 23-48-43    test_user        subtest         0-inf           b2ceb52d6aa9  1         Test assignment for
 4       2012-10-30 23-48-42    test_user        default         0-inf           55d35b501c1a  2         Test assignment for
 2       2012-08-30 23-48-42    test_user        test            500-3000        9c6697ea9cda  1         Test assignment for
 1       2012-07-30 23-48-42    test_user        default         0-inf           b62adcd1b563  1         Test assignment for
```

Assignments 4 and 6 hold the same data. [Constant sets and their hashes](concepts/constant-sets.md)
explains when data is shared.

### Database management

`ccdb db` without a subcommand prints the connection and the schema version:

```
$ ccdb db
Connection to: sqlite:///ccdb.sqlite
Schema version: 6
```

| subcommand | what it does | flags |
|---|---|---|
| `db init` | drops every CCDB table and creates the schema with its standard content; all data is lost | `--init-i-am-sure` |
| `db stats` | counts assignments, constant sets and the sets shared by several assignments | |
| `db upgrade` | upgrades the database from schema version 5 to 6 | `--dry-run`, `--duplicates none\|sample\|all`, `--upgrade-i-am-sure`, `--skip-privilege-check`, `--no-transaction-check`, `--in-place` |
| `db dedup` | reports byte-identical and unused constant sets; with its flag merges and removes them and creates the unique index | `--table PATH`, `--dedup-i-am-sure`, `--no-transaction-check` |
| `db rehash` | recomputes the SHA-256 and size of every constant set and compares them with the stored values | `--sample N`, `--server`, `--rehash-i-am-sure` |
| `db rollback-v6` | returns the database from schema version 6 to 5, for CCDB 2.4 | `--rollback-i-am-sure`, `--drop-v6-data`, `--allow-non-strict`, `--in-place`, `--skip-privilege-check`, `--no-transaction-check` |

```
$ ccdb db stats
Num assignments: 6
Num constant sets: 5
Num shared constant sets: 1
```

A subcommand that changes data acts only with its own flag, `--<verb>-i-am-sure`. Without it, `init`,
`upgrade` and `rollback-v6` print a warning, change nothing and exit with 1; `dedup` prints its report and
`rehash` verifies. `db upgrade --dry-run` writes nothing. The commands exit with 1 on a refusal, a
collision or a hash mismatch. [Upgrading to CCDB 2.5](deployment/upgrade-2.5.md) describes every flag
and its output.

