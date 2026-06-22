# Concepts illustrated

## Introduction

Let's take a simple example of calibration data, say "target position," which is defined by three
coordinates x, y, z, each represented by a floating point number.

Using C++ as an example language, if a user asks for "target position":

```cpp
auto data = calibration->GetCalib("/target/position");
```

the calibration database should provide the appropriate data in the current context so it can be
used:

```cpp
if (data["z"] > 30) ...
```

"The **current context**" is the key phrase here, since the values of target position could be
different for different runs, values may change with time (e.g. if more precise calibration is
performed), and a user may want to use a personal version of the data for various reasons.

![Target position sample](../images/target_position_sample.png)

The picture above illustrates features of CCDB that involve control of the context:

- The data returned depends on the run number.
- A history mechanism: by default CCDB honors the last assignment of data to a particular run, but one
  can always recover assignments made in the past.
- Variations (equivalent to "branches" in version control systems): users have the ability to create
  and work with alternative versions of the data, varying the run assignments and/or the data itself.

## Concepts

![Target position naming](../images/target_position_naming.png)

### Namepath

Data is associated by the namepath. The namepath string is unique across all detector systems. A
forward slash (`/`) is used to specify a hierarchical namepath.

For example:

```
/target/position
/FDC/driftvelocity/timewalk_parameters
/FDC/base_time_offset
```

This allows implementors of individual detector systems to specify a hierarchy with as much or as
little depth as is needed, appropriate to the physical structure of their device.

**Namepath format:** Allowed symbols are `a-z`, `A-Z`, `0-9`, `_` and `-`. Spaces or other special
symbols are not allowed in the namepath (this simplifies console management and database validation of
namepath objects).

```
/My-path/to/data_01           # OK
/Some...thing/is wrong here!   # ERROR: illegal symbols '...', '!' and spaces.
```

### Table types

Each namepath corresponds to a "table type". A **table type** defines columns and a number of rows.
The idea behind a "type table" is that while data values may change, "the shape" of the table never
does.

> The term "table" is ambiguous when talking about data, and it is especially ambiguous when the topic
> is related to databases. Thus CCDB uses the term "**table type**" for a definition of data (the
> shape), and "**data set**" or "**constant set**" for the data itself, i.e. the values of a table
> type.

In the target-position example, the namepath `/target/position` is a table type, defining data
arranged in three columns of type "float" and one row. Whatever the values of `/target/position` are,
they are always presented as one row of "x", "y", "z".

#### Columns

Each column has a type and may have a name. However, column names are optional.

The `/target/position` example has 3 columns named "x", "y", and "z". They could also be identified as
0, 1, 2.

As another example, the `/FDC/driftvelocity/timewalk_parameters` parameters may have members "slope",
"offset", and "exponent".

By contrast, a set of constants with the namepath `/FDC/CathodeStrips/pedestals` may have 100 values
identified simply as 0, 1, 2, 3, ...

**Column types** may be one of the following:

- int
- uint
- long
- ulong
- bool
- double
- string

### Constant sets and assignments

Each table type may have multiple versions of constant sets, i.e. the data. Each constant set has at
least one "assignment". The assignment holds the information specifying the association of the
constant set with a context:

- **run range** — runs for which the data is valid
- **creation time** — creation time of the assignment (used for the history feature)
- **variation** — name of the variation
- **comment** — any useful comments about the assignment

One could say that an assignment shows the context within which the data "is correct". One could also
say that while a constant set is data, an associated assignment is a header for this data.

A particular constant set can have several assignments. This allows the same constants to be used for
different run ranges and helps avoid "update anomalies".

![Target position assignments](../images/target_position_assignments.png)

To summarize all of the above concepts: one namepath may have several versions of data (constant
sets); each such constant set is connected to one or more assignments. These assignments hold
information about the right context (run number, variation, date) for each constant set.

### Requests

There are two use cases:

1. In general, getting constants should be as easy as saying "Give me /target/position for June 2011".
2. Sometimes you need a way to name (and get) a particular set of constants. This means there should
   be a unique key for every set of data.

CCDB uses so-called "Requests" to solve both problems. The full form of a request is a "unique
composite key" for the particular data values. The full form of the request is:

