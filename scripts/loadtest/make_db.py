#!/usr/bin/env python3
"""A synthetic CCDB database shaped like a production one, for the load tests (docs/deployment/scaling.md).

    python scripts/loadtest/make_db.py sqlite:////tmp/loadtest.sqlite --manifest /tmp/loadtest.json
    python scripts/loadtest/make_db.py mysql://ccdb_user@127.0.0.1:33083/ccdb_loadtest --scale 0.05

The database is re-initialized. Its tables have the shapes of profile.json (make_profile.py; hallddb's by default):
rows and columns as surveyed, the number of assignments scaled by --scale (at 1.0 it is the full 3.2 GB of hallddb),
the mean size of a constant set as surveyed, and the surveyed share of byte-identical sets, which schema 6 stores
once and the new assignments point to. Every assignment covers a run range of 0..--runs-1; the first of each table
covers them all, so every table resolves for every run. Creation times spread over 2016-2025 in id order.

Deterministic: the same arguments give the same rows (--seed). The manifest lists the table paths with their shapes,
the run count and the campaign time (2026-01-01 00:00:00 UTC, after every assignment), for client.py.
"""
import argparse
import contextlib
import hashlib
import io
import json
import os
import random
import sys
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
FIRST = datetime(2016, 1, 1, tzinfo=timezone.utc)
LAST = datetime(2025, 12, 31, tzinfo=timezone.utc)
CAMPAIGN = datetime(2026, 1, 1, tzinfo=timezone.utc)
DIRECTORIES = 64                    # hallddb's directory count
DIGITS = bytes(ord("0") + value % 10 for value in range(256))


def load_profile(path=None):
    with open(path or os.path.join(HERE, "profile.json")) as stream:
        return json.load(stream)["tables"]


def plan(shapes, scale, seed, runs, tables=None):
    """The database to build, without data: a list of tables, each a dict with the shape, its assignments (run range,
    created time, set index) and its set count. Pure, so the tests check the distributions without a database.

    tables draws that many shapes from the profile (with replacement), else every shape once.
    """
    rng = random.Random(seed)
    chosen = list(shapes) if tables is None else [rng.choice(shapes) for _ in range(tables)]
    span = (LAST - FIRST).total_seconds()
    result = []
    for index, (rows, columns, sets, mean_bytes, redundant) in enumerate(chosen):
        count = max(1, round(sets * scale))
        shared = redundant / sets
        assignments, set_count = [], 0
        for number in range(count):
            if number == 0:
                run_min, run_max = 0, runs - 1
            else:
                length = max(1, int(runs * rng.random() ** 3))
                run_min = rng.randrange(0, runs - length + 1)
                run_max = run_min + length - 1
            if number > 0 and rng.random() < shared:
                set_index = rng.randrange(set_count)            # a byte-identical copy of an earlier set
            else:
                set_index = set_count
                set_count += 1
            created = FIRST + timedelta(microseconds=int(rng.random() * span * 1e6))
            assignments.append((run_min, run_max, created, set_index))
        result.append({"path": "/loadtest/d{0:02d}/t{1:04d}".format(index % DIRECTORIES, index),
                       "rows": rows, "columns": columns, "mean_set_bytes": mean_bytes, "sets": set_count,
                       "assignments": assignments})
    return result


def vault(rng, rows, columns, mean_bytes):
    """A data text of rows x columns numbers, cells of equal width, about mean_bytes long"""
    cells = rows * columns
    width = max(1, round((mean_bytes + 1) / cells) - 1)
    text = rng.randbytes(cells * width).translate(DIGITS).decode("ascii")
    return "|".join(text[start:start + width] for start in range(0, len(text), width))


