# CLI command coherence audit (proposal)

Status: analysis / proposal only, 2026-07. No command changes implemented.
Companion to [cli-modernization.md](cli-modernization.md); both
land naturally with the eventual click port.

## Current command surface

23 commands registered from `python/ccdb/cmd/commands/`:

| Command | Description | Notes |
|---|---|---|
| `add` | Add data constants | |
| `cat` | Show assignment data by ID | |
| `cd` | Change current directory | interactive-shell only concept |
| `cp` | Copy assignment | |
| `db` | Database info & management (`init`, `upgrade`, `stats`) | only command with subcommands |
| `dump` | Dumps data table | alias that rewrites itself to `cat --no-borders ...` |
| `edit` | Edit a value in the table | |
| `empty` | "empty utility example" | scaffolding template, shipped to users |
| `gui` | Starts local web GUI | |
| `horse` | "Horse" | joke command (ASCII horse), shipped to users |
| `howto` | Prints howtos | overlaps `help` |
| `info` | Extended info of object by path | |
| `log` | Shows log records | |
| `ls` | List objects in a directory | |
| `mkdir` | Create directory | |
| `mktbl` | Create constants type table | |
| `mkvar` | Create variation | |
| `pwd` | Prints working directory | interactive-shell only concept |
| `rm` | Removes directory / table / variation / assignment | flag-driven type dispatch |
| `run` | gets or sets current working run | state setter, useful mostly in `-i` shell |
| `user` | Manage users | |
| `var` | gets or sets current working variation | state setter, mostly `-i` shell |
| `vers` | Show versions of data for a table | |

## Incoherence findings

1. **Two naming families mixed.** Unix-filesystem metaphor (`ls`, `cd`, `pwd`,
   `mkdir`, `rm`, `cat`, `cp`) coexists with abbreviated make-commands
   (`mktbl`, `mkvar`) and plain words (`add`, `dump`, `info`, `vers`). A new
   user cannot predict whether creating X is `mkX`, `make X`, or `add X`.

2. **One `rm` deletes four object kinds** (directory `-d`, variation `-v`,
   table by default, assignment by id) via flags, while *creation* of the same
   four kinds is spread over four commands (`mkdir`, `mktbl`, `mkvar`, `add`).
   Create and delete are asymmetric.

3. **Overlaps.** `dump` is literally an alias to `cat` with flags; `howto`
   overlaps `help`; `info` vs `ls <table>` vs `vers` all answer "tell me about
   this table" at different depths (`ls` even silently rewrites itself into
   `vers`/`info` when given a single table path — surprising alias behavior).

4. **Interactive-shell state leaks into one-shot mode.** `cd`, `pwd`, `run`,
   `var` exist for the `ccdb -i` shell; in one-shot mode `cd`/`pwd` are no-ops
   of no value, but they still appear as top-level commands.

5. **Junk in the public surface.** `horse` (joke) and `empty` (a template for
   writing new commands) are registered and listed in `ccdb help`.

6. **Return-value chaos** (found while building CI smoke tests): commands
   variously return `True`, `0`-as-success, an SQLAlchemy object, a
   next-command string (alias mechanism), or `None` — and the console maps
   `None` to exit code 1, so several commands "succeeded with exit 1" for
   years (`ls`, `mkdir`, `mkvar`, `help` — fixed in passing; others may lurk).

7. **Global flags are hand-parsed** (`--version`, `--debug`, `--no-color`,
   `--raise` scattered over `sys.argv` checks in `ccdb/__init__.py` plus a
   second hand-rolled parse loop in `cli_manager.process`), so `ccdb --help`
   and `ccdb help` are different code paths.

## Comparison with rcdb

rcdb (click-based) groups by noun: `rcdb db init`, `rcdb add type`,
`rcdb add condition`, `rcdb file ls|cat|vers`, `rcdb select`, `rcdb info`,
`rcdb ls`. One spelling for "create" (`add <noun>`), subcommand groups instead
of flag dispatch, and click generates `--help` uniformly. ccdb's `db` command
(`db init --init-i-am-sure`) is already this shape — it is the model to extend.

## Proposed coherent command map (for the click port)

Keep the filesystem metaphor for *navigation/reading* (it fits CCDB's
path-addressed data and is muscle memory for existing users), group
*creation/deletion* by noun, and demote shell-state commands:

```
ccdb ls [path]              # list (no silent aliasing into vers/info)
ccdb info <path>            # table/dir/variation details (absorbs ls's alias trick)
ccdb cat <path|id>          # show data (absorbs dump as `cat --dump` or a --format flag)
ccdb vers <path>            # assignment history of a table
ccdb log                    # log records

ccdb add data <path> <file> # today's `add`
ccdb add table <path> ...   # today's `mktbl`
ccdb add dir <path>         # today's `mkdir`
ccdb add variation <name>   # today's `mkvar`

ccdb rm table|dir|variation|assignment <target>   # explicit noun, mirrors add

ccdb cp <assignment>        # copy assignment
ccdb edit <path> ...        # edit value

ccdb db init|upgrade|stats  # unchanged (rename --init-i-am-sure -> --confirm, rcdb-style)
ccdb user ...               # unchanged
ccdb gui                    # unchanged

ccdb -i                     # interactive shell keeps cd/pwd/run/var as *shell builtins*,
                            # they disappear from the one-shot command list
```

Dropped from the public surface: `horse`, `empty` (move to a developer howto),
`howto` (merge into `help`/docs). Old spellings (`mktbl`, `mkvar`, `mkdir`,
`dump`) survive one major version as hidden click aliases that print a
one-line deprecation pointer, since GlueX/Hall-D scripts call them.

Uniform contract to adopt with the port: every command returns exit 0 on
success and non-zero on failure (never "object or None"), and click owns all
global flags so `ccdb --help`, `ccdb help` and `ccdb <cmd> --help` agree.

## Suggested sequencing

1. Output layer first (see cli-modernization.md, phase 1) — behavior-preserving.
2. Click port with the map above, old names as deprecated aliases.
3. Remove aliases in the next major version.
