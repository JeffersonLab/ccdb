#!/usr/bin/env python3
"""
Checks a shallow copy against its source with one AlchemyProvider.get_assignment call per table,
variation and run on each database.

For every table, listed variation and run of the period, the copy must return the same assignment
id as the source, and every returned assignment must carry the same constants. Lookups for the run
just before and just after the period must find nothing in the copy.

Pass the same --run-min, --run-max, --time and --variations as to ccdb_shallow_copy.py. Tables are
split between worker processes; --time-limit stops the check and reports how far it got.

Example:
  verify_shallow_copy.py sqlite:///ccdb_full.sqlite sqlite:///ccdb_140k.sqlite \\
      --run-min 140000 --run-max 140901 --variations default,mc --workers 8
"""

import argparse
import json
import multiprocessing
import os
import sys
import time

from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ccdb_shallow_copy as shallow  # noqa: E402

from ccdb.model import INFINITE_RUN, TypeTable  # noqa: E402
from ccdb.path_utils import parse_time  # noqa: E402
from ccdb.provider import AlchemyProvider  # noqa: E402

# Mismatches kept in the report; the count covers all of them
MAX_REPORTED_MISMATCHES = 50

# Set in every worker process by start_worker()
worker = {}


def open_provider(connection_string):
    engine = shallow.open_engine(connection_string)
    provider = AlchemyProvider()
    provider.attach(engine, sessionmaker(bind=engine)())
    return provider


def start_worker(source_url, copy_url, settings):
    worker["source"] = open_provider(source_url)
    worker["copy"] = open_provider(copy_url)
    worker.update(settings)


def check_table(table_id):
    """Compares one table on both databases. Returns a result dict for this table."""
    source, copy = worker["source"], worker["copy"]
    run_min, run_max, max_time = worker["run_min"], worker["run_max"], worker["max_time"]
    result = {"table_id": table_id, "lookups": 0, "found": 0, "mismatches": [], "complete": True, "stopped_at_run": None}
    source_table = source.session.get(TypeTable, table_id)
    copy_table = copy.session.get(TypeTable, table_id)
    if copy_table is None:
        result["mismatches"].append({"table_id": table_id, "problem": "table missing in the copy"})
        return result

    checked_constants = set()
    for variation in worker["variations"]:
        for run in range(run_min, run_max + 1):
            if worker["deadline"] and time.monotonic() > worker["deadline"]:
                result["complete"] = False
                result["stopped_at_run"] = "{0} {1}".format(variation, run)
                return result
            expected = shallow.lookup(source, source_table, run, variation, max_time)
            actual = shallow.lookup(copy, copy_table, run, variation, max_time)
            result["lookups"] += 1
            expected_id = expected.id if expected else None
            actual_id = actual.id if actual else None
            if expected_id != actual_id:
                result["mismatches"].append({"table_id": table_id, "variation": variation, "run": run,
                                             "source_assignment": expected_id, "copy_assignment": actual_id})
                continue
            if expected is None:
                continue
            result["found"] += 1
            if expected_id not in checked_constants:
                checked_constants.add(expected_id)
                if expected.constant_set.vault != actual.constant_set.vault:
                    result["mismatches"].append({"table_id": table_id, "assignment": expected_id, "problem": "constants differ"})

        # Just outside the period the copy must find nothing
        for outside_run in (run_min - 1, run_max + 1):
            if 0 <= outside_run <= INFINITE_RUN:
                found = shallow.lookup(copy, copy_table, outside_run, variation, None)
                if found is not None:
                    result["mismatches"].append({"table_id": table_id, "variation": variation, "run": outside_run,
                                                 "problem": "copy finds assignment {0} outside the period".format(found.id)})
    return result


