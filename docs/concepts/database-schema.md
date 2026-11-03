# Database schema

This page documents the tables of CCDB database schema version 6, the schema of CCDB 2.5. See
[Conceptual design](concepts/conceptual-design.md) for the reasoning behind the schema and
[Concepts illustrated](concepts/concepts.md) for how these tables map to namepaths, table types,
constant sets and assignments. [Upgrading to CCDB 2.5](deployment/upgrade-2.5.md) describes the move
from schema version 5.

## Where the schema is defined

The Python package defines the schema, and `ccdb db init` creates it from there:

- [python/ccdb/sql/mysql_schema.py](https://github.com/JeffersonLab/ccdb/blob/v2-main/python/ccdb/sql/mysql_schema.py)
  for MySQL and MariaDB;
- [python/ccdb/sql/sqlite_schema.py](https://github.com/JeffersonLab/ccdb/blob/v2-main/python/ccdb/sql/sqlite_schema.py)
  for SQLite;
- [python/ccdb/sql/update_v6.py](https://github.com/JeffersonLab/ccdb/blob/v2-main/python/ccdb/sql/update_v6.py)
  for the upgrade from schema version 5.

The SQL file `sql/ccdb.mysql.sql` is generated from `mysql_schema.py`. To regenerate it after a change,
run from the repository root, with the `ccdb` package installed:

```bash
python -m ccdb.sql.mysql_schema sql/ccdb.mysql.sql
```

The MySQL Workbench model `sql/ccdb_eer_diagram.mwb` is kept as it was; it does not show schema 6.

## Engines and character sets

On MySQL and MariaDB every table is InnoDB with the default collation `utf8mb4_general_ci`, and every
character column names its character set and collation. `utf8mb4_general_ci` ignores case and
trailing spaces in comparisons, so name lookups behave as they did on latin1. `constantSets.sha256` is
`ascii` with the case-sensitive `ascii_bin`. CCDB declares no foreign key constraints. On SQLite text
is always Unicode.

The listings below are `DESCRIBE` output of a database created by `ccdb db init` on MariaDB 10.5.
MySQL 8 prints `int` and `int unsigned` where MariaDB prints `int(11)` and `int(10) unsigned`, and
`CURRENT_TIMESTAMP` with `DEFAULT_GENERATED` in `Extra` where MariaDB prints `current_timestamp()`.

## Reserved objects

Schema 6 holds tables and columns that no command of this version reads or writes yet; the listings
mark them **reserved**:

- `tags` in its new shape: named snapshots of a variation at a time;
- `properties`: instance and object metadata;
- `columns.units`: the units of a column;
- `deprecatedTime` and `deprecationComment` on `directories`, `typeTables` and `variations`, with the
  older `isDeprecated` and `deprecatedByUserId`: deprecation of tables, directories and variations;
- `timeRanges` and `assignments.timeRangeId`: validity by time.

## assignments

An assignment gives one constant set to a table for a run range, in a variation, at a creation time:
`created`, a UTC instant with microseconds ([Time](concepts/time.md)).

```
+---------------+------------------+------+-----+---------------------+----------------+
| Field         | Type             | Null | Key | Default             | Extra          |
+---------------+------------------+------+-----+---------------------+----------------+
| id            | int(10) unsigned | NO   | PRI | NULL                | auto_increment |
| created       | timestamp(6)     | NO   | MUL | current_timestamp(6) |               |
| modified      | timestamp        | NO   |     | 2007-01-01 00:00:00 |                |
| variationId   | int(11)          | NO   | MUL | NULL                |                |
| runRangeId    | int(11)          | YES  | MUL | NULL                |                |
| eventRangeId  | int(11)          | YES  | MUL | NULL                |                |
| authorId      | int(11)          | NO   |     | 1                   |                |
| comment       | text             | YES  |     | NULL                |                |
| constantSetId | int(11)          | NO   | MUL | NULL                |                |
| timeRangeId   | int(11)          | YES  | MUL | NULL                |                |
+---------------+------------------+------+-----+---------------------+----------------+
```

- `constantSetId`: the set of this assignment. From schema 6 on, several assignments of one table can
  point at one set; see [Constant sets and their hashes](concepts/constant-sets.md).
- `timeRangeId`: **reserved** for validity by time; always NULL in CCDB 2.5.

## columns

The columns of each table: name, type, order.

```
+------------+------------------------------------------------------------+------+-----+---------------------+----------------+
| Field      | Type                                                       | Null | Key | Default             | Extra          |
+------------+------------------------------------------------------------+------+-----+---------------------+----------------+
| id         | int(11)                                                    | NO   | PRI | NULL                | auto_increment |
| created    | timestamp                                                  | NO   |     | current_timestamp() |                |
| modified   | timestamp                                                  | NO   |     | 2007-01-01 00:00:00 |                |
| name       | varchar(45)                                                | NO   |     | NULL                |                |
| typeId     | int(11)                                                    | NO   | MUL | NULL                |                |
| columnType | enum('int','uint','long','ulong','double','string','bool') | YES  |     | NULL                |                |
| order      | int(11)                                                    | NO   |     | NULL                |                |
| comment    | text                                                       | YES  |     | NULL                |                |
| units      | varchar(64)                                                | YES  |     | NULL                |                |
+------------+------------------------------------------------------------+------+-----+---------------------+----------------+
```

- `units`: **reserved**, the units of the column, free text, up to 64 characters.

## constantSets

The data. `vault` holds the values of all rows, separated by `|`.

```
+----------------+------------------+------+-----+---------------------+----------------+
| Field          | Type             | Null | Key | Default             | Extra          |
+----------------+------------------+------+-----+---------------------+----------------+
| id             | int(11)          | NO   | PRI | NULL                | auto_increment |
| created        | timestamp        | NO   |     | current_timestamp() |                |
| modified       | timestamp        | NO   |     | 2007-01-01 00:00:00 |                |
| vault          | longtext         | NO   |     | NULL                |                |
| constantTypeId | int(11)          | NO   | MUL | NULL                |                |
| sha256         | char(64)         | NO   |     | NULL                |                |
| size           | int(10) unsigned | NO   |     | NULL                |                |
+----------------+------------------+------+-----+---------------------+----------------+
```

- `sha256`: the SHA-256 of `vault` encoded as UTF-8, 64 lower-case hex digits.
- `size`: the number of bytes of `vault` encoded as UTF-8.
- Unique index `uq_constantSets_table_sha256` on `(constantTypeId, sha256)`: one set per table and
  data. A database upgraded from schema 5 has the non-unique `ix_constantSets_table_sha256` on the same
  columns until `ccdb db dedup --dedup-i-am-sure` has merged its duplicates.

## directories

The directory tree of tables.

```
+--------------------+--------------+------+-----+---------------------+----------------+
| Field              | Type         | Null | Key | Default             | Extra          |
+--------------------+--------------+------+-----+---------------------+----------------+
| id                 | int(11)      | NO   | PRI | NULL                | auto_increment |
| created            | timestamp    | NO   |     | current_timestamp() |                |
| modified           | timestamp    | NO   |     | 2007-01-01 00:00:00 |                |
| name               | varchar(255) | NO   |     |                     |                |
| parentId           | int(11)      | NO   | MUL | 0                   |                |
| authorId           | int(11)      | NO   |     | 1                   |                |
| comment            | text         | YES  |     | NULL                |                |
| isDeprecated       | tinyint(1)   | NO   |     | 0                   |                |
| deprecatedByUserId | int(11)      | YES  |     | NULL                |                |
| isLocked           | tinyint(1)   | NO   |     | 0                   |                |
| lockedByUserId     | int(11)      | YES  |     | NULL                |                |
| deprecatedTime     | datetime     | YES  |     | NULL                |                |
| deprecationComment | text         | YES  |     | NULL                |                |
+--------------------+--------------+------+-----+---------------------+----------------+
```

- `isDeprecated`, `deprecatedByUserId`, `deprecatedTime`, `deprecationComment`: **reserved** for
  deprecation.
- `isLocked`, `lockedByUserId`: unused.

## eventRanges

Unused. Assignments reference event ranges in the schema, and no code reads or writes them.

```
+-----------+-----------+------+-----+---------------------+----------------+
| Field     | Type      | Null | Key | Default             | Extra          |
+-----------+-----------+------+-----+---------------------+----------------+
| id        | int(11)   | NO   | PRI | NULL                | auto_increment |
| created   | timestamp | NO   |     | current_timestamp() |                |
| modified  | timestamp | NO   |     | 2007-01-01 00:00:00 |                |
| runNumber | int(11)   | NO   |     | NULL                |                |
| eventMin  | int(11)   | NO   |     | NULL                |                |
| eventMax  | int(11)   | NO   |     | NULL                |                |
| comment   | text      | YES  |     | NULL                |                |
+-----------+-----------+------+-----+---------------------+----------------+
```

## logs

One record per change: what, who, when.

```
+-------------+--------------+------+-----+---------------------+----------------+
| Field       | Type         | Null | Key | Default             | Extra          |
+-------------+--------------+------+-----+---------------------+----------------+
| id          | int(11)      | NO   | PRI | NULL                | auto_increment |
| created     | timestamp    | NO   |     | current_timestamp() |                |
| affectedIds | text         | NO   |     | NULL                |                |
| action      | varchar(7)   | NO   |     | NULL                |                |
| description | varchar(255) | NO   |     | NULL                |                |
| comment     | text         | YES  |     | NULL                |                |
| authorId    | int(11)      | NO   | MUL | NULL                |                |
+-------------+--------------+------+-----+---------------------+----------------+
```

- `affectedIds`: the changed objects, as `|<table><id>|`. The record of a new assignment names its
  set too, `|assignments8|constantSets4|`, and its description ends with `(shared data)` when the
  assignment reuses a stored set.

## properties

**Reserved.** Instance and object metadata, one row per owner and name.

```
+-----------+-------------+------+-----+---------------------+----------------+
| Field     | Type        | Null | Key | Default             | Extra          |
+-----------+-------------+------+-----+---------------------+----------------+
| id        | int(11)     | NO   | PRI | NULL                | auto_increment |
| ownerType | varchar(16) | NO   | MUL | NULL                |                |
| ownerId   | int(11)     | NO   |     | NULL                |                |
| name      | varchar(64) | NO   |     | NULL                |                |
| value     | text        | NO   |     | NULL                |                |
| authorId  | int(11)     | NO   |     | 1                   |                |
| modified  | datetime    | NO   |     | current_timestamp() |                |
+-----------+-------------+------+-----+---------------------+----------------+
```

- `ownerType`: `instance` (with `ownerId` 0), `directory`, `table`, `variation` or `column`.
- Unique index `uq_properties_owner_name` on `(ownerType, ownerId, name)`.

## runRanges

```
+----------+-------------+------+-----+---------------------+----------------+
| Field    | Type        | Null | Key | Default             | Extra          |
+----------+-------------+------+-----+---------------------+----------------+
| id       | int(11)     | NO   | PRI | NULL                | auto_increment |
| created  | timestamp   | NO   |     | 2007-01-01 00:00:00 |                |
| modified | timestamp   | NO   |     | current_timestamp() |                |
| name     | varchar(45) | YES  |     |                     |                |
| runMin   | int(11)     | NO   | MUL | NULL                |                |
| runMax   | int(11)     | NO   |     | NULL                |                |
| comment  | text        | YES  |     | NULL                |                |
+----------+-------------+------+-----+---------------------+----------------+
```

## schemaVersions

One row; `schemaVersion` is 6. CCDB 2.5 refuses a database with another version, and CCDB 2.4 refuses
version 6.

```
+---------------+---------+------+-----+---------+-------+
| Field         | Type    | Null | Key | Default | Extra |
+---------------+---------+------+-----+---------+-------+
| id            | int(11) | NO   | PRI | NULL    |       |
| schemaVersion | int(11) | NO   |     | 1       |       |
+---------------+---------+------+-----+---------+-------+
```

## tags

**Reserved.** A tag names a variation at a time.

```
+--------------+--------------+------+-----+---------------------+----------------+
| Field        | Type         | Null | Key | Default             | Extra          |
+--------------+--------------+------+-----+---------------------+----------------+
| id           | int(11)      | NO   | PRI | NULL                | auto_increment |
| name         | varchar(100) | NO   | UNI | NULL                |                |
| variationId  | int(11)      | NO   | MUL | NULL                |                |
| snapshotTime | datetime(6)  | NO   |     | NULL                |                |
| comment      | text         | YES  |     | NULL                |                |
| authorId     | int(11)      | NO   |     | 1                   |                |
| created      | datetime     | NO   |     | current_timestamp() |                |
+--------------+--------------+------+-----+---------------------+----------------+
```

- `name`: unique (`uq_tags_name`), up to 100 characters.
- `snapshotTime`: a UTC instant with microseconds ([Time](concepts/time.md)).
- In schema 5 this table had only `id` and `name`. The upgrade gives it the new shape and refuses a
  database where it holds rows.

## timeRanges

**Reserved** for validity by time.

```
+----------+----------+------+-----+---------+----------------+
| Field    | Type     | Null | Key | Default | Extra          |
+----------+----------+------+-----+---------+----------------+
| id       | int(11)  | NO   | PRI | NULL    | auto_increment |
| timeFrom | datetime | NO   |     | NULL    |                |
| timeTo   | datetime | YES  |     | NULL    |                |
| comment  | text     | YES  |     | NULL    |                |
+----------+----------+------+-----+---------+----------------+
```

## typeTables

The tables of constants: their directory, name and shape.

```
+--------------------+--------------+------+-----+---------------------+----------------+
| Field              | Type         | Null | Key | Default             | Extra          |
+--------------------+--------------+------+-----+---------------------+----------------+
| id                 | int(11)      | NO   | PRI | NULL                | auto_increment |
| created            | timestamp    | NO   |     | current_timestamp() |                |
| modified           | timestamp    | NO   |     | 2007-01-01 00:00:00 |                |
| directoryId        | int(11)      | NO   | MUL | NULL                |                |
| name               | varchar(255) | NO   |     | NULL                |                |
| nRows              | int(11)      | NO   |     | 1                   |                |
| nColumns           | int(11)      | NO   |     | NULL                |                |
| nAssignments       | int(11)      | NO   |     | 0                   |                |
| authorId           | int(11)      | NO   |     | 1                   |                |
| comment            | text         | YES  |     | NULL                |                |
| isDeprecated       | tinyint(1)   | NO   |     | 0                   |                |
| deprecatedByUserId | int(11)      | YES  |     | NULL                |                |
| isLocked           | tinyint(1)   | NO   |     | 0                   |                |
| lockedByUserId     | int(11)      | YES  |     | NULL                |                |
| lockTime           | timestamp    | YES  |     | NULL                |                |
| deprecatedTime     | datetime     | YES  |     | NULL                |                |
| deprecationComment | text         | YES  |     | NULL                |                |
+--------------------+--------------+------+-----+---------------------+----------------+
```

- `isDeprecated`, `deprecatedByUserId`, `deprecatedTime`, `deprecationComment`: **reserved** for
  deprecation.
- `isLocked`, `lockedByUserId`, `lockTime`: unused.

## users

```
+----------------+--------------+------+-----+---------------------+----------------+
| Field          | Type         | Null | Key | Default             | Extra          |
+----------------+--------------+------+-----+---------------------+----------------+
| id             | int(11)      | NO   | PRI | NULL                | auto_increment |
| created        | timestamp    | NO   |     | current_timestamp() |                |
| lastActionTime | timestamp    | NO   |     | 2001-01-01 00:00:00 |                |
| name           | varchar(100) | NO   |     | NULL                |                |
| password       | varchar(100) | YES  |     | NULL                |                |
| roles          | text         | NO   |     | NULL                |                |
| info           | varchar(125) | NO   |     | NULL                |                |
| isDeleted      | tinyint(1)   | NO   |     | 0                   |                |
+----------------+--------------+------+-----+---------------------+----------------+
```

## variations

```
+--------------------+--------------+------+-----+---------------------+----------------+
| Field              | Type         | Null | Key | Default             | Extra          |
+--------------------+--------------+------+-----+---------------------+----------------+
| id                 | int(11)      | NO   | PRI | NULL                | auto_increment |
| created            | timestamp    | NO   |     | 2007-01-01 00:00:00 |                |
| modified           | timestamp    | NO   |     | current_timestamp() |                |
| name               | varchar(100) | NO   | MUL | default             |                |
| description        | varchar(255) | YES  |     | NULL                |                |
| authorId           | int(11)      | NO   |     | 1                   |                |
| comment            | text         | YES  |     | NULL                |                |
| parentId           | int(11)      | NO   | MUL | 1                   |                |
| isLocked           | tinyint(1)   | NO   |     | 0                   |                |
| lockTime           | timestamp    | YES  |     | NULL                |                |
| lockedByUserId     | int(11)      | YES  |     | NULL                |                |
| goBackBehavior     | int(11)      | NO   |     | 0                   |                |
| goBackTime         | timestamp    | YES  |     | NULL                |                |
| isDeprecated       | tinyint(1)   | NO   |     | 0                   |                |
| deprecatedByUserId | int(11)      | YES  |     | NULL                |                |
| deprecatedTime     | datetime     | YES  |     | NULL                |                |
| deprecationComment | text         | YES  |     | NULL                |                |
+--------------------+--------------+------+-----+---------------------+----------------+
```

- `isDeprecated`, `deprecatedByUserId`, `deprecatedTime`, `deprecationComment`: **reserved** for
  deprecation.
- `isLocked` and `lockTime`: set when a variation is created (`isLocked` to 1), read by nothing.
- `lockedByUserId`, `goBackBehavior`, `goBackTime`: unused.

## assignmentsMaterializedView

Unused.

```
+----------------+-----------+------+-----+---------------------+-------------------------------+
| Field          | Type      | Null | Key | Default             | Extra                         |
+----------------+-----------+------+-----+---------------------+-------------------------------+
| id             | int(11)   | NO   | PRI | NULL                | auto_increment                |
| assignmentsId  | int(11)   | NO   |     | NULL                |                               |
| variationsId   | int(11)   | NO   |     | NULL                |                               |
| constantSetsId | int(11)   | NO   |     | NULL                |                               |
| typeTablesId   | int(11)   | NO   |     | NULL                |                               |
| runRangesId    | int(11)   | NO   |     | NULL                |                               |
| runMin         | int(11)   | NO   |     | NULL                |                               |
| runMax         | int(11)   | NO   |     | NULL                |                               |
| assignmentTime | timestamp | NO   |     | current_timestamp() | on update current_timestamp() |
+----------------+-----------+------+-----+---------------------+-------------------------------+
```

## variationsToTags

The link table of variations and schema 5 tags, `variations_has_tags` on some installations. Schema 6
does not use it: `ccdb db init` no longer creates it, and the upgrade keeps an existing one (on MySQL
and MariaDB it converts it to InnoDB and utf8mb4 like every CCDB table).
