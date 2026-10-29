# Deploying CCDB for a new experiment

This page is for the person who sets up CCDB for an experiment: the database server, the accounts, the
layout of the constants, the rules the collaboration follows, and the way jobs read constants. It
collects what has worked at GlueX since 2012. [Installation](../get-started/installation.md) covers
installing the software; [Deploying the web GUI](webgui.md) covers the web interface.

## Topology

```mermaid
flowchart LR
    CAL[Calibration scripts<br/>and calibrators] -->|write| DB[(MySQL primary)]
    DB -->|read-only user| LAB[Jobs on the lab network]
    DB -->|nightly export| SQL[SQLite snapshot<br/>shared file system or CVMFS]
    DB -->|shallow copy| SC[SQLite per run period<br/>containers, offsite]
    SQL --> FARM[Farm jobs]
    SC --> OFF[Offsite jobs]
    DB -->|read-only user| GUI[Web GUI]
    DB -->|mysqldump| BK[Backups]
```

One MySQL (or MariaDB) server holds the truth. Everything that writes goes there. Everything that reads
in volume reads a copy, because a database connection is the one resource that does not scale with the
number of jobs.

## The database server

Create the schema and the accounts, then initialize the tables:

```sql
CREATE SCHEMA IF NOT EXISTS `ccdb`;
CREATE USER 'ccdb_admin'@'%' IDENTIFIED BY '...';
GRANT ALL PRIVILEGES ON ccdb.* TO 'ccdb_admin'@'%';
CREATE USER 'ccdb_calib'@'%' IDENTIFIED BY '...';
GRANT SELECT, INSERT, UPDATE ON ccdb.* TO 'ccdb_calib'@'%';
CREATE USER 'ccdb_user'@'%';
GRANT SELECT ON ccdb.* TO 'ccdb_user'@'%';
```

```bash
export CCDB_CONNECTION="mysql://ccdb_admin:...@dbhost/ccdb"
ccdb db init      # asks for the init-i-am-sure flag before touching anything
```

| account | who | rights |
|---|---|---|
| `ccdb_admin` | the one or two people who maintain the database | everything, including deletion |
| `ccdb_calib` | calibrators and calibration scripts | read, add constants, create tables and variations |
| `ccdb_user` | every job and every user, no password | read only |

A read-only account without a password is deliberate: constants are not secret, and a job that only
needs a connection string with no secret in it can run anywhere. Keep the writing accounts off the farm.