```
</path/to/data>:<run>:<variation>:<time>
```

But to get the data the user can specify only a part of the request. The minimal request to get the
data is just `/path/to/data`.

One may omit any part of the request except the namepath:

- `/path/to/data` — just the path to data, no run, variation, or timestamp specified
- `/path/to/data::mc` — no run specified, variation is "mc", no date specified
- `/path/to/data:::2029` — only path and date (year) are specified

So, for example, to specify path and variation but use the default run, skip the run number and leave
its place like `::`:

```
                   +-- variation
                   |
   /path/to/data::mc
                |
                +-- place where run number should be
```

And the request:

```
/path/to/data:::2029
```

means that the path and the date are specified but the run number and variation should be deduced. See
the next section, [Default values](#default-values).

The time is parsed as:

```
YYYY:MM:DD-hh:mm:ss
```

Any non-digit character may be used as a separator instead of `:` and `-`, so all these time strings
are the same:

```
2029/06/17-22:03:05
2029-06-17-22-03-05
2029/06/17:22/03/05
2029a06b17c22d03e05
```

One can omit any part of the time from the right. In this case the latest date for the omitted part is
returned. For example:

- `2011` — (Year 2011, everything else omitted) is interpreted as `2011/12/31-23:59:59`, so the latest
  constants for the year 2011 are returned.
- `2012/05/21` — interpreted as `2012/05/21-23:59:59`, the latest constants for 21 May 2012.

CCDB searches for the latest constants.

> **WARNING** — Don't use requests (instead of a simple namepath) in C++ or Java *production* code.
> Use them to manage constants or for debugging. See the next section!

### Default values

There are two general cases of CCDB usage:

1. Reading out constants in physics analysis (or similar).
2. Managing constants with the ccdb console or Python.

In the case of physics analysis, most probably the software provides the number of the run being
processed and allows setting parameters like a variation name through command line arguments or
environment variables.

**JANA framework example:**

```bash
export JANA_CALIB_CONTEXT="variation=mc"
hd_root data_for_run_5000.evio
```

Now JANA knows that the preferred variation is "mc" and the run number = 5000 is obtained from the
data file. Thus when constants are requested by namepaths "the right context" is deduced:

```cpp
auto data = ccdb->GetCalib("/target/position");
// The latest data for run=5000 and variation=mc is selected
```

CCDB defaults and priorities (highest first):

1. Run number, variation, or date specified in a request.
   > If the `/path/to/data:100` request is used, constants for run 100 are returned even if another
   > run is actually being processed.
2. Run number, variation, or date provided by outer software.
   > If run 10200 is being processed and `GetCalib("/path/to/data")` is called, data for run 10200 is
   > returned.
3. If it is not possible to deduce values:
   - run number 0
   - variation "default"
   - current time

**Example. ccdb command:**

```
sh> ccdb -r 100 -i            # interactive mode, run 100
ccdb> cat /path/to/data       # commands get constants for run 100
ccdb> cat /path/to/data:333   # constants for run 333 are returned
                              # because request run has higher priority

sh> ccdb cat /path/to/data    # constants for run 0 are returned
                              # no other run is given
```

Sometimes it is vital to get particular data for **debugging** purposes. Requests are to be used in
this case. Don't forget to remove everything besides a namepath **after** debugging, because
**production** physics analysis code should **never** use requests — run, variation, and time given in
requests override values provided by the software framework.

```cpp
ccdb->GetCalib("/my/data");                 // Good. Use only namepaths in production
ccdb->GetCalib("/my/data:333::2017-04");    // Danger! Use only to DEBUG,
                                            // remove ':333::2017-04' after!!!
```

## Connection strings

In order to connect to a data source, CCDB uses so-called `connection strings`. The connection
strings have the same form for all APIs and the `ccdb` CLI tool. The general form is:

```
dialect://username:password@host:port/database
```

For MySQL and SQLite databases the connection strings are:

```
mysql://user_name:password@host:port/database
sqlite:///path_to_file
```

> **(!)** Note that because SQLite doesn't have a user name and password, it starts with 3 (three)
> slashes `///`. Thus there are 4 (four) slashes `////` in an absolute path to a file:
>
> ```
> sqlite:////home/user/example.db
> ```
