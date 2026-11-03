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
| dump      | Dump            | Dumps data table                               |
| show      | Show            | Shows type table data                          |
| mkdir     | MakeDirectory   | Create directory                               |
| pwd       | PrintWorkDir    | Prints working directory                       |
| cd        | ChangeDir       | Change current directory                       |
| mktbl     | MakeTable       | Create constants type table                    |
| cat       | Cat             | Show assignment data by ID                     |
| ls        | List            | List objects in a given directory              |
| log       | ShowLog         | Shows log records                              |
| db        | Database        | Database information and management            |
| deprecate | Deprecate       | Marks a table, a directory or a variation as deprecated |
| tag       | Tag             | Creates, lists, shows or removes snapshot tags |
| prop      | Prop            | Sets, gets and lists properties of the instance, tables, directories and variations |

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
- `log [N] [SKIP] [TABLE]` — the newest N log records (20 by default, 0 for all), skipping SKIP; a table path
  or pattern, `-v VARIATION` or `-u USER` narrow them. Every command that changes the database writes a record,
  on SQLite files as on MySQL and MariaDB (before 2.5.0 the command line kept no log on `sqlite://` connections)
- `tag` — lists and shows tags
- `prop get`, `prop ls` — read properties

**Manage objects**

- `mkdir` — creates a directory
- `mktbl` — creates a data table
- `add` — adds data from a text file to a table (variation and run ranges are created automatically)
- `deprecate` — hides a directory, table or variation from listings
- `edit -a ID --comment "text"` — replaces the comment of a version; the log keeps the previous one
- `tag` — creates and removes tags
- `prop set` — sets a property

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

