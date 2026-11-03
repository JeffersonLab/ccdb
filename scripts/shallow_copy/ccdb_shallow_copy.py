#!/usr/bin/env python3
"""
Shallow copy of a CCDB database: only the constants that a run period, a point in time and a set
of variations need.

The copy answers a lookup the same way the source does when the lookup asks for a copied variation,
a run inside the period, and no time or a time at or after --time. A lookup for a run outside the
period, or for a variation that was not copied, fails with "no assignment" instead of returning
constants the source would not return.

What the copy holds:
  - schema version, users, directories, tables and their columns: all of them.
    Passwords are blanked unless --copy-passwords is given.
  - variations: the listed ones and all their parents.
  - assignments: for every table, listed variation and run of the period, the one that
    AlchemyProvider.get_assignment returns: the highest assignment id created at or before --time,
    falling back to the parent variation while a variation has none. Their constant sets are copied whole,
    each once: in CCDB schema 6 assignments of one table may share a set.
  - run ranges: clipped to the period. A range that lies inside the period keeps its row; any other
    range gets a new clipped row, so lookups outside the period find nothing.
  - one log record with the copy parameters. Logs, tags and event ranges are not copied.
  - every column of the source; a column the target schema lacks is added to it.

--full copies every row of every table instead (users' passwords are still blanked by default). The schema 5
link table (variationsToTags, or variations_has_tags on SQLite and hallddb) is copied only when the source and the
target have it; a fresh schema 6 target does not.

Source and target are CCDB schema 6. The target gets the unique index of constantSets (constantTypeId, sha256)
after the rows are in; a source upgraded from schema 5 that still holds duplicate sets gives the target the
interim index ix_constantSets_table_sha256 instead, as `ccdb db upgrade` does.
--per-run selects assignments with one get_assignment call per table, variation and run: the
reference method, slow on real databases, used to check the default one.

Examples:
  ccdb_shallow_copy.py mysql://ccdb_user@hallddb.jlab.org/ccdb sqlite:///ccdb_140k.sqlite \\
      --run-min 140000 --run-max 140901 --variations default,mc
  ccdb_shallow_copy.py mysql://ccdb_user@hallddb.jlab.org/ccdb sqlite:///ccdb_full.sqlite --full
"""

import argparse
import json
import logging
import sys

# The library lives in the package (ccdb.snapshot), so the HTTP API builds its run bundles with the same code;
# this script is its command line and keeps the names the tests and verify_shallow_copy.py use.
from ccdb.snapshot import (CopyError, INTERIM_INDEX, UNIQUE_INDEX, as_datetime, claim_runs, full_copy, hide_password,
                           lookup, open_engine, prepare_target, shallow_copy, table_paths)
from ccdb.path_utils import parse_time

__all__ = ["CopyError", "INTERIM_INDEX", "UNIQUE_INDEX", "as_datetime", "claim_runs", "full_copy", "hide_password", "lookup",
           "open_engine", "prepare_target", "shallow_copy", "table_paths", "main"]

log = logging.getLogger("ccdb_shallow_copy")


def parse_arguments(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0].strip(),
                                     epilog=__doc__.split("\n\n", 1)[1], formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("source", help="source connection string, e.g. mysql://ccdb_user@hallddb.jlab.org/ccdb")
    parser.add_argument("target", help="target connection string, e.g. sqlite:///ccdb_shallow.sqlite (an empty database)")
    parser.add_argument("--run-min", type=int, help="first run of the period")
    parser.add_argument("--run-max", type=int, help="last run of the period (default: --run-min)")
    parser.add_argument("--time", help="constants created at or before this time, CCDB format (2017-11-16_10-03-20); default: latest")
    parser.add_argument("--variations", default="default", help="comma separated variation names, or '*' for all (default: default)")
    parser.add_argument("--full", action="store_true", help="copy every row of every table instead")
    parser.add_argument("--per-run", action="store_true", help="select with one get_assignment call per table, variation and run (reference method)")
    parser.add_argument("--copy-passwords", action="store_true", help="copy users' passwords (blanked by default)")
    parser.add_argument("--overwrite", action="store_true", help="replace an existing SQLite target file")
    parser.add_argument("--time-limit", type=float, help="stop after this many seconds and report where (the copy is then incomplete)")
    parser.add_argument("--report-json", help="write the report to this file")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)
    if not args.full and args.run_min is None:
        parser.error("--run-min is required (or --full)")
    if args.run_max is None:
        args.run_max = args.run_min
    return args


def main(argv=None):
    args = parse_arguments(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(asctime)s %(message)s", stream=sys.stderr)
    try:
        if args.full:
            report = full_copy(args.source, args.target, args.overwrite, args.copy_passwords)
        else:
            variations = [name.strip() for name in args.variations.split(",") if name.strip()]
            max_time = parse_time(args.time) if args.time else None
            report = shallow_copy(args.source, args.target, args.run_min, args.run_max, variations, max_time,
                                  args.overwrite, args.per_run, args.copy_passwords, args.time_limit)
    except CopyError as error:
        log.error("%s", error)
        return 2

    text_report = json.dumps(report, indent=2, default=str)
    if args.report_json:
        with open(args.report_json, "w") as report_file:
            report_file.write(text_report + "\n")
    print(text_report)
    if not report.get("complete", True):
        log.error("Time limit reached at %s; the copy is incomplete", report["stopped_at"])
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
