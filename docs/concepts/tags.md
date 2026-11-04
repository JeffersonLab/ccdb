# Tags

A tag is a named snapshot of one variation at one moment. A request with a tag returns the constants
that the variation held at that moment, whatever was added later. Use a tag to name the calibration
of a data production, a paper or a software release, and to reproduce it years later.

A tag stores:

- a name, unique in the database, of letters, digits and `_`, at most 100 characters;
- a variation, `default` unless you give another one;
- a time, stored as a UTC instant;
- a comment, the author and the creation time.

A tag copies no data. It is a pointer into the history that CCDB keeps.

## Snapshot model

A git tag names one commit: `git checkout v1.0` shows the files as they were in that commit, and later
commits do not change what `v1.0` shows. A CCDB tag works the same way for constants. CCDB keeps every
assignment, so the history of a variation is complete, and a tag names a point in that history. The
request `/path/to/data:1500@Run2026` returns what `/path/to/data:1500:<variation of the tag>` returned at
the tag's moment.

The difference: a git tag points at a commit, and a CCDB tag points at a time. Two tags with the same
variation and the same time return the same constants.

## What a tag freezes

A tag fixes two parts of a request:

- **The variation.** The request uses the tag's variation, with the usual fallback to its parent
  variations.
- **The time.** The request sees only assignments created at or before the tag's instant.
  Assignments added later are ignored, even for the same run range.

You still give the table, and the run as in any request. A request with a tag resolves like
`/path/to/data:<run>:<variation>:<time>` with the tag's variation and time filled in.

## What a tag does not freeze

- **The run.** The run comes from the request, so one tag serves every run.
- **The data itself.** Nothing is copied. If an assignment the tag sees is removed with
  `rm -a ID -f`, requests with the tag resolve to the next older matching assignment.
- **New work.** You can add assignments to the tagged variation after the tag. The tag ignores them;
  requests without the tag see them.
- **The structure.** Directories, tables and variations created, deprecated or removed after the tag
  are not tracked. [Deprecation](concepts/deprecation.md) never changes what a request returns, with or
  without a tag.

## Tag time

- Without `-t`, `ccdb tag` stores the current time.
- `-t TIME` takes a time in your local time zone, in the request time format
  (`YYYY:MM:DD-hh:mm:ss.ffffff`, see [Time](concepts/time.md)). CCDB converts it to UTC. A partial time is
  the latest moment it covers: `-t 2026-03-01-12-00-00` is 12:00:00.999999.
- A time in the future is refused. A tag describes history that already exists.

The tag stores a UTC instant with microseconds, and assignment creation times are UTC instants with
microseconds too, on MySQL, MariaDB and SQLite. A request with a tag and the `rm -a` pin check compare
them exactly, wherever the client runs. Creation times written by CCDB 2.4 or earlier from a client in
another time zone than the server keep that zone difference.

## Tags in requests

The request part `@NAME` names a tag:

```
/path/to/data:1500@Run2026
```

| request | meaning |
|---|---|
| `/path/to/data:1500@Run2026` | run 1500, with the variation and the time of tag `Run2026` |
| `/path/to/data@Run2026` | no run given: the run resolves as in a request without a tag |
| `/path/to/data:1500:mc@Run2026` | error: the tag already sets the variation |
| `/path/to/data:1500::2026@Run2026` | error: the tag already sets the time |

A request with a tag and a variation, or a tag and a time, is an error in Python and in C++:

```
$ ccdb cat /test/test_vars/test_table:1500:mc@Run2026
A request with a tag can have neither a variation nor a time: '/test/test_vars/test_table:1500:mc@Run2026'
```

The error prevents a request that looks pinned from returning something the tag does not describe.

`cat`, `dump`, `vers` and `info` accept a request with a tag. `vers` with a tag lists the versions the tag sees: those of the tag's variation and of its parents up to `default`, created at or before the tag's time.

## No deletion of tagged history

CCDB treats the database as a logbook: a new assignment supersedes the old one, and the old one stays.
Tags depend on this. A tag made in 2026 resolves correctly in 2030 only if the assignments it sees
still exist.

`rm -a` checks this. It refuses to delete an assignment when a tag pins it: a tag whose variation is
the assignment's variation, or inherits from it, and whose time is at or after the assignment's
creation. To delete such an assignment anyway, add `-f` (`--force`); it also skips the confirmation prompt.
Requests with that tag then resolve to the next older matching assignment.

`ccdb tag rm NAME` removes a tag and writes a log record. The constants stay.

## Examples

To create a tag of the `default` variation at the current time:

```
$ ccdb tag Run2026 -c "Calibration of the 2026 production"
Tag 'Run2026' is created
```

To create a tag of the `mc` variation at a past time:

```
$ ccdb tag mc_2025_10 -v mc -t 2025:10:31-23:59:59 -c "MC constants as of October 2025"
Tag 'mc_2025_10' is created
```