`rm -a` refuses to delete an assignment that a tag pins, unless you add `--force`; see
[Tags](concepts/tags.md#no-deletion-of-tagged-history). To retire an object without deleting it, use
[`deprecate`](#deprecation).

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

### Deprecation

To hide a directory, a table or a variation from listings without deleting it, use `deprecate`:

```
ccdb deprecate [-t|-d|-v] NAME -c COMMENT
ccdb deprecate --undo [-t|-d|-v] NAME
```

| flag | meaning |
|---|---|
| `-t` | NAME is a table |
| `-d` | NAME is a directory |
| `-v` | NAME is a variation |
| `-c COMMENT` | why the object is deprecated and what to use instead; required |
| `--undo` | clears the deprecation |

Without `-t`, `-d` or `-v`, NAME is tried as a table, then as a directory.

```
$ ccdb deprecate /TOF/params -c "Replaced by /TOF/params_v2"
Table '/TOF/params' deprecated
$ ccdb deprecate -d /TOF/old -c "Superseded by /TOF"
Directory '/TOF/old' deprecated
$ ccdb deprecate -v mc_2019 -c "Use mc_2024"
Variation 'mc_2019' deprecated
$ ccdb ls -a -l /TOF
old (deprecated) 2026-11-01 18:31:41 Superseded by /TOF
params (deprecated) 2026-11-01 18:31:40 Replaced by /TOF/params_v2
params_v2
$ ccdb deprecate --undo /TOF/params
Table '/TOF/params' is no longer deprecated
```

Deprecated objects:

- are hidden from `ls` and `ls -l`; `ls -a` shows them marked, and `ls -a -l` adds the date and the
  comment;
- appear in `info` with a `Deprecated` line that holds the date and the comment;
- stay unchanged for requests, `cat`, `vers` and `dump`.

Each deprecation and each undo writes a log record. [Deprecation](concepts/deprecation.md) describes
what is hidden and what is not.

### Tags

A tag names a snapshot of one variation at one moment; see [Tags](concepts/tags.md).

```
ccdb tag NAME [-v VARIATION] [-t TIME] -c COMMENT     # create
ccdb tag                                              # list
ccdb tag NAME                                         # show
ccdb tag rm NAME                                      # remove
```

| flag | meaning |
|---|---|
| `-v VARIATION` | the variation the tag freezes; `default` if omitted |
| `-t TIME` | the moment the tag freezes, in local time and the request time format; the current time if omitted; a future time is refused |
| `-c COMMENT` | what the tag is for; required to create a tag |

A tag name consists of `A-Z`, `a-z`, `0-9` and `_`, at most 100 characters.

```
$ ccdb tag Run2026 -c "Calibration of the 2026 production"
Tag 'Run2026' is created
$ ccdb tag mc_2025_10 -v mc -t 2025:10:31-23:59:59 -c "MC constants as of October 2025"
Tag 'mc_2025_10' is created
$ ccdb tag
(name)                (variation)      (time UTC)            (comment)
 Run2026               default          2026-11-01 23:35:54   Calibration of the 2026 production
 mc_2025_10            mc               2025-11-01 03:59:59   MC constants as of October 2025
$ ccdb tag Run2026
...
$ ccdb tag rm Run2026
Tag 'Run2026' is removed
```

The tag stores the time as a UTC instant. `ccdb tag rm` writes a log record and leaves the constants
in place. `rm -a` refuses to delete an assignment that a tag may resolve to; `rm -a ID -f` skips the
prompt and deletes it anyway.

### Tags in requests

The [request](concepts/concepts.md#requests) part `@NAME` reads constants through a tag:

```
</path/to/data>[:<run>]@<tag>
```

The request uses the tag's variation and sees only assignments created at or before the tag's time.
The run is optional, as in any request.

```
$ ccdb cat /test/test_vars/test_table:1500@Run2026
$ ccdb dump /test/test_vars/test_table:1500@Run2026 > test_table.txt
```

`cat`, `dump`, `vers` and `info` accept a request with a tag. A tag already sets the variation and the
time, so a request with a tag and a variation (`/path:1500:mc@Run2026`) or a tag and a time
(`/path:1500::2026@Run2026`) is an error:

```
$ ccdb cat /test/test_vars/test_table:1500:mc@Run2026
A request with a tag can have neither a variation nor a time: '/test/test_vars/test_table:1500:mc@Run2026'
```

### Properties

Properties are name and value pairs that describe the CCDB instance or an object in it: a contact, a
description, a license.

```
ccdb prop set [--instance | [-t|-d|-v] NAME] KEY VALUE
ccdb prop get [--instance | [-t|-d|-v] NAME] KEY
ccdb prop ls  [--instance | [-t|-d|-v] NAME]
ccdb prop rm  [--instance | [-t|-d|-v] NAME] KEY
```

| flag | meaning |
|---|---|
| `--instance` | the property belongs to the CCDB instance |
| `-t` | NAME is a table; the default |
| `-d` | NAME is a directory |
| `-v` | NAME is a variation |

Standard names:

| owner | names |
|---|---|
| instance | `experiment`, `description`, `license`, `citation`, `contact`, `url` |
| directory, table, variation | `description`, `contact`, `keywords`, `source_url`, `doc_url`, `license`, `citation` |

Any other name is allowed. One owner holds one value per name; `prop set` on an existing name
replaces the value.

```
$ ccdb prop set --instance experiment GlueX
Property 'experiment' of the instance is set
$ ccdb prop set /TOF/params_v2 contact "tof-calib@example.org"
Property 'contact' of table '/TOF/params_v2' is set
$ ccdb prop get /TOF/params_v2 contact
tof-calib@example.org
$ ccdb prop ls /TOF/params_v2
contact = tof-calib@example.org
description = TOF timing offsets per paddle
$ ccdb prop rm /TOF/params_v2 contact
Deleted property 'contact' of table '/TOF/params_v2'
```

Each change writes a log record. `info` lists the properties of the object at the end of its output:

```
$ ccdb info /TOF/params_v2
...
Properties: 
 contact     :  tof-calib@example.org
 description :  TOF timing offsets per paddle
```

### Column units

To give a column units, add them after the type in `mktbl`:

```
name=type:units
```

```
$ ccdb mktbl /calib/gains -r 2 channel=int gain=double:MeV offset=double:ns time=:ns "#Gains per channel"
```

The units part is optional, and `name=type` stays valid. An empty type keeps the default `double`:
`time=:ns` is a `double` column in `ns`. `info` shows the units in brackets:

```
$ ccdb info /calib/gains
...
Columns info 
 N.   (type)    : (name) [units]
 0    int       : channel
 1    double    : gain [MeV]
 2    double    : offset [ns]
 3    double    : time [ns]
```

`dump` writes a `#meta units:` line after the comment lines when a table has units:

```
$ ccdb dump /calib/gains:100
#
#meta units: gain=MeV offset=ns time=ns
  1            1.5          0.1          3
  2            1.6          0.2          4
```

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

