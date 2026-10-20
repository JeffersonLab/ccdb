# Shallow copy of a CCDB database

`ccdb_shallow_copy.py` makes a small database that holds only the constants a run period, a point
in time and a set of variations need. Use it to ship constants for one run period to jobs that
cannot reach the MySQL server, instead of the full SQLite snapshot.

## Make a copy

To copy runs 140000–140901 of the `default` and `mc` variations from hallddb into a new SQLite file,
run from the repository root:

```bash
python scripts/shallow_copy/ccdb_shallow_copy.py \
    mysql://ccdb_user@hallddb.jlab.org/ccdb sqlite:///ccdb_140000-140901.sqlite \
    --run-min 140000 --run-max 140901 --variations default,mc
```

| option | meaning |
|---|---|
| `--run-min`, `--run-max` | the run period; `--run-max` defaults to `--run-min` (one run) |
| `--time` | keep the constants valid at this time, in CCDB format (`2024-05-01_12-00-00`); default: the latest |
| `--variations` | comma-separated names, or `*` for all; default: `default` |
| `--overwrite` | replace an existing SQLite target file; other targets must be empty databases |
| `--copy-passwords` | copy user passwords; they are blanked by default |
| `--full` | copy every row of every table instead |
| `--per-run` | select assignments with one `get_assignment` call per table, variation and run: the slow reference method |
| `--time-limit` | stop after this many seconds and report where the copy stopped; the copy is then incomplete |
| `--report-json` | write the report (counts, seconds, file size, peak memory) to a file |

The script prints the report as JSON. Exit codes: 0 success, 2 bad arguments or databases,
3 time limit reached.

## What the copy answers

A lookup in the copy returns the same constants as the source when it asks for:

- a copied variation (a listed one or one of its parents),
- a run inside the period,
- no time, or a time at or after `--time`.

Lookups outside the period, or for a variation that was not copied, fail with "no assignment".
Lookups with an earlier time can differ from the source: the copy keeps only the assignments that
win at `--time`.

## What the copy holds

- All users, directories, tables and columns, and the schema version.
- The listed variations and their parents.
- For every table, listed variation and run: the assignment `get_assignment` returns, which is the
  highest assignment id created at or before `--time`, with fallback to the parent variation.
  Each such assignment comes with its constant set.
- Run ranges clipped to the period. A range inside the period keeps its row. A wider range gets a
  new row, with an id above the source maximum and a comment naming the original.
- `typeTables.nAssignments` recounted for the copy.
- One log record with the copy parameters. Source logs, tags and event ranges are not copied.
- Every column of the source. A column the target schema lacks is added to the target.

## How the selection works

One query reads the candidates for the whole database: the assignments of the copied variations
whose run range overlaps the period. Then, table by table, the script hands out the runs of the
period to the candidates in descending id order, level by level along each variation chain.
That gives the same assignments as calling `get_assignment` for every run, without the per-run
queries. The script then copies the table's run ranges, constant sets and assignments, and frees
its candidates before the next table.

## Check a copy

To compare a copy with its source lookup by lookup, run `verify_shallow_copy.py` with the same
period, time and variations:

```bash
python scripts/shallow_copy/verify_shallow_copy.py \
    sqlite:///ccdb_full.sqlite sqlite:///ccdb_140000-140901.sqlite \
    --run-min 140000 --run-max 140901 --variations default,mc
```

For every table, variation and run it calls `get_assignment` on both databases and compares the
assignment ids, and the constants of each returned assignment. Runs just outside the period must
find nothing in the copy. The tables are split over worker processes (`--workers`, default: cores − 2).
Run it against a full SQLite copy of the server rather than the server itself: a check sends two
lookups per table, variation and run.

## Tests

```bash
python -m unittest discover -s scripts/shallow_copy
```

The tests build small SQLite databases in a temporary directory. A seeded random database
checks that the default selection, the `--per-run` reference and the source give the same answers.