def build(connection_string, scale=0.02, seed=2026, runs=100000, tables=None, profile=None):
    """Re-creates the database and fills it; returns the manifest"""
    sys.path.insert(0, os.path.join(REPO, "python"))
    from sqlalchemy import create_engine, select
    from ccdb import testing
    from ccdb.model import Assignment, ConstantSet, Directory, RunRange, TypeTable, TypeTableColumn, Variation
    from ccdb.sql.sqlite_schema import create_sqlite_database

    if connection_string.startswith("sqlite:///"):
        create_sqlite_database(connection_string[len("sqlite:///"):])
    else:
        with contextlib.redirect_stdout(io.StringIO()):
            testing.recreate_mysql_db(connection_string)

    layout = plan(load_profile(profile), scale, seed, runs, tables)
    rng = random.Random(seed + 1)
    url = connection_string.replace("mysql://", "mysql+pymysql://", 1)
    engine = create_engine(url)
    with engine.begin() as db:
        default_id = db.execute(select(Variation.id).where(Variation.name == "default")).scalar_one()
        stamp = {"created": FIRST, "modified": FIRST}
        top = db.execute(Directory.__table__.insert().values(name="loadtest", parentId=0, comment="load test", **stamp)).inserted_primary_key[0]
        directories = {}
        for number in range(min(DIRECTORIES, len(layout))):
            directories[number] = db.execute(Directory.__table__.insert().values(
                name="d{0:02d}".format(number), parentId=top, comment="", **stamp)).inserted_primary_key[0]

        # run ranges: one per distinct (min, max)
        ranges = sorted({(run_min, run_max) for table in layout for run_min, run_max, _, _ in table["assignments"]})
        db.execute(RunRange.__table__.insert(), [{"name": "", "runMin": low, "runMax": high, "comment": "", **stamp} for low, high in ranges])
        range_ids = {(row.runMin, row.runMax): row.id for row in db.execute(select(RunRange.__table__.c.id, RunRange.min, RunRange.max).where(RunRange.name == ""))}

        pending = []                                    # (created, table index, assignment index, set id)
        for index, table in enumerate(layout):
            name = table["path"].rsplit("/", 1)[1]
            type_id = db.execute(TypeTable.__table__.insert().values(
                name=name, directoryId=directories[index % DIRECTORIES], nRows=table["rows"], nColumns=table["columns"],
                comment="", **stamp)).inserted_primary_key[0]
            table["type_id"] = type_id
            db.execute(TypeTableColumn.__table__.insert(), [
                {"name": "c{0}".format(column), "typeId": type_id, "order": column, "columnType": "double", "comment": "", **stamp}
                for column in range(table["columns"])])
            set_ids, by_hash = [], {}
            for _ in range(table["sets"]):
                text = vault(rng, table["rows"], table["columns"], table["mean_set_bytes"])
                data = text.encode("utf-8")
                digest = hashlib.sha256(data).hexdigest()
                if digest not in by_hash:      # a tiny table can draw the same numbers twice: one set, as schema 6 keeps it
                    by_hash[digest] = db.execute(ConstantSet.__table__.insert().values(
                        vault=text, constantTypeId=type_id, sha256=digest, size=len(data), **stamp)).inserted_primary_key[0]
                set_ids.append(by_hash[digest])
            table["stored_sets"] = len(by_hash)
            for number, (run_min, run_max, created, set_index) in enumerate(table["assignments"]):
                pending.append((created, index, number, range_ids[(run_min, run_max)], set_ids[set_index]))

        pending.sort()                                  # ids grow with creation time, as in a real database
        for start in range(0, len(pending), 5000):
            db.execute(Assignment.__table__.insert(), [
                {"created": created, "modified": created, "runRangeId": range_id, "variationId": default_id,
                 "constantSetId": set_id, "comment": "", "authorId": 1}
                for created, _, _, range_id, set_id in pending[start:start + 5000]])
    engine.dispose()

    return {"connection": connection_string.split("@")[-1] if "@" in connection_string else connection_string,
            "scale": scale, "seed": seed, "runs": runs, "campaign_time": CAMPAIGN.strftime("%Y-%m-%d %H:%M:%S"),
            "assignments": len(pending), "sets": sum(table["stored_sets"] for table in layout),
            "tables": [{"path": table["path"], "rows": table["rows"], "columns": table["columns"],
                        "mean_set_bytes": table["mean_set_bytes"], "assignments": len(table["assignments"])}
                       for table in layout]}


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("connection", help="sqlite:///path or mysql://user@host/database; it is re-initialized")
    parser.add_argument("--scale", type=float, default=0.02, help="assignments per table as a share of the profile's (default 0.02)")
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--runs", type=int, default=100000, help="run numbers 0..RUNS-1 (default 100000)")
    parser.add_argument("--tables", type=int, help="draw this many table shapes from the profile (default: each shape once)")
    parser.add_argument("--profile", help="profile JSON (default: profile.json next to this script)")
    parser.add_argument("--manifest", help="write the manifest JSON here")
    args = parser.parse_args()
    manifest = build(args.connection, args.scale, args.seed, args.runs, args.tables, args.profile)
    if args.manifest:
        with open(args.manifest, "w") as stream:
            json.dump(manifest, stream, indent=1)
    print("{0} tables, {1} assignments, {2} constant sets".format(len(manifest["tables"]), manifest["assignments"], manifest["sets"]))


if __name__ == "__main__":
    main()
