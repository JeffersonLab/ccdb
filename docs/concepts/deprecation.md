# Deprecation

Deprecation marks a directory, a table or a variation as no longer recommended. A deprecated object
is hidden from listings, so new users do not pick it up, and stays readable, so old code and old
requests keep working.

Deprecation removes nothing. CCDB treats the database as a logbook, and deprecation is the way to
retire an object without deleting it.

A deprecated object stores:

- the deprecation flag;
- the user who deprecated it;
- the time of deprecation;
- a comment, required, that says why and what to use instead.

## What deprecation hides

- `ls` without `-a` leaves deprecated directories, tables and variations out.
- `ls -a` shows them, marked as deprecated.
- `ls -a -l` adds the deprecation date and comment. `ls -l` alone leaves deprecated objects out.
- The directory tree of the CLI leaves them out.

## What deprecation never changes

- **Requests.** A request for a deprecated table or variation returns the same constants as before.
- **`cat`, `vers` and `dump`.** They work on deprecated objects unchanged.
- **`info`.** `info` always shows the named object. For a deprecated object it adds a line with the
  comment and the date.
- **The Python provider listings.** `get_directories`, `get_type_tables` and `get_variations` return
  every object by default, deprecated ones included, so existing scripts see no change. To hide
  deprecated objects, pass `include_deprecated=False`.
- **The C++ listing APIs.** They return every object, deprecated ones included.

## Commands

To deprecate a table:

```
$ ccdb deprecate /TOF/params -c "Replaced by /TOF/params_v2"
Table '/TOF/params' deprecated
```

To deprecate a directory or a variation, add `-d` or `-v`:

```
$ ccdb deprecate -d /TOF/old -c "Superseded by /TOF"
Directory '/TOF/old' deprecated
$ ccdb deprecate -v mc_2019 -c "Use mc_2024"
Variation 'mc_2019' deprecated
```

Without a flag, `deprecate` tries the name as a table, then as a directory. `-t` names a table
explicitly.

To undo a deprecation:

```
$ ccdb deprecate --undo /TOF/params
Table '/TOF/params' is no longer deprecated
```

`--undo` clears the flag, the user, the time and the comment. Each deprecation and each undo writes
a log record.

To see deprecated objects:

```
$ ccdb ls -a /TOF
old (deprecated)
params (deprecated)
params_v2
$ ccdb ls -a -l /TOF
old (deprecated) 2026-11-01 18:31:41 Superseded by /TOF
params (deprecated) 2026-11-01 18:31:40 Replaced by /TOF/params_v2
params_v2
$ ccdb info /TOF/params
+------------------------------------------+
| Type table information                   |
+------------------------------------------+
 Name       :  params
 Full path  :  /TOF/params
 Rows       :  2
 Columns    :  1
 Created    :  2026-11-01 18-31-34
 Modified   :  2026-11-01 18-31-40
 DB Id      :  3
 Deprecated :  yes, 2026-11-01 18-31-40: Replaced by /TOF/params_v2
...
```

See [Command line (CLI)](cli.md#deprecation) for the options of `ccdb deprecate`.
