#!/usr/bin/env python3
"""Writes the data of testdata/time/resolution.tsv into a fresh CCDB database, for the time resolution tests.

    python scripts/time/make_time_db.py sqlite:////tmp/time.sqlite
    python scripts/time/make_time_db.py mysql://ccdb_user@127.0.0.1/ccdb_test     (the database is re-initialized)

The table /test/time/values (one int column) gets one assignment per `assignment` row, in file order, with the
row's value as its data and the row's UTC creation time to the microsecond; the variation child (parent default)
and the tags are made as the file says. The Python test (python/tests/unit_test_time_resolution.py) and the C++
test (cpp/src/tests/test_TimeResolution.cc) run the file's queries on the result. See docs/concepts/time.md.
"""
import argparse
import contextlib
import io
import os
import sys
from datetime import datetime, timezone

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CASES = os.path.join(REPO, "testdata", "time", "resolution.tsv")
TABLE_DIR = "/test/time"
TABLE = TABLE_DIR + "/values"


def read_cases(path=CASES):
    """{"assignment": [(value, variation, utc text)], "tag": [(name, variation, utc text)],
    "query": [(zone, request, expected value or None)]}"""
    cases = {"assignment": [], "tag": [], "query": []}
    with open(path, encoding="utf-8") as file:
        for line in file:
            if not line.strip() or line.startswith("#"):
                continue
            kind, *fields = line.rstrip("\n").split("\t")
            if kind == "assignment":
                cases[kind].append((int(fields[0]), fields[1], fields[2]))
            elif kind == "tag":
                cases[kind].append((fields[0], fields[1], fields[2]))
            elif kind == "query":
                cases[kind].append((fields[0], fields[1], None if fields[2] == "NONE" else int(fields[2])))
            else:
                raise ValueError("Unknown line kind '{0}' in {1}".format(kind, path))
    return cases


def utc(text):
    return datetime.strptime(text, "%Y-%m-%d %H:%M:%S.%f").replace(tzinfo=timezone.utc)


def build(connection_string, cases=None):
    """Re-creates the database and writes the cases' data into it"""
    from ccdb import AlchemyProvider, testing
    from ccdb.sql.sqlite_schema import create_sqlite_database

    cases = cases or read_cases()
    if connection_string.startswith("sqlite:///"):
        create_sqlite_database(connection_string[len("sqlite:///"):])
    else:
        with contextlib.redirect_stdout(io.StringIO()):
            testing.recreate_mysql_db(connection_string)

    provider = AlchemyProvider()
    provider.connect(connection_string)
    try:
        provider.authentication.current_user_name = "test_user"
        provider.create_directory("time", "/test", "time resolution tests (docs/concepts/time.md)")
        provider.create_type_table("values", TABLE_DIR, 1, [("value", "int")], "one value per assignment")
        provider.create_variation("child", "inherits from default", "default")
        for value, variation, created in cases["assignment"]:
            assignment = provider.create_assignment([[value]], TABLE, 0, 2147483647, variation, "value {0}".format(value))
            assignment.created = utc(created)
            provider.session.commit()
        for name, variation, snapshot in cases["tag"]:
            provider.create_tag(name, variation, utc(snapshot), "time resolution tests")
    finally:
        provider.disconnect()


def main():
    parser = argparse.ArgumentParser(description="Write testdata/time/resolution.tsv into a fresh CCDB database")
    parser.add_argument("connection", help="sqlite:///path or mysql://user@host/database; it is re-created")
    sys.path.insert(0, os.path.join(REPO, "python"))
    build(parser.parse_args().connection)
    print(parser.parse_args().connection)


if __name__ == "__main__":
    main()
