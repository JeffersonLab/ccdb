# Upgrading to CCDB 2.5

This page is for the administrator of a CCDB database. CCDB 2.5 works with database schema version 6;
CCDB 2.4 works with version 5. `ccdb db upgrade` takes a database from version 5 to 6, once, on MySQL,
MariaDB and SQLite; it is tested on MySQL 8.3 and MariaDB 10.5.

To run the commands on this page, install CCDB 2.5 in a separate environment on a machine that reaches
the database server ([Installation](get-started/installation.md)), for example:

```bash
python -m venv ccdb25
ccdb25/bin/python -m pip install "ccdb>=2.5"
ccdb25/bin/ccdb --version
```

CCDB 2.4 has no `db upgrade --dry-run`, `db dedup`, `db rehash` or `db rollback-v6`. Leave the
installations that clients use at 2.4 until step 5.

To upgrade a database:

1. Take a verified backup.
2. Stop every Python client of CCDB 2.4 that uses the database, the web GUI and scripts included.
   C++ jobs may keep reading.
3. Run `ccdb db upgrade --dry-run`, then `ccdb db upgrade --upgrade-i-am-sure`.
4. Run `ccdb db dedup --dedup-i-am-sure` in the same maintenance window.
5. Move every Python installation that reads or writes the database to CCDB 2.5 the same day.

## What changes

**Shared constant sets.** Every constant set gets two columns: `sha256`, the SHA-256 of its text, and
`size`, the number of bytes of that text. Assignments of one table with the same data share one set, and
`ccdb db dedup` merges the byte-identical sets that CCDB 2.4 stored. A unique index on
`(constantTypeId, sha256)` keeps two writers from storing the same data twice.
[Constant sets and their hashes](concepts/constant-sets.md) describes the rules.

**InnoDB and utf8mb4.** On MySQL and MariaDB, the upgrade converts every table still on MyISAM to
InnoDB and every character column to utf8mb4. The column's collation decides the target: a
case-sensitive collation (`*_bin`, `*_cs`) becomes `utf8mb4_bin`, any other `utf8mb4_general_ci`,
which ignores case and trailing spaces as `latin1_swedish_ci` does. The server converts each value
from the column's old character set; text stored wrongly before (UTF-8 bytes written through a latin1
connection, for example) stays as it is. A text column keeps its type: `TEXT` stays `TEXT`. Every
Python connection of CCDB 2.5 uses utf8mb4, so any Unicode character (μs, Ω) can be stored.

**Times in UTC, with microseconds.** Every time CCDB stores becomes a UTC instant on every engine, and
`assignments.created` and `tags.snapshotTime` keep microseconds, so a request with a time or a tag gives the
same answer on MySQL, MariaDB and SQLite wherever the job runs. On MySQL and MariaDB the upgrade changes
`assignments.created` to `TIMESTAMP(6)` in the statement that rebuilds `assignments` anyway (7.8 s for
821 394 assignments on a copy of the Hall D database), and `tags.snapshotTime` to `DATETIME(6)`; the stored
instants do not change. On SQLite the upgrade rewrites every time from the writers' local time to UTC, so it
needs the zone the file was written in (below). [Time](concepts/time.md) gives the rules.

**New tables and columns.** The upgrade also creates tables and columns that no command of this version
reads or writes yet. The table marks them reserved; the others are in use.

| object | purpose | status |
|---|---|---|
| `constantSets.sha256`, `constantSets.size` | identity and size of a set's data | in use |
| index `uq_constantSets_table_sha256` (or the interim `ix_constantSets_table_sha256`) | finds a table's set by hash; the unique form rejects a second copy | in use |
| `tags` (new shape: `variationId`, `snapshotTime`, `comment`, `authorId`, `created`) | named snapshots of a variation at a time | reserved |
| `properties` | instance and object metadata: description, contact, license, citation | reserved |
| `columns.units` | the units of a column | reserved |
| `deprecatedTime`, `deprecationComment` on `directories`, `typeTables`, `variations` | deprecation of tables, directories and variations | reserved |
| `timeRanges`, `assignments.timeRangeId` | validity by time | reserved |

Nothing is dropped. `eventRanges`, `assignmentsMaterializedView`, the `isLocked` columns and the link
table `variationsToTags` (`variations_has_tags` on some installations) stay. A database created fresh
by CCDB 2.5 has no link table. [Database schema](concepts/database-schema.md) lists every column.

