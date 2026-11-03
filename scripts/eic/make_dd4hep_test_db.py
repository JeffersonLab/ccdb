#!/usr/bin/env python3
"""Creates the SQLite database the [dd4hep] tests read (dd4hep/tests/test_dd4hep.cc).

    python3 scripts/eic/make_dd4hep_test_db.py /tmp/dd4hep_tests.sqlite

The database is made by the real `ccdb` CLI (db init, mktbl, add), with the units of schema 6 on the columns:

    table                     runs     rows
    /test/dd4hep/ecal_dims    0-max    inner_radius=105.5 outer_radius=160 length=340 [mm], n_sectors=48, material=PbWO4
    /test/dd4hep/gains        0-99     /world/box1 1.10 5   | /world/box2 1.20 6      element, gain, pedestal
    /test/dd4hep/gains        100-199  /world/box1 2.10 15  | /world/box2 2.20 16
    /test/dd4hep/alignment    0-99     /world/box1 dx=1 dy=0 dz=0 [mm], dphi=dtheta=dpsi=0 [rad]
    /test/dd4hep/alignment    100-199  /world/box1 dx=2 dy=0 dz=-3 [mm], dpsi=0.01 [rad]

The CLI runs from this checkout (PYTHONPATH=<repo>/python), so the script needs only the ccdb package's
dependencies, which the eic-shell image has.
"""

import argparse
import os
import subprocess
import sys
import tempfile

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
USER = "dd4hep_tests"

TABLES = [
    ("/test/dd4hep/ecal_dims", 1, ["inner_radius=double:mm", "outer_radius=double:mm", "length=double:mm", "n_sectors=int",
                                   "material=string"], "#ECal dimensions of the dd4hep tests"),
    ("/test/dd4hep/gains", 2, ["element=string", "gain=double", "pedestal=double:ADC"], "#gains per detector element"),
    ("/test/dd4hep/alignment", 1, ["element=string", "dx=double:mm", "dy=double:mm", "dz=double:mm", "dphi=double:rad",
                                   "dtheta=double:rad", "dpsi=double:rad"], "#alignment deltas per detector element"),
]

ASSIGNMENTS = [
    ("/test/dd4hep/ecal_dims", "0-", ["105.5 160 340 48 PbWO4"]),
    ("/test/dd4hep/gains", "0-99", ["/world/box1 1.10 5", "/world/box2 1.20 6"]),
    ("/test/dd4hep/gains", "100-199", ["/world/box1 2.10 15", "/world/box2 2.20 16"]),
    ("/test/dd4hep/alignment", "0-99", ["/world/box1 1 0 0 0 0 0"]),
    ("/test/dd4hep/alignment", "100-199", ["/world/box1 2 0 -3 0 0 0.01"]),
]


def run_ccdb(connection, *args):
    """Runs one ccdb CLI command from this checkout and stops on its failure"""
    env = dict(os.environ, PYTHONPATH=os.path.join(REPO, "python"))
    command = [sys.executable, "-m", "ccdb", "-c", connection, "-u", USER] + list(args)
    result = subprocess.run(command, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
    if result.returncode != 0:
        sys.exit("ccdb {} failed with exit code {}:\n{}".format(" ".join(args), result.returncode, result.stdout))


def main():
    parser = argparse.ArgumentParser(description="Create the SQLite database of the [dd4hep] tests")
    parser.add_argument("path", help="SQLite file to create; an existing file is replaced")
    path = os.path.abspath(parser.parse_args().path)
    if os.path.exists(path):
        os.remove(path)
    connection = "sqlite:///" + path

    run_ccdb(connection, "db", "init", "--init-i-am-sure")
    run_ccdb(connection, "user", "--create", USER)
    run_ccdb(connection, "mkdir", "/test/dd4hep")
    for table, rows, columns, comment in TABLES:
        run_ccdb(connection, "mktbl", table, "-r", str(rows), *columns, comment)
    with tempfile.TemporaryDirectory() as tmp_dir:
        for index, (table, runs, rows) in enumerate(ASSIGNMENTS):
            data_file = os.path.join(tmp_dir, "data{0}.txt".format(index))
            with open(data_file, "w") as f:
                f.write("\n".join(rows) + "\n")
            run_ccdb(connection, "add", table, "-r", runs, data_file)
    print(path)


if __name__ == "__main__":
    main()
