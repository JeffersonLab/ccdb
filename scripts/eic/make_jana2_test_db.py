#!/usr/bin/env python3
"""Creates the SQLite database the [jana2] C++ tests read (cpp/src/tests/test_JANA2_*.cc).

    python3 scripts/eic/make_jana2_test_db.py /tmp/jana2_tests.sqlite

The database is made by the real `ccdb` CLI: db init, mkvar, mktbl, add and tag. Afterwards the creation
times of the assignments are set to fixed dates with one SQL statement each, so the tests of the ccdb:time
parameter and of the tag do not depend on the clock:

    table              variation    runs     created      rows (the values the tests expect)
    /test/jana2/gains  default      0-999    2020-01-01   1.0 0.1 1 | 2.0 0.2 2       "old"
    /test/jana2/gains  default      0-999    2024-01-01   1.5 0.15 1 | 2.5 0.25 2     "new"
    /test/jana2/gains  default      200-299  2024-06-01   3.0 0.3 1 | 4.0 0.4 2       "runs 200"
    /test/jana2/pedestal default    0-999    2020-01-01   100
    /test/jana2/pedestal jana2_child 0-999   2024-01-01   200

The tag jana2_campaign points at variation default at 2022-01-01, so under it the gains are "old".
The child variation has no gains of its own: it inherits them from default.

The CLI runs from this checkout (PYTHONPATH=<repo>/python), so the script needs only the ccdb package's
dependencies, which the eic-shell image has.
"""

import argparse
import os
import sqlite3
import subprocess
import sys
import tempfile

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
USER = "jana2_tests"

# marker in the file's comment line -> (table, variation, runs, rows, created)
ASSIGNMENTS = [
    ("jana2:gains_old", "/test/jana2/gains", "default", "0-999", ["1.0 0.1 1", "2.0 0.2 2"], "2020-01-01 00:00:00"),
    ("jana2:gains_new", "/test/jana2/gains", "default", "0-999", ["1.5 0.15 1", "2.5 0.25 2"], "2024-01-01 00:00:00"),
    ("jana2:gains_run200", "/test/jana2/gains", "default", "200-299", ["3.0 0.3 1", "4.0 0.4 2"], "2024-06-01 00:00:00"),
    ("jana2:pedestal_default", "/test/jana2/pedestal", "default", "0-999", ["100"], "2020-01-01 00:00:00"),
    ("jana2:pedestal_child", "/test/jana2/pedestal", "jana2_child", "0-999", ["200"], "2024-01-01 00:00:00"),
]


def run_ccdb(connection, *args):
    """Runs one ccdb CLI command from this checkout and stops on its failure"""
    env = dict(os.environ, PYTHONPATH=os.path.join(REPO, "python"))
    command = [sys.executable, "-m", "ccdb", "-c", connection, "-u", USER] + list(args)
    result = subprocess.run(command, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
    if result.returncode != 0:
        sys.exit("ccdb {} failed with exit code {}:\n{}".format(" ".join(args), result.returncode, result.stdout))


def main():
    parser = argparse.ArgumentParser(description="Create the SQLite database of the [jana2] C++ tests")
    parser.add_argument("path", help="SQLite file to create; an existing file is replaced")
    path = os.path.abspath(parser.parse_args().path)

    if os.path.exists(path):
        os.remove(path)
    connection = "sqlite:///" + path

    run_ccdb(connection, "db", "init", "--init-i-am-sure")
    run_ccdb(connection, "user", "--create", USER)
    run_ccdb(connection, "mkdir", "/test/jana2")
    run_ccdb(connection, "mkvar", "jana2_child", "-p", "default")
    run_ccdb(connection, "mktbl", "/test/jana2/gains", "-r", "2", "gain=double", "offset=double", "channel=int", "#gains of the jana2 tests")
    run_ccdb(connection, "mktbl", "/test/jana2/pedestal", "-r", "1", "value=double", "#pedestal of the jana2 tests")

    with tempfile.TemporaryDirectory() as tmp_dir:
        for marker, table, variation, runs, rows, _ in ASSIGNMENTS:
            data_file = os.path.join(tmp_dir, marker.replace(":", "_") + ".txt")
            with open(data_file, "w") as f:
                f.write("#" + marker + "\n" + "\n".join(rows) + "\n")
            run_ccdb(connection, "add", table, "-v", variation, "-r", runs, data_file)

    # Fixed creation times; the file comment carries the marker into assignments.comment
    db = sqlite3.connect(path)
    for marker, _, _, _, _, created in ASSIGNMENTS:
        changed = db.execute("UPDATE assignments SET created = ? WHERE comment LIKE ?", (created, "%" + marker + "%")).rowcount
        if changed != 1:
            sys.exit("expected one assignment with the comment '{}', found {}".format(marker, changed))
    db.commit()
    db.close()

    run_ccdb(connection, "tag", "jana2_campaign", "-v", "default", "-t", "2022-01-01", "-c", "jana2 tests: the 2022 campaign")
    print(path)


if __name__ == "__main__":
    main()