def verify(source_url, copy_url, run_min, run_max, variations, max_time=None, workers=1, time_limit=None, sample_tables=None):
    started = time.monotonic()
    with shallow.open_engine(copy_url).connect() as connection:
        table_ids = [row[0] for row in connection.execute(text("SELECT id FROM typeTables ORDER BY id"))]
    if sample_tables:
        step = max(1, len(table_ids) // sample_tables)
        table_ids = table_ids[::step][:sample_tables]
    if variations == ["*"]:
        with shallow.open_engine(copy_url).connect() as connection:
            variations = sorted(row[0] for row in connection.execute(text("SELECT name FROM variations")))

    settings = {"run_min": run_min, "run_max": run_max, "max_time": max_time, "variations": variations,
                "deadline": started + time_limit if time_limit else None}
    totals = {"tables_checked": 0, "tables_incomplete": 0, "lookups": 0, "found": 0, "mismatch_count": 0}
    mismatches = []
    incomplete = []
    with multiprocessing.Pool(workers, initializer=start_worker, initargs=(source_url, copy_url, settings)) as pool:
        for result in pool.imap_unordered(check_table, table_ids):
            totals["tables_checked"] += result["complete"]
            totals["lookups"] += result["lookups"]
            totals["found"] += result["found"]
            totals["mismatch_count"] += len(result["mismatches"])
            mismatches.extend(result["mismatches"][:MAX_REPORTED_MISMATCHES - len(mismatches)])
            if not result["complete"]:
                totals["tables_incomplete"] += 1
                incomplete.append((result["table_id"], result["stopped_at_run"]))

    paths = shallow.table_paths(shallow.open_engine(copy_url))
    for mismatch in mismatches:
        mismatch["table"] = paths.get(mismatch["table_id"])
    expected_lookups = len(table_ids) * len(variations) * (run_max - run_min + 1)
    report = {"source": shallow.hide_password(source_url), "copy": shallow.hide_password(copy_url),
              "run_min": run_min, "run_max": run_max, "variations": variations,
              "time": max_time.isoformat(sep=" ") if max_time else "latest", "workers": workers,
              "tables": len(table_ids), "expected_lookups": expected_lookups}
    report.update(totals)
    report["complete"] = totals["lookups"] == expected_lookups and not incomplete
    report["passed"] = report["complete"] and totals["mismatch_count"] == 0
    report["seconds"] = round(time.monotonic() - started, 1)
    report["lookups_per_second"] = round(totals["lookups"] / max(report["seconds"], 0.001))
    report["incomplete_tables"] = [{"table": paths.get(table_id), "stopped_at": where} for table_id, where in incomplete[:20]]
    report["mismatches"] = mismatches
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0].strip(), epilog=__doc__.split("\n\n", 1)[1],
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("source", help="connection string of the database the copy was made from")
    parser.add_argument("copy", help="connection string of the shallow copy")
    parser.add_argument("--run-min", type=int, required=True)
    parser.add_argument("--run-max", type=int, help="default: --run-min")
    parser.add_argument("--time", help="the --time given to the copy; default: latest")
    parser.add_argument("--variations", default="default", help="comma separated variation names, or '*'")
    parser.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 1) - 2), help="worker processes (default: cores - 2)")
    parser.add_argument("--time-limit", type=float, help="stop after this many seconds and report how far the check got")
    parser.add_argument("--sample-tables", type=int, help="check only this many tables, spread evenly over the table ids")
    parser.add_argument("--report-json", help="write the report to this file")
    args = parser.parse_args(argv)

    run_max = args.run_min if args.run_max is None else args.run_max
    variations = [name.strip() for name in args.variations.split(",") if name.strip()]
    max_time = parse_time(args.time) if args.time else None
    report = verify(args.source, args.copy, args.run_min, run_max, variations, max_time, args.workers, args.time_limit, args.sample_tables)
    text_report = json.dumps(report, indent=2, default=str)
    if args.report_json:
        with open(args.report_json, "w") as report_file:
            report_file.write(text_report + "\n")
    print(text_report)
    if not report["complete"]:
        return 3
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