To list the tags:

```
$ ccdb tag
(name)                (variation)      (time UTC)            (comment)
 Run2026               default          2026-11-01 23:35:54   Calibration of the 2026 production
 mc_2025_10            mc               2025-11-01 03:59:59   MC constants as of October 2025
```

The `-t` time `2025:10:31-23:59:59` in New York local time is `2025-11-01 03:59:59` UTC.

To show one tag:

```
$ ccdb tag Run2026
 Tag        :  Run2026
 Variation  :  default
 Time (UTC) :  2026-11-01 23:35:54
 Time (loc) :  2026-11-01 18:35:54
 DB Id      :  1
 Comment    :  Calibration of the 2026 production
```

A time in the future is refused:

```
$ ccdb tag x2 -t 2030:01:01 -c x
Cannot create tag 'x2' at 2030-01-02 04:59:59 UTC: the time is in the future
```

To read constants through a tag:

```
$ ccdb cat /test/test_vars/test_table:1500@Run2026
+--------------------------------------+
| x          | y          | z          |
| double     | double     | double     |
+--------------------------------------+
| 2.2        | 2.3        | 2.4        |
| 2.5        | 2.6        | 2.7        |
+--------------------------------------+
```

To see which assignments a tag sees:

```
$ ccdb vers /test/test_vars/test_table@Run2026
For variation: default (tag 'Run2026' at 2026-11-01 23:35:54 UTC)
(ID)     (created)              (user)           (variation)     (run range)      (comments)
 4       2012-10-30 23-48-42    test_user        default         0-inf           Test assignment for
 1       2012-07-30 23-48-42    test_user        default         0-inf           Test assignment for
```

`rm -a` asks for confirmation, then refuses an assignment that a tag pins. Tag `mc_2025_10` pins
assignment 1 of `default`, because `mc` inherits from `default`:

```
$ ccdb rm -a 1
...
To confirm delete type 'yes': yes
Assignment 1 may be the data of tag(s) 'Run2026', 'mc_2025_10'. Use force to delete it anyway
```

To delete the assignment anyway, without the prompt:

```
$ ccdb rm -a 1 -f
```

To remove a tag:

```
$ ccdb tag rm Run2026
Tag 'Run2026' is removed
```

See [Command line (CLI)](cli.md#tags) for the options of `ccdb tag`.

## Tag properties

A tag names the constants of a pass. Its [properties](cli.md#properties) name the rest of the pass, so the
tag alone answers "what produced this data": the software version, the container image, the input data,
the identifier of the output and the DOI of the deposited constants. A property command names a tag as a
request does, with `@NAME`:

```
$ ccdb prop set @Run2026 software halld_recon-5.14.0
$ ccdb prop set @Run2026 container "docker://jeffersonlab/halld_recon:5.14.0"
$ ccdb prop set @Run2026 data "RunPeriod-2026-01 recon ver03"
$ ccdb prop ls @Run2026
container = docker://jeffersonlab/halld_recon:5.14.0
data = RunPeriod-2026-01 recon ver03
software = halld_recon-5.14.0
```

The standard names for a tag are `description`, `software`, `container`, `data`, `rucio_did`, `doi` and
`citation`. `ccdb tag NAME`, `ccdb tag -l`, `ccdb info @NAME`, `/api/v1/tags/NAME`, the MCP tool `list_tags`
and the tag's page in the web GUI show them. Each change writes a log record; `ccdb tag rm` removes the
tag's properties with it.

## Publishing a tag

To cite constants in a paper, deposit a tag in a repository and record its DOI:

1. `ccdb export tag @Run2026 -o deposit/` writes `Run2026.sqlite` (the constants the tag gives for every
   run, with the tag and the descriptions of the tables inside), `Run2026.sha256` and
   `Run2026.datacite.json`, a DataCite metadata record built from the instance properties (`experiment`,
   `contact`, `license`, `url`, `citation`) and the tag's ([CLI](cli.md#export-of-a-tag)).
2. Upload the three files to Zenodo or an institutional repository. The metadata record holds what the
   deposit form asks for. CCDB makes no network call.
3. `ccdb prop set @Run2026 doi 10.5281/zenodo.1234567`. A later export of the same tag names that DOI as the
   version it replaces.

The deposited file opens with `sqlite:////path/Run2026.sqlite` in Python and C++, and a request
`/path:run@Run2026` gives in it what it gives in the experiment's database, so a reader of the paper
reproduces every constant the analysis used without access to that database.

## Tags in the web GUI

- **Tags** in the sidebar lists every tag with its variation, time (UTC) and comment.
- A tag's page lists its properties, takes a run number and shows, for every table, what `table:run@NAME` returns: the variation the constants come from and when they were added, as a link to them.
- The Request page has a tag selector that builds `/path/table:run@NAME`.
- An assignment page opened with `@NAME` in its request string shows the assignment the tag gives and the request it was resolved from.
