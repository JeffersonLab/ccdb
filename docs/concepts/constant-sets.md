# Constant sets and their hashes

A constant set holds the values of one table for one assignment: the rows and columns of
`/test/test_vars/test_table` that a request for run 1000 returns, for example. CCDB stores a set as
one text, the values of every row in order, separated by `|`:

```
2.2|2.3|2.4|2.5|2.6|2.7
```

From CCDB 2.5 on (database schema version 6), every set also stores the SHA-256 of that text and its
size in bytes. The hash is the identity of the data: assignments of one table with the same data share
one set.

## Identity rule

The identity of a set is the SHA-256 of its text encoded as UTF-8, inside one table:

- Two sets of one table with the same bytes are the same data, and CCDB stores them once.
- Two tables never share a set, even when their bytes are equal.
- The hash and the size are computed in Python when the set is written, and stored in the columns
  `constantSets.sha256` (64 lower-case hex digits) and `constantSets.size`. The database server never
  computes the stored values.

The hash is the ordinary SHA-256 of the text, so any tool reproduces it:

```bash
printf '%s' '2.2|2.3|2.4|2.5|2.6|2.7' | sha256sum
# 55d35b501c1a5775b00fe77c00e7195ebe4d0b1b513ec0948d60df9cba239346  -
```

## Sharing between assignments

When `ccdb add` (or `create_assignment` in the Python API) stores data, CCDB looks for a set of the
same table with the same hash, compares the bytes and, when they are equal, gives the new assignment
that set. Otherwise it stores a new set. The assignment keeps its own run range, variation, time,
author and comment, so sharing changes nothing a request returns.

`ccdb cp` copies an assignment to another run range or variation; the copy always shares the set of
its source.

A stored set never changes: new data is a new assignment. The Python API raises
`ConstantSetIsImmutableError` when code sets a different text on a stored set.

### `vers -l` output

`ccdb vers` lists the assignments of a table, as in CCDB 2.4. The `-l` flag adds two columns: `(data)`,
the first 12 hex digits of the set's SHA-256, and `(shared)`, the number of assignments that use the
set.

In this example, assignment 4 of the sample data that `ccdb db init` creates holds the six values above. Adding a file with the
same values for runs 100 to 200 makes assignment 6, which shares the set of assignment 4:

```
$ cat same_as_4.txt
2.2 2.3 2.4
2.5 2.6 2.7
$ ccdb add /test/test_vars/test_table -v default -r 100-200 same_as_4.txt '#Same values as assignment 4'
/test/test_vars/test_table:100:default:2026-11-01_14-44-26
$ ccdb vers -l /test/test_vars/test_table
(ID)     (created)              (user)           (variation)     (run range)      (data)        (shared)  (comments)
 6       2026-11-01 14-44-26    test_user        default         100-200         55d35b501c1a  2         Same values as assig
 5       2012-10-30 23-48-43    test_user        subtest         0-inf           b2ceb52d6aa9  1         Test assignment for
 4       2012-10-30 23-48-42    test_user        default         0-inf           55d35b501c1a  2         Test assignment for
 2       2012-08-30 23-48-42    test_user        test            500-3000        9c6697ea9cda  1         Test assignment for
 1       2012-07-30 23-48-42    test_user        default         0-inf           b62adcd1b563  1         Test assignment for
$ ccdb db stats
Num assignments: 6
Num constant sets: 5
Num shared constant sets: 1
```

The log record of an assignment that reuses a set ends with `(shared data)` (the command-line tool writes no log records to a SQLite file). The same `add` on a
MariaDB test database:

```
$ ccdb log
(action)        (author)         (date)                 (description)
 ...
 create         test_user        2026-11-01 15-44-11    Created assignment '/test/test_vars/test_table:100:default:2026-11-01_15-44-11' (shared data)
```

The record also names the set: its `affectedIds` column in the `logs` table holds
`|assignments6|constantSets4|`.

## Equal numbers in different text

CCDB compares the stored text. `1.0` and `1.00` are equal numbers and different texts, so they are
two sets:

