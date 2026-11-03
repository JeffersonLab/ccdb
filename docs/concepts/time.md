# Time

Every assignment records the moment it was created, and a request can ask for the constants as they were
at a moment: `/calorimeter/gains:1000:default:2026-03-01 12:00`. CCDB stores every time as a UTC instant,
keeps the creation time of an assignment to the microsecond, and resolves a time the same way on MySQL,
MariaDB and SQLite, in Python and in C++.

## Stored times

- **UTC everywhere.** Every time column of every table holds a UTC instant on every engine. A database
  therefore answers a time request the same way wherever the job runs and whatever zone the server or the
  writing client is in.
- **Microseconds where they select constants.** `assignments.created` and `tags.snapshotTime` keep
  microseconds: two assignments added within one second, or a tag made between them, keep their order.
  On MySQL and MariaDB they are `TIMESTAMP(6)` and `DATETIME(6)`; on SQLite every time is the text
  `YYYY-MM-DD HH:MM:SS.ffffff` in UTC, so text order is time order.
- **Whole seconds elsewhere.** The other times (the `created` and `modified` of tables, directories,
  variations, log records) are metadata: CCDB writes them to the second.

## Times you type

A time in a request (`/path:run:variation:time`), in `ccdb cat -t`, `ccdb tag -t`, `calibtime=` of a context
string, `ccdb:time` of the JANA2 service, or a web GUI address uses one format:

```
YYYY-MM-DD hh:mm:ss.ffffff
```

- Groups of digits separated by one character that is not a digit, any one: `2026-03-01 12:00:00`,
  `2026-03-01_12-00-00`, `2026/03/01T12:00:00` are the same time.
- The fraction has 1 to 6 digits. More is an error.
- Any leading part is a time: `2026`, `2026-03`, `2026-03-01 12`.
- A time that does not follow the format, or names a date that does not exist (`2026-02-30`), is an error,
  in Python and in C++.

**A partial time is the latest moment it covers.** It selects the constants that existed at the end of the
part you name:

| you type | the moment |
|---|---|
| `2026` | 2026-12-31 23:59:59.999999 |
| `2026-02` | 2026-02-28 23:59:59.999999 |
| `2026-03-01 12:00:00` | 2026-03-01 12:00:00.999999 |
| `2026-03-01 12:00:00.5` | 2026-03-01 12:00:00.599999 |
| `2026-03-01 12:00:00.123456` | 2026-03-01 12:00:00.123456 |

**A typed time is local wall time.** CCDB converts it to UTC with the zone of the process (`TZ`). Once a year,
when daylight saving time ends, a local hour happens twice; once a year, when it starts, an hour is skipped.
CCDB reads such a time with the UTC offset in effect before the change, as Python does by default (PEP 495,
`fold=0`):

- a repeated time means its first occurrence: in New York, `2026-11-01 01:30` is 05:30 UTC;
- a skipped time moves forward by the gap: `2026-03-08 02:30` is 07:30 UTC, which is 03:30 local time.

## Selecting constants by time

A request with a time returns, among the assignments of the table, run and variation created at or before
that moment, the one added last (the highest id). Two assignments with the same creation time, to the
microsecond, are ordered by id: the later one wins at every moment from then on, and the earlier one is
reached by its id, through the web GUI or the API.

A request with a tag uses the tag's variation and its time, compared to the microsecond: an assignment
created one microsecond after the tag is not part of it. [Tags](concepts/tags.md) describes tags.

The same rules give the same answer on MySQL, MariaDB and SQLite, in Python and in C++. The test data in
`testdata/time/` holds the cases both languages run on every engine: ties within one second and one
microsecond, partial times, three time zones, and tags.

## Shown times

Commands and the web GUI show times as local wall time, to the second. Where a time names an assignment
exactly — `ccdb vers -l`, `ccdb tag NAME`, the request strings in web GUI links — it carries the microseconds
when they are not zero, so the address resolves to that assignment.

## C++

- `ccdb::TimeUtils::ParseLocalTime(text, &ok)` reads a time as above and returns UTC microseconds since
  1970 (`int64_t`).
- A `time_t` given to the C++ API means the end of that second: `CalibrationGenerator::MakeCalibration(url,
  run, variation, t)` and `Calibration(run, variation, t)` read the constants created at or before
  `t.999999`, as they did when the database kept whole seconds. `0` means the newest constants.
- `MakeCalibrationMicro`, `CreateCalibrationMicro` and `DataProvider::GetAssignmentShortMicro` take the time
  in microseconds.

## CCDB 2.4 programs on a schema 6 database

Python CCDB 2.4 does not open a schema 6 database. C++ programs built with CCDB 2.4 read it, with two
differences when a request carries a time:

- On MySQL and MariaDB, a 2.4 program compares the creation time with a whole second, so it does not see
  the assignments created within the second it names, after its start. Requests without a time are
  unaffected.
- On SQLite, a 2.4 program compares the stored UTC text with its own local wall time. West of UTC it sees
  only what was created some hours before the time it names (four or five at Jefferson Lab); east of UTC,
  up to that many hours after it. Requests without a time are unaffected.