Two server settings matter. Raise `max_allowed_packet` (32M is enough for large tables) in the
`[mysqld]` section, or large constant sets fail to load. Size `max_connections` for the jobs that will
connect directly; the default of 151 is not a farm. Give the web GUI its own read-only account with a
statement timeout, as [Deploying the web GUI](webgui.md#exposing-the-gui) describes.

CCDB records the author of every change. The name comes from the `CCDB_USER` environment variable, or
the login name when it is not set, and must exist in the database: `ccdb user --create <name>`. Create
the calibrators before they start adding constants.

## Lay out the tree

Directories are for people, tables are for software. A layout that stays readable after ten years:

```
/<detector>/<quantity>                e.g. /ecal/gains
/<detector>/<subsystem>/<quantity>    e.g. /tracker/barrel/alignment
/beam/...  /target/...  /trigger/... for things that are not a detector
```

Rules for a table:

- **One quantity per table.** A table is read whole; software that needs gains should not read
  pedestals with them.
- **One row per channel, fixed row count.** The row count is part of the table definition
  (`mktbl -r`), so the reading code can rely on it. A change in channel count is a new table.
- **Typed, named columns.** Column names are the API that reconstruction code uses; choose them as you
  would choose function names. Types are `int`, `double` or `string`.
- **Units in the comment.** The table comment is the place to say that `offset` is in nanoseconds.

```
ccdb mktbl /ecal/gains -r 1024 gain gain_error #Energy gain per channel, GeV per ADC count
ccdb mktbl /ecal/geometry -r 1 x y z=string #Position of the calorimeter front face, cm
```

See `ccdb help mktbl` for the column format (`<quantity><name>=<type>` creates several columns at
once, for example `8sigma=double`).

## Variations

Variations are branches. A child variation returns its own assignment when it has one for the table and
run, and its parent's otherwise, recursively up to `default`. The standard set:

| variation | parent | use |
|---|---|---|
| `default` | none | the best known constants for real data; what production reads |
| `mc` | `default` | constants for simulation that differ from data: ideal values, no dead channels |
| `<name>_work` | `default` | a calibrator's work in progress; merged into `default` by re-adding the accepted constants there |

```
ccdb mkvar mc #Constants for simulation
ccdb mkvar ecal_work -p default #ECAL timing recalibration, spring 2027
```

Production software reads `default` (or `mc`) and never a work variation. Analysts who want to try
alternative constants create their own variation; nothing they do there affects anyone else.

## Run ranges and the first assignment

The first assignment of every table should cover all runs (`0` to the largest run number), with
nominal values. Then the software never fails because a run has no constants, and every later
assignment narrows the range to the runs it was calibrated for. Run ranges may overlap; for a given run
the most recently created assignment wins, and the older one stays in the history.

```
ccdb add /ecal/gains -v default -r 0- nominal_gains.txt #Nominal gains before the first calibration
ccdb add /ecal/gains -v default -r 10200-10499 gains_pass1.txt #First calibration of the spring run
```

Three rules keep the history useful:

- **Never delete.** A wrong assignment is superseded by a new one. Deleting changes what past
  productions would resolve.
- **Comment every add.** The comment after `#` is what the log and the web GUI show a year later.
- **Check before you declare.** `ccdb vers /ecal/gains` lists the assignments; the web GUI's
  *Compare assignments* page shows what changed between two of them, cell by cell, and offers the
  difference as a unified diff.

## Writing constants from calibration scripts

The text format `ccdb add` reads is a table of numbers with `#` comments, the same format `ccdb dump`
writes, so a calibration script produces files and a second step adds them. Keep the files in a git
repository: a pull request is then the review step, and a script applies accepted files with `ccdb add`.
Scripts that add many tables use the [Python API](../apis/python.md) directly, with the same account as
the CLI, and get exceptions instead of exit codes.

## Serving constants to jobs

| how jobs read | when | notes |
|---|---|---|
| MySQL directly, `mysql://ccdb_user@dbhost/ccdb` | interactive work and small numbers of jobs on the lab network | one connection per job; the C++ client has connect, read and write timeouts (`CCDB_MYSQL_*_TIMEOUT`, see [C++ API](../apis/cpp.md#timeouts-and-reconnect)) and reconnects once after a dropped connection |
| SQLite snapshot of the whole database | farms, containers, any place with a shared file system | made with [mysql2sqlite](../utilities.md#creating-a-sqlite-database) from a dump; publish it on CVMFS or a shared file system; open it as `sqlite:///file:/path/ccdb.sqlite?immutable=1` on network file systems |
| SQLite shallow copy of one run period | offsite jobs, containers that ship their constants | made with [ccdb_shallow_copy.py](https://github.com/JeffersonLab/ccdb/tree/v2-main/scripts/shallow_copy): the constants one run range, one snapshot time and chosen variations need, a few megabytes |

The same program reads all three; only the connection string changes, through `CCDB_CONNECTION` or
the framework's own setting (`JANA_CALIB_URL` for JANA). A snapshot is as old as its export, so publish
a nightly snapshot and say so: a calibrator who adds constants in the afternoon should know when the
farm will see them.

For production, fix the context: the variation and the snapshot time. In JANA this is the
`JANA_CALIB_CONTEXT` variable (`variation=default calibtime=2027-03-01`); in your own code it is the
time passed when the `Calibration` object is created. Every job of the campaign then resolves the same
constants, whatever calibrators add while it runs, and the campaign can be repeated later.

## Web GUI and monitoring

Deploy the web GUI early; it is how calibrators check their work and how everyone else finds out what a
table contains. [Deploying the web GUI](webgui.md) has the steps and the hardening list. Its `/health`
endpoint answers with the database state and the CCDB version, and is meant for the monitoring system.

## Backups

The MySQL server is the only copy that matters; a nightly `mysqldump` kept for a few months is the
minimum. The SQLite snapshot made for the farm is a second copy of the data, but not a substitute: it
loses the user accounts and anything added after the export. Test a restore once before the first run.

The `logs` table records every change with its author and time, and the web GUI's *Logs* page searches
it. That is the audit trail; keep it.

## Streaming readout

A streaming DAQ changes none of the above. What a run means for a streaming experiment, and how a time
frame finds its constants, is on [Streaming readout and runs](../concepts/streaming-readout.md).

## Checklist

- [ ] MySQL server with `max_allowed_packet` raised and `max_connections` sized
- [ ] schema initialized with `ccdb db init`
- [ ] accounts: admin, calibrators, password-less read-only user, GUI user
- [ ] calibrators created with `ccdb user --create`
- [ ] directory tree agreed with the detector groups; table naming rules written down
- [ ] `default` and `mc` variations; rule that production never reads work variations
- [ ] every table has an all-runs first assignment
- [ ] nightly SQLite snapshot published where jobs run; cadence announced
- [ ] web GUI deployed, `/health` monitored
- [ ] nightly `mysqldump`, restore tested