```
$ cat gain_1.0.txt
1.0
$ cat gain_1.00.txt
1.00
$ ccdb mktbl /test/gain -r 1 gain=double '#Gain of one channel'
saving table to database...  completed
$ ccdb add /test/gain -r 0- gain_1.0.txt '#Written as 1.0'
Max run bound was set as INFINITE_RUN by default.
/test/gain:0:default:2026-11-01_14-44-27
$ ccdb add /test/gain -r 0- gain_1.00.txt '#Written as 1.00'
Max run bound was set as INFINITE_RUN by default.
/test/gain:0:default:2026-11-01_14-44-27
$ ccdb vers -l /test/gain
(ID)     (created)              (user)           (variation)     (run range)      (data)        (shared)  (comments)
 8       2026-11-01 14-44-27    test_user        default         0-inf           cf9dcf6da8a8  1         Written as 1.00
 7       2026-11-01 14-44-27    test_user        default         0-inf           d0ff5974b6aa  1         Written as 1.0
```

CCDB compares bytes because a request returns the stored text character for character: if `1.0` and
`1.00` shared one set, one of the two assignments would return other text than was added. Comparing
numbers would also need each column's type and a rule for every way to write a number (`0`, `0.0`,
`0.`, `1e0`); comparing bytes needs neither. On a copy of the GlueX database, 1 379 sets differ from
another set of their table only in how the numbers are written, and they stay separate sets.

Text from `ccdb add` is stored as the file writes it. The Python API stores a Python number as Python
prints it, so the float `1.00` becomes `1.0`.

## Shared data in the web GUI

An assignment page shows the SHA-256 and the size of its data and links the other assignments that use the same constant set under **Same data as**. A table's list of assignments marks a row whose data is shared with ×N, the number of assignments that use it.

## Hash collisions

Two different texts with the same SHA-256 have never been found. If a table holds a set with the
hash of new data but other bytes, `ccdb add` stops with `DataCollisionError`, writes nothing and logs
an error line that names the sets:

```
Data collision in table '<path>': constant set(s) <ids> have sha256 <hash> but other bytes than the new data. Nothing was written
```

Such a collision means corrupt data or a broken hash function. Check the named sets with
`ccdb db rehash` (see [Upgrading to CCDB 2.5](deployment/upgrade-2.5.md#verifying-stored-hashes)).

## Deleting assignments and tables

- `ccdb rm -a <id>` deletes an assignment, and its set when no other assignment uses it, as CCDB 2.4
  does. A set that other assignments share stays.
- `ccdb rm <table>` deletes a table only when it has no assignments, and deletes the table's unused
  sets with it.
- `ccdb db dedup` removes unused sets that older versions left behind; see
  [Upgrading to CCDB 2.5](deployment/upgrade-2.5.md#merging-duplicate-sets).

In the example above, deleting assignment 6 keeps its set, which assignment 4 still uses. Deleting
assignments 7 and 8 deletes their sets, and then the table can go:

```
$ ccdb rm -f -a 6
$ ccdb db stats
Num assignments: 7
Num constant sets: 7
Num shared constant sets: 0
$ ccdb rm -f -a 7
$ ccdb rm -f /test/gain
Can't delete type table that has data assigned to it. The type table '/test/gain' with id '3' has 1 assignments. Please, delete the assignments first
$ ccdb rm -f -a 8
$ ccdb rm -f /test/gain
$ ccdb db stats
Num assignments: 5
Num constant sets: 5
Num shared constant sets: 0
```

`rm` prints the warning `CCDB is no-delete storage by design!` before each of these lines; the listing
leaves it out. The refused `rm` exits with 1.

## Databases upgraded from CCDB 2.4

CCDB 2.4 stored a new set for every assignment, so an upgraded database holds byte-identical sets in
many tables. On a copy of the GlueX database, 235 645 of its 821 431 sets (28.7 %) repeated the bytes of
another set of their table. Until `ccdb db dedup --dedup-i-am-sure`
merges them, `ccdb add` reuses the oldest of equal sets, the same set dedup keeps. The
[upgrade guide](deployment/upgrade-2.5.md) describes the procedure.