## Clients after the upgrade

| client | on a schema 6 database |
|---|---|
| Python CCDB 2.5 | works |
| Python CCDB 2.4 CLI and scripts, started after the upgrade | refuse to connect, exit code 1 |
| Python CCDB 2.4 web GUI, started after the upgrade | answers its requests with the version error |
| Python CCDB 2.4, connected before the upgrade | keeps reading; its open transaction blocks the upgrade (with `PROCESS` the upgrade refuses while it is open); its new data fails or is stored without a hash (below) |
| Python CCDB 2.4 code that connects with `check_version=False` | reads; its new data fails or is stored without a hash (below) |
| C++ jobs built with CCDB 2.4 | keep reading, shared sets included; a request with a time sees UTC times ([Time](concepts/time.md#ccdb-24-programs-on-a-schema-6-database)) |
| Python CCDB 2.5 on a schema 5 database | refuses to connect, exit code 1 |

CCDB 2.4 on an upgraded file:

```
$ ccdb ls /test
CCDB provider unable to connect to sqlite:///ccdb.sqlite. Aborting command. Exception details: Version mismatch. The database schema version is '6'. This CCDB version works with schema version 5
```

CCDB 2.5 on a database that is not upgraded yet:

```
$ ccdb ls /test
CCDB provider unable to connect to sqlite:///ccdb.sqlite. Aborting command. Exception details: The database schema version is 5. This CCDB version works with schema version 6. Upgrade with 'ccdb db upgrade' (docs/deployment/upgrade-2.5.md)
```

Once `sha256` and `size` are `NOT NULL`, new data from CCDB 2.4 fails on a server with a strict
`sql_mode` (`Field 'sha256' doesn't have a default value`); the run range of that `add` may already be
written. A non-strict server stores the set with an empty `sha256` and size 0:
`ccdb db rehash --rehash-i-am-sure` repairs such sets, and `ccdb db dedup --dedup-i-am-sure` refuses
until then.

Python clients and the database change version together: upgrade every Python installation that
reads or writes the database (calibration scripts, the web GUI, shared installations on the farm) on
the day of the upgrade.

The C++ library has no version check and reads named columns, so new columns and tables do not affect
it, and it reads a shared set through each of its assignments. A C++ 2.4 job on a schema 6 database
after `db dedup` returns the same assignments and the same bytes as Python 2.5. It may run during the
upgrade: a reader that holds no transaction does not block it. A C++ job whose MySQL connection uses
latin1 reads ASCII text as before; a non-ASCII character that CCDB 2.5 stores later (μs, Ω) arrives
there as `?`.

## Preparing

**Backup.** Take a dump or a storage snapshot and check that it restores. No `ccdb` command makes a
backup. `db dedup` deletes sets permanently, and on MariaDB before 10.6, which has no atomic DDL, a server
crash during an `ALTER TABLE` can leave a table that only the backup repairs.

**Account.** Run the upgrade with an account that has `SELECT`, `ALTER`, `CREATE`, `INDEX`, `INSERT`,
`UPDATE` and `DELETE` on the database; `db rollback-v6` also needs `DROP`. `PROCESS` is a global privilege and lets
the command see other sessions' open transactions (below):

```sql
GRANT SELECT, ALTER, CREATE, INDEX, INSERT, UPDATE, DELETE, DROP ON ccdb.* TO 'ccdb_admin'@'%';
GRANT PROCESS ON *.* TO 'ccdb_admin'@'%';
```

The examples on this page name this account `ccdb_admin`, and a `SELECT`-only account `ccdb_reader`.
Give a password in the connection string, `mysql://ccdb_admin:<password>@dbhost/ccdb`
([Connection strings](concepts/concepts.md#connection-strings)). Privileges granted through a role do
not show in the views the check reads; then add `--skip-privilege-check`.

**CCDB user.** `db dedup --dedup-i-am-sure` and `db rehash --rehash-i-am-sure` write log records signed
by the CCDB user named in `CCDB_USER`, or in `USER` (your login name) when `CCDB_USER` is not set. The name must exist in
the database's `users` table: `ccdb user --list` lists them, `ccdb user --create <name>` adds one. Set it
before the maintenance window:

```bash
export CCDB_USER=<name>
```

With an unknown name, a dedup that has sets to merge or remove changes nothing and exits with 1:

```
No user with name 'nobody_here' is found in database. Set the user name by CCDB_USER environment variable. See 'ccdb user' command to create a user.
```

**Open transactions.** An `ALTER TABLE` waits for every open transaction on its table, and every later
reader waits behind it. With `PROCESS`, the upgrade lists the other sessions and refuses while one of
them holds a transaction open or runs a query longer than 60 seconds. Without `PROCESS` it cannot see
them, refuses, and proceeds only with `--no-transaction-check`, after you have stopped the clients.
Idle sessions, such as C++ jobs between reads, are listed and do not block. The refusal, here from
`db dedup --dedup-i-am-sure` while another session held a transaction open:

```
Dedup refused, nothing was changed: other sessions hold a transaction open on this database or run a query longer than 60 s; every ALTER would wait for them: id 38199 root@localhost (Query for 3 s, InnoDB transaction open since 2026-11-01 19:46:16, running a SELECT statement). End them (stop the clients), or add --no-transaction-check
```

**Disk, binary log and replicas.** Converting a table copies it, so the server needs free space for the
largest table once more (`constantSets`, 4.9 GB at GlueX). With row-based binary logging, the hash
backfill writes about twice the bytes of all constant set text to the binary log (3 255 MB of text at
GlueX). A replica applies the same statements and needs the same free space. The dry run prints the
space, the binary log settings (with the estimated bytes when binary logging is on) and the replica
status.

**What stops the upgrade before any change.** The upgrade refuses, names the tables, columns or rows,
and changes nothing in these cases. Fix the cause, then run the dry run again:

| refusal | what to do |
|---|---|
| `schemaVersions` does not hold exactly one row with version 5 | check that this is a CCDB 2.4 database; a version below 5 needs the upgrade of CCDB 2.4 first |
| `tags` holds rows | schema 5 tags have no variation or time: save the rows, then empty the table |
| a CCDB table has a foreign key constraint | CCDB declares none: drop the named constraints |
| a value would not survive the conversion to utf8mb4, or would no longer fit its column | correct the named rows |
| two names would become equal under the new collation | rename one name of each named pair |
| a `vault` or `name` column is declared binary | change the column to a text type |

## Dry run

`ccdb db upgrade --dry-run` prints what the upgrade would do and writes nothing. It is safe on a
production server with an account that has `SELECT` only. It exits with 0 at version 5, also when the
preflight would refuse, and with 1 when `schemaVersions` does not hold exactly one row with version 5
or, on SQLite, no file exists at the path. By default it reads no constant set data: the counts come
from `information_schema` and row counts.

```bash
ccdb -c mysql://ccdb_reader@dbhost/ccdb db upgrade --dry-run
```

It prints the server version and session settings; the preflight (privileges, open transactions,
what would refuse the upgrade, disk, binary log, replicas); every table with its engine, size and
collation and what changes, MyISAM tables listed with their sizes; every statement in order with its
lock clause; the number of sets to hash; and an estimate of the time. On a schema 5 test database on
MariaDB 10.5, with MyISAM tables as `ccdb db init` of CCDB 2.4 creates them:

```
Dry run of 'ccdb db upgrade': nothing is written
Server: 10.5.29-MariaDB-ubu2004
  alter_algorithm: DEFAULT
  innodb_instant_alter_column_allowed: add_drop_reorder
  session: autocommit=0, isolation=REPEATABLE-READ, sql_mode='STRICT_TRANS_TABLES,ERROR_FOR_DIVISION_BY_ZERO,NO_AUTO_CREATE_USER,NO_ENGINE_SUBSTITUTION', lock_wait_timeout=86400, time_zone=SYSTEM, system_time_zone=UTC
  the upgrade sets sql_mode='STRICT_ALL_TABLES,NO_ENGINE_SUBSTITUTION' and lock_wait_timeout=10 for its session

Preflight:
  privileges of 'ccdb_reader'@'%' on this database: SELECT, USAGE
  open transactions: cannot be seen without the PROCESS privilege; the upgrade then needs --no-transaction-check
  would refuse: the account 'ccdb_reader'@'%' lacks the privileges ALTER, CREATE, INDEX, INSERT, UPDATE, DELETE on this database, which the command needs (it has: SELECT, USAGE)
  Resources: a rebuild of the largest table, assignments, needs about 8.7 kB of free disk space (the server cannot report free space over SQL)
  Resources: log_bin=OFF, binlog_format=MIXED, binlog_row_image=FULL
  Resources: replica status: unknown (reading it needs the REPLICATION CLIENT or SLAVE MONITOR privilege)

Tables:
  assignments: 8664 bytes, engine MyISAM, row format Dynamic, collation utf8mb4_general_ci; engine MyISAM to InnoDB
  ...
  MyISAM tables, converted to InnoDB by a copy: assignments (8664 bytes), assignmentsMaterializedView (1024 bytes), ...

Statements, in order:
  step 1: ALTER TABLE `assignments` ENGINE = InnoDB, ADD COLUMN `timeRangeId` INT NULL DEFAULT NULL, ADD INDEX `fk_assignments_timeRanges1_idx` (`timeRangeId`), ALGORITHM=COPY, LOCK=SHARED;
  ...
  step 1: ALTER TABLE `constantSets` ENGINE = InnoDB, ADD COLUMN `sha256` CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NULL DEFAULT NULL, ADD COLUMN `size` INT UNSIGNED NULL DEFAULT NULL, ALGORITHM=COPY, LOCK=SHARED;
  ...
  step 2: hash 8 of 8 constant sets in batches of 500 (about 364 bytes of vault text, estimated from DATA_LENGTH)
  step 3: ALTER TABLE `constantSets` MODIFY `sha256` CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, MODIFY `size` INT UNSIGNED NOT NULL, ALGORITHM=INPLACE, LOCK=NONE;
  step 4: ALTER TABLE `constantSets` ADD UNIQUE INDEX `uq_constantSets_table_sha256` (`constantTypeId`, `sha256`), ALGORITHM=INPLACE, LOCK=NONE; or, while a table holds duplicate sets, the same with the interim non-unique index `ix_constantSets_table_sha256`
  step 5: UPDATE schemaVersions SET schemaVersion = 6;

Duplicate sets: not counted (--duplicates none reads no vault); 'sample' or 'all' counts them

Estimated time: about 0 s at the rates of the trial copy of hallddb on local NVMe (slower storage takes longer)
```

The `would refuse` line is the expected answer for a `SELECT`-only account; the same account with
`--upgrade-i-am-sure` is refused before any change. Run the upgrade itself with an account that has
the privileges above. The time estimate uses rates measured on a copy of the GlueX database, named
`hallddb` in the output.

`--duplicates` decides how the dry run counts byte-identical sets:

| value | reads | use |
|---|---|---|
| `none` (default) | no constant set data | any server |
| `sample` | the SHA-256 the server computes for every set of the 20 tables with most sets | production, a bounded read |
| `all` | the same for every set: a full read of `constantSets` through the buffer pool | a copy of the database |

```
$ ccdb -c mysql://ccdb_reader@copyhost/ccdb db upgrade --dry-run --duplicates all
...
Duplicate sets in all tables: 1 groups in 1 tables, 2 redundant sets, about 46 bytes; the upgrade would create the interim index
```

On SQLite the dry run names the copy it would work on and lists the changes:

```
$ ccdb -c sqlite:///ccdb.sqlite db upgrade --dry-run --duplicates all
Dry run of 'ccdb db upgrade': nothing is written
File: ccdb.sqlite, 184320 bytes, encoding UTF-8 (SQLite text is always Unicode: nothing to convert)
The upgrade works on a copy, 'ccdb.sqlite.v6', and replaces the file with it, keeping the original as 'ccdb.sqlite.v5' (--in-place changes the file itself)
Changes, in one transaction:
  directories: new column deprecatedTime DATETIME NULL
  ...
  constantSets: rebuilt with sha256 and size, 8 sets hashed in batches of 500
  tags: created anew in its schema 6 shape
  timeRanges: new table
  properties: new table
  constantSets: the unique index uq_constantSets_table_sha256, or the interim index ix_constantSets_table_sha256 while a table holds duplicate sets
  schemaVersions: 6
Duplicate sets: 1 groups in 1 tables, 2 redundant sets
```

## Timing on a copy

The dry run's estimate uses rates measured on one machine. To know how long your database takes, time
the upgrade on a copy:

1. Load a dump of the database into a server of the same version, with the production settings
   (`innodb_buffer_pool_size`, `innodb_log_file_size`, `innodb_flush_log_at_trx_commit`, `sql_mode`,
   character set).
2. Run `ccdb db upgrade --dry-run --duplicates all` there to count the duplicates.
3. Time the upgrade and the dedup:
   ```bash
   time ccdb -c mysql://ccdb_admin@copyhost/ccdb db upgrade --upgrade-i-am-sure
   time ccdb -c mysql://ccdb_admin@copyhost/ccdb db dedup --dedup-i-am-sure
   ```
4. Allow for slower storage on the production server.

The steps were measured on a copy of the GlueX database (MariaDB 10.5.29 in a container with the
production settings: buffer pool 1 GB, redo log 64 MB, `innodb_flush_log_at_trx_commit=1`, latin1; local
NVMe storage), by scripts that run the upgrade's statements:

| quantity | value on the GlueX copy |
|---|---|
| constant sets / assignments | 821 431 / 821 394, in 679 tables |
| constant set text | 3 255 MB; `constantSets` 4.9 GB on disk |
| per-table `ALTER` of the 13 other tables | 11.9 s (`assignments` 6.6 s, `logs` 3.6 s) |
| `constantSets`: character set and new columns, one copy | 29.3 s |
| hash backfill, 1 643 batches of 500 sets | 95—100 s |
| `sha256` and `size` made `NOT NULL` | 19.6 s |
| interim index | 2.8 s |
| upgrade in all | about 160 s |
| byte-identical duplicates | 235 645 sets (28.7 %) in 274 tables, 66 152 groups, 384 MB |
| sets equal as numbers but not as text (`0` and `0.0`), kept apart | 1 379 |
| dedup: 235 622 assignments moved, 235 645 sets deleted | 36.6 s |
| unique index | 1.6 s |
| constant sets after dedup | 585 786 |

On MySQL and on MariaDB 10.6.9 or newer, the new columns of `constantSets` are added instantly and the
table is rebuilt once, in step 3, instead of twice; these timings are not measured there.

## Running the upgrade

```bash
ccdb -c mysql://ccdb_admin@dbhost/ccdb db upgrade --upgrade-i-am-sure
```

Without `--upgrade-i-am-sure` the command changes nothing and exits with 1:

```
$ ccdb db upgrade
(!!!) DO NOT PERFORM ON PRODUCTION DATABASE WITHOUT PROPER BACKUP (!!!)
This command tries to upgrade DB structure to current version
Run it with --dry-run first to see what it would do
Add --upgrade-i-am-sure flag to this command to really execute
```

On MySQL and MariaDB the upgrade runs five steps and prints every statement:

1. One `ALTER TABLE` per table: engine, character set, new columns (empty), new indexes; then the new
   tables. Each statement names its algorithm and lock. A conversion copies the table and lets reads
   through (`ALGORITHM=COPY, LOCK=SHARED`); so does the longer `tags.name`. New indexes are added in
   place (`ALGORITHM=INPLACE, LOCK=NONE`). New columns are added instantly (`ALGORITHM=INSTANT`) on
   MySQL and on MariaDB 10.6.9 or newer; on older MariaDB a table that gains columns is rebuilt in place
   (`FORCE, ALGORITHM=INPLACE, LOCK=NONE`), which avoids a corruption bug of instant `ADD COLUMN` there
   (MDEV-18519).
2. The backfill: it reads the sets without a hash in batches of 500, computes `sha256` and `size` in
   Python and commits each batch.
3. `sha256` and `size` become `NOT NULL`. On MySQL and on MariaDB 10.6.9 or newer, when `constantSets` is
   InnoDB already, its character set change is made in this statement, a copy, so the table is rebuilt
   once.
4. The unique index when no table holds duplicate sets, otherwise the interim index
   `ix_constantSets_table_sha256` and the advice to run `db dedup`.
5. `schemaVersions` is set to 6, last.

The session runs with `sql_mode='STRICT_ALL_TABLES,NO_ENGINE_SUBSTITUTION'` and a lock wait timeout of
10 seconds; a statement that times out is retried three times. After the fourth wait the upgrade stops
and names the sessions on the database it can see: end the transaction of the one that holds the lock, then run
the upgrade again. Every step checks what exists first, so an interrupted upgrade, which leaves
version 5, continues where it stopped when you run it again. On a database that is at version 6
already it refuses and changes nothing. The end of the output on the test database above:

```
...
Backfill: hashed 8 constant sets
ALTER TABLE `constantSets` MODIFY `sha256` CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, MODIFY `size` INT UNSIGNED NOT NULL, ALGORITHM=INPLACE, LOCK=NONE
ALTER TABLE `constantSets` ADD INDEX `ix_constantSets_table_sha256` (`constantTypeId`, `sha256`), ALGORITHM=INPLACE, LOCK=NONE
Some CCDB tables hold constant sets with equal data, so constantSets has the interim index ix_constantSets_table_sha256. Run 'ccdb db dedup --dedup-i-am-sure' to merge them and create the unique index uq_constantSets_table_sha256; until then two writers can store the same data twice
Schema version is 6
```

### SQLite files

A SQLite file is upgraded on a copy: the upgrade writes `<file>.v6`, checks it, and replaces the file
with it in one rename, keeping the original as `<file>.v5`. Jobs that have the old file open keep
reading it; new ones open the upgraded file. An interruption leaves the original untouched.

```
$ ccdb -c sqlite:///ccdb.sqlite db upgrade --upgrade-i-am-sure --sqlite-time-zone America/New_York
ALTER TABLE "directories" ADD COLUMN "deprecatedTime" DATETIME NULL
...
Copied and hashed 8 constant sets
...
'ccdb.sqlite' replaced by its changed copy; the file before the change is kept as 'ccdb.sqlite.v5'
Schema version is 6. Delete 'ccdb.sqlite.v5' when you are satisfied
```

`--sqlite-time-zone` is required for an SQLite file: an SQLite file stores the local time of the clients that
wrote it and does not say which zone that was. Give the IANA name of that zone (`America/New_York` for files
made at Jefferson Lab, `Europe/Berlin`, `UTC`). `--dry-run --sqlite-time-zone ZONE` prints, per time column,
the first and last value before and after the conversion, and how many values fall in an hour that repeats or
is skipped at a daylight-saving change. A file written by clients in different zones cannot be converted
exactly; convert it with the zone of most of its writers.

While `<file>.v5` exists, the upgrade of that file refuses; move it away or delete it once the upgraded
file works. `--in-place` changes the file itself, without a copy, for a file no job reads.

SQLite snapshots that jobs read, such as files on CVMFS, follow the same rule as the server: CCDB 2.5
Python reads only schema 6 files and CCDB 2.4 Python only schema 5 files; C++ jobs read both. Publish
snapshots exported from the upgraded server when the Python clients move to 2.5, or upgrade a published
file with `ccdb db upgrade --upgrade-i-am-sure`.

## Merging duplicate sets

`ccdb db dedup` finds, per table, the sets with equal SHA-256 and the sets no assignment uses. Without a
flag it reports and changes nothing:

```
$ ccdb db dedup
Dedup report, nothing is changed (add --dedup-i-am-sure to merge and remove):
  /test/test_vars/test_table: 1 groups of equal sets, 2 sets would go (46 bytes), 2 assignments would move to the oldest set of their group, 0 unused sets would be removed (0 bytes)
  /test/test_vars/test_table2: 0 groups of equal sets, 0 sets would go (0 bytes), 0 assignments would move to the oldest set of their group, 1 unused sets would be removed (5 bytes)
In all: 2 tables, 1 groups, 2 sets would go, 2 assignments would move, 1 unused sets would be removed, 51 bytes saved
```

With `--dedup-i-am-sure` it merges each group into its oldest set (the smallest id), moves the
assignments of the others to it, deletes the others and the unused sets, and writes one log record per
changed table. It compares the bytes of the sets of each group: two sets with one hash and different bytes
stop the run, and that table is left unchanged. When no table holds duplicates any more, it creates the
unique index and drops the interim one:

```
$ ccdb db dedup --dedup-i-am-sure --no-transaction-check
No transaction check: open transactions of other sessions cannot be seen without the PROCESS privilege
/test/test_vars/test_table: merged 2 constant sets into 1, removed 0 unused sets
/test/test_vars/test_table2: merged 0 constant sets into 0, removed 1 unused sets
Dedup: merged 2 constant sets into 1, removed 1 unused sets
Session before the change: autocommit=0, isolation=REPEATABLE-READ, sql_mode='STRICT_ALL_TABLES,NO_ENGINE_SUBSTITUTION', lock_wait_timeout=10, time_zone=SYSTEM, system_time_zone=UTC
ALTER TABLE `constantSets` ADD UNIQUE INDEX `uq_constantSets_table_sha256` (`constantTypeId`, `sha256`), ALGORITHM=INPLACE, LOCK=NONE
ALTER TABLE `constantSets` DROP INDEX `ix_constantSets_table_sha256`, ALGORITHM=INPLACE, LOCK=NONE
```

Until the unique index exists, two writers that add the same data at the same moment can store it
twice. To close that gap, run dedup in the maintenance window of the upgrade; a later dedup merges any
such pair. A second run finds nothing to do.

A set whose stored `sha256` is not 64 lower-case hex digits (an empty hash that CCDB 2.4 wrote on a
non-strict server, for example) could equal any other set. While one exists, `ccdb db dedup` warns,
and `--dedup-i-am-sure` changes nothing and exits with 1:

```
Dedup refused, nothing was changed: 1 row (id 5) of constantSets have a sha256 that is not 64 lowercase hex characters, so their duplicates cannot be found. Run 'ccdb db rehash --rehash-i-am-sure' first
```

Merging changes no assignment id and no creation time, and the merged sets held the same bytes, so
every request returns the same assignment with the same data as before. `--table PATH` limits the run
to one table. Like the upgrade, `--dedup-i-am-sure` checks for open transactions and needs `PROCESS` or
`--no-transaction-check`. On SQLite, dedup changes the file in place, one transaction per table.

## Verifying stored hashes

`ccdb db rehash` recomputes the SHA-256 and size of every set and compares them with the stored
values. It exits with 1 when any differs:

```
$ ccdb db rehash
Rehash: checked 5 constant sets
  constant set 3 (table id 2): stored sha256 '460cfda750b2e85b51d5ee6d7b8f390635a61c25763daca5a2592ba7849340ce' size 8, its data gives sha256 24a9e9d3fedf298cf5076b6957811e9d6acaffb2767fe2986bea01290f5809bb size 8
  1 mismatches; add --rehash-i-am-sure to rewrite the stored hashes
```

The set in this example was changed by an SQL `UPDATE` outside CCDB. `--rehash-i-am-sure` rewrites the
stored hashes and writes a log record; it exits with 0 when every mismatch was repaired.

A rewrite can give a set the hash of another set of its table whose data it equals. While the table
has only the interim index `ix_constantSets_table_sha256`, rehash makes the rewrite and names both sets;
`ccdb db dedup --dedup-i-am-sure` then merges them. Once the unique index `uq_constantSets_table_sha256`
exists, rehash refuses that rewrite and exits with 1:

```
  constant set 5 not rewritten: its data equals constant sets 4 of the same table, and the unique index uq_constantSets_table_sha256 allows one set per hash in a table. Point its assignments to constant set 4 and delete it with SQL, then rerun rehash
```

| flag | effect |
|---|---|
| `--sample N` | checks N sets spread over the id range |
| `--server` | also compares with the SHA-256 the MySQL or MariaDB server computes (`SHA2()`), a second implementation; refused on SQLite |
| `--rehash-i-am-sure` | rewrites mismatching hashes |

```
$ ccdb db rehash --server
Rehash: checked 5 constant sets, also against the server's SHA2
  every stored hash equals the data
```

## Rolling back

`ccdb db rollback-v6 --rollback-i-am-sure` returns a database to version 5, for CCDB 2.4. It drops what
the upgrade added: `sha256`, `size` and their indexes, `timeRangeId`, `units`, `deprecatedTime`,
`deprecationComment`, the tables `timeRanges` and `properties`, and the new columns and indexes of
`tags`, whose `name` returns to `VARCHAR(45)`; `assignments.created` returns to whole seconds, the fraction
cut, and an SQLite file's times return to local time in the zone of `--sqlite-time-zone`, which the SQLite
rollback requires. It also takes a version 5 database that an interrupted
upgrade left half done. After the rollback, CCDB 2.5 refuses the database: install CCDB 2.4 again
wherever Python reads or writes it.

```
$ ccdb db rollback-v6 --rollback-i-am-sure --no-transaction-check
Server: 10.5.29-MariaDB-ubu2004
No transaction check: open transactions of other sessions cannot be seen without the PROCESS privilege
...
ALTER TABLE `constantSets` DROP INDEX `uq_constantSets_table_sha256`, DROP COLUMN `sha256`, DROP COLUMN `size`, FORCE, ALGORITHM=INPLACE, LOCK=NONE
...
DROP TABLE `timeRanges`
DROP TABLE `properties`
Schema version is 5
```

What stays changed:

- Engines and character sets: tables stay InnoDB and utf8mb4, which CCDB 2.4 works with.
- Merged duplicates stay merged. Their bytes were identical, so no data is lost, but assignments now
  share sets. CCDB 2.4 deletes a set together with its assignment: on a server with a strict
  `sql_mode`, its `rm -a` of an assignment whose set is shared fails; on a non-strict server it would
  delete the shared set under the other assignments. The rollback therefore refuses when the server's
  global `sql_mode` is not strict, unless you add `--allow-non-strict`. On SQLite, `rm -a` of CCDB 2.4
  fails on an assignment whose set is shared, as on a strict server, and changes nothing.

The rollback refuses while the new tables or columns hold data, since CCDB 2.4 cannot keep it;
`--drop-v6-data` deletes that data first:

```
The rollback to schema 5 is refused, nothing was changed:
  schema 6 data exists (rows in properties: 1, columns.units values: 1). 2.4 cannot hold it; add --drop-v6-data to delete it with the rollback
```

On SQLite the rollback works on a copy like the upgrade and keeps the file as it was before as
`<file>.before-rollback`; `--in-place` skips the copy. While `<file>.before-rollback` exists, the
rollback of that file refuses; move it away once the rolled-back file works. For an SQLite file that
nothing has written to since the upgrade, restoring the kept `<file>.v5` returns it to version 5 too.
The rollback also takes `--skip-privilege-check` and `--no-transaction-check`.

## Exit codes and confirmation flags

Every `db` subcommand that changes data acts only with its own flag, `--<verb>-i-am-sure`, as
`ccdb db init --init-i-am-sure` does. Without it the command reports, verifies or warns, and
changes nothing. No command asks a question and none makes a backup.

| command | without its flag | exit code |
|---|---|---|
| `db upgrade --upgrade-i-am-sure` | prints the backup warning, changes nothing | 0 on success; 1 without the flag, on a refusal or an error |
| `db upgrade --dry-run` | (writes nothing by design) | 0 at version 5, also when the preflight would refuse; 1 when `schemaVersions` does not hold exactly one row with version 5, or no SQLite file exists at the path |
| `db dedup --dedup-i-am-sure` | prints the report | 0 on success; 1 on a refusal or a collision |
| `db rehash --rehash-i-am-sure` | verifies | 0 when every hash matches or was repaired; 1 on a mismatch left |
| `db rollback-v6 --rollback-i-am-sure` | prints the backup warning, changes nothing | 0 on success; 1 without the flag or on a refusal |

## Checklist

- [ ] CCDB 2.5 installed in a separate environment; `ccdb --version` prints 2.5
- [ ] verified backup of the database
- [ ] `CCDB_USER` set to a user that exists in the database
- [ ] dry run on production with a read-only account; the lines `would refuse` understood
- [ ] upgrade and dedup timed on a copy; maintenance window announced
- [ ] every Python 2.4 client stopped: GUI, scripts, cron jobs
- [ ] `ccdb db upgrade --upgrade-i-am-sure`; `ccdb db` prints `Schema version: 6`
- [ ] `ccdb db dedup --dedup-i-am-sure`; a second `ccdb db dedup` prints `no table holds duplicate or unused constant sets`
- [ ] `ccdb db rehash --sample 1000` (on MySQL and MariaDB with `--server`) prints `every stored hash equals the data`
- [ ] CCDB 2.5 installed wherever Python reads or writes the database; GUI restarted
- [ ] SQLite files that Python clients read: upgraded with `ccdb db upgrade`, or exported again
