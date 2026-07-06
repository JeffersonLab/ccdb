"""
Example: dump CCDB constant tables for a run period into a pandas DataFrame
==========================================================================

For a range of runs (a "run period") this script reads a CCDB
constant table and builds a pandas DataFrame where:

  * each **run** is a single row (the run number is the DataFrame index)
  * the first data columns are the assignment metadata:
        created         - date/time the assignment was added to CCDB
        assignment_id   - database id of the assignment
        data_id         - database id of the constant set (the data)
        variation       - variation the assignment was taken from
  * then come the table's data columns.

Data column naming
------------------
A CCDB type table is a small grid (rows x columns). Its data is flattened
into the run's row:

  * If the table has a single row, columns are just ``<column_name>``.
  * If the table has several rows, columns are ``r0_<column_name>``,
    ``r1_<column_name>``, ... one block per table row.

Values are converted to proper python types (int/float/bool/str) according
to each CCDB column type, so the DataFrame is numeric where it should be.
Pass ``--save-strings`` to keep the raw DB strings untouched instead.

Runs that do not have an assignment for the table are skipped.

With ``--no-repeat`` consecutive runs whose whole row is identical are
collapsed into one: a run is kept only when something changed compared to the
previously kept run. Since the assignment/data ids are part of the row, this
keeps exactly the runs where a new constant set takes effect.

Usage
-----
    python example_run_period_to_pandas.py /BCAL/z_track_parameters -o out.csv

    python example_run_period_to_pandas.py /BCAL/z_track_parameters \
        --run-min 130000 --run-max 133696 \
        -v default --no-repeat -o period.feather

Note on dependencies
--------------------
CCDB itself does not depend on pandas. This is only an *example*, so it
imports pandas at runtime and tells you to install it if it is missing.
Serialization formats that need extra packages (feather/parquet -> pyarrow,
xlsx -> openpyxl, hdf -> tables) are attempted and produce a friendly hint
if the backend is not installed, instead of adding new hard dependencies.
"""

import argparse
import os
import sys

# sqlalchemy is already a CCDB dependency
from sqlalchemy.orm.exc import NoResultFound

try:
    import ccdb
except ImportError:
    # Allow running straight from a CCDB checkout via $CCDB_HOME
    ccdb_home = os.environ.get("CCDB_HOME")
    if ccdb_home:
        sys.path.append(os.path.join(ccdb_home, "python"))
    import ccdb

from ccdb.errors import ObjectIsNotFoundInDbError

# Default connection string (Hall D). Override with -C/--connection.
DEFAULT_CONNECTION = "mysql://ccdb_user@hallddb.jlab.org/ccdb"

# Default run period.
DEFAULT_RUN_MIN = 130000
DEFAULT_RUN_MAX = 133696


# ----------------------------------------------------------------------
# Type conversion: CCDB stores everything as strings in the blob.
# ----------------------------------------------------------------------
def convert_value(value, column_type):
    """Convert a raw CCDB string value to a proper python type.

    :param value: raw value (usually a string) coming from the constant set
    :param column_type: CCDB column type: one of
        int, uint, long, ulong, double, string, bool
    :return: value cast to the matching python type (falls back to the
        original value if it cannot be parsed)
    """
    if value is None:
        return None
    try:
        if column_type in ("int", "uint", "long", "ulong"):
            return int(value)
        if column_type == "double":
            return float(value)
        if column_type == "bool":
            # CCDB writes booleans as "0"/"1" (or "true"/"false")
            if isinstance(value, str):
                return value.strip().lower() in ("1", "true", "yes")
            return bool(value)
    except (ValueError, TypeError):
        # Leave the raw value in place rather than crashing the whole dump
        return value
    return value  # string (or already the right type)


# ----------------------------------------------------------------------
# Build one run's row for a single table
# ----------------------------------------------------------------------
def assignment_to_row(assignment, save_strings=False):
    """Turn a CCDB assignment into an ordered dict of column -> value.

    :param assignment: ccdb Assignment object
    :param save_strings: if True, keep data values as the raw strings stored
        in the DB instead of converting them to int/float/bool
    :return: dict preserving CCDB column order (metadata first, then data)
    """
    row = {}

    # --- assignment metadata ---
    row["created"] = assignment.created
    row["assignment_id"] = assignment.id
    row["data_id"] = assignment.constant_set.id
    row["variation"] = assignment.variation.name

    # --- tabular data ---
    type_table = assignment.constant_set.type_table
    columns = type_table.columns                 # ordered list of TypeTableColumn
    data_table = assignment.constant_set.data_table  # list of rows (list of str)

    single_row = len(data_table) == 1
    for row_index, data_row in enumerate(data_table):
        row_prefix = "" if single_row else "r{}_".format(row_index)
        for column, raw_value in zip(columns, data_row):
            name = row_prefix + column.name
            row[name] = raw_value if save_strings \
                else convert_value(raw_value, column.type)

    return row


# ----------------------------------------------------------------------
# Main data collection
# ----------------------------------------------------------------------
def collect_data(provider, table, run_min, run_max, variation, date,
                 no_repeat=False, save_strings=False):
    """Query CCDB for every run and build a list of row dicts.

    Runs that have no assignment for the table are skipped.

    :param provider: connected ccdb.AlchemyProvider
    :param table: resolved TypeTable object
    :param run_min: first run (inclusive)
    :param run_max: last run (inclusive)
    :param variation: variation name
    :param date: date string (or None) - constants at or before this date
    :param no_repeat: if True, drop a run whose whole row is identical to the
        previously kept run (only keep rows where something changed)
    :param save_strings: if True, keep data values as raw DB strings
    :return: (index list of run numbers, list of row dicts)
    """
    index = []
    rows = []
    skipped = 0
    repeated = 0

    total = run_max - run_min + 1
    for i, run in enumerate(range(run_min, run_max + 1)):
        if i % 200 == 0:
            sys.stderr.write("  ... run {} ({}/{}), collected {}\n"
                             .format(run, i, total, len(rows)))
            sys.stderr.flush()

        try:
            assignment = provider.get_assignment(table, run, variation, date)
        except (NoResultFound, ObjectIsNotFoundInDbError):
            skipped += 1
            continue

        row = assignment_to_row(assignment, save_strings=save_strings)

        # With --no-repeat, keep a run only when its whole row differs from
        # the previously kept one (i.e. something actually changed).
        if no_repeat and rows and row == rows[-1]:
            repeated += 1
            continue

        index.append(run)
        rows.append(row)

    sys.stderr.write("Collected {} runs, skipped {} (missing assignments)"
                     .format(len(rows), skipped))
    if no_repeat:
        sys.stderr.write(", dropped {} unchanged".format(repeated))
    sys.stderr.write("\n")
    return index, rows


# ----------------------------------------------------------------------
# Serialization: guess format from the output file extension
# ----------------------------------------------------------------------
def save_dataframe(df, output):
    """Save a DataFrame, guessing the format from the file extension.

    Uses only pandas built-in writers. Formats that need an extra backend
    (feather/parquet, xlsx, hdf) raise a friendly hint if it is missing,
    so CCDB gains no new hard dependencies.
    """
    ext = os.path.splitext(output)[1].lower().lstrip(".")

    # ext -> (callable, human name, optional backend package to hint at)
    writers = {
        "csv":     (lambda: df.to_csv(output), "CSV", None),
        "txt":     (lambda: df.to_csv(output, sep="\t"), "TSV", None),
        "tsv":     (lambda: df.to_csv(output, sep="\t"), "TSV", None),
        "json":    (lambda: df.to_json(output, orient="table", indent=2), "JSON", None),
        "pkl":     (lambda: df.to_pickle(output), "pickle", None),
        "pickle":  (lambda: df.to_pickle(output), "pickle", None),
        "feather": (lambda: df.reset_index().to_feather(output), "feather", "pyarrow"),
        "parquet": (lambda: df.to_parquet(output), "parquet", "pyarrow"),
        "h5":      (lambda: df.to_hdf(output, key="ccdb"), "HDF5", "tables"),
        "hdf":     (lambda: df.to_hdf(output, key="ccdb"), "HDF5", "tables"),
        "hdf5":    (lambda: df.to_hdf(output, key="ccdb"), "HDF5", "tables"),
        "xlsx":    (lambda: df.to_excel(output), "Excel", "openpyxl"),
    }

    if ext not in writers:
        sys.stderr.write(
            "Unknown output extension '.{}'. Falling back to CSV.\n"
            "Known extensions: {}\n".format(ext, ", ".join(sorted(writers))))
        df.to_csv(output)
        return

    writer, name, backend = writers[ext]
    try:
        writer()
    except ImportError:
        sys.stderr.write(
            "Saving as {} needs the '{}' package which is not installed.\n"
            "Install it (e.g. `pip install {}`) or choose another extension "
            "such as .csv / .json / .pkl\n".format(name, backend, backend))
        sys.exit(1)

    sys.stderr.write("Saved {} rows x {} columns as {} -> {}\n"
                     .format(len(df), len(df.columns), name, output))


# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Dump CCDB constant tables for a runs into a table",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Example:\n uv run example_run_period_to_pandas.py /BCAL/z_track_parameters -o period.csv")

    parser.add_argument("table", help="CCDB table path, e.g. /BCAL/z_track_parameters")
    parser.add_argument("-o", "--output",
                        help="Output file. Format is guessed from the extension (.csv, .json, .pkl, .feather, "
                             ".parquet, .xlsx, .h5). If omitted, the table is printed to stdout.")
    parser.add_argument("-C", "--connection", default=DEFAULT_CONNECTION,
                        help="CCDB connection string (default: %(default)s)")
    parser.add_argument("-v", "--variation", default="default", help="Variation name (default: %(default)s)")
    parser.add_argument("-d", "--date", default=None, help="Date/time cut: use constants added at or before "
                             "this date (CCDB date format, e.g. '2020-01-31_00-00-00'). Default: latest.")
    parser.add_argument("--run-min", type=int, default=DEFAULT_RUN_MIN, help="First run of the period (default: %(default)s)")
    parser.add_argument("--run-max", type=int, default=DEFAULT_RUN_MAX, help="Last run of the period (default: %(default)s)")
    parser.add_argument("--no-repeat", action="store_true", help="Remove identical rows: keep a run only when something changed compared to the previous kept run.")
    parser.add_argument("--save-strings", action="store_true", help="Keep data values as the raw strings stored in the DB (no int/float/bool conversion). Handy for CSVs.")

    args = parser.parse_args()

    if args.run_min > args.run_max:
        parser.error("--run-min must be <= --run-max")

    # pandas is only needed here, not by CCDB itself.
    try:
        import pandas as pd
    except ImportError:
        sys.stderr.write("This example needs pandas. Install it with "
                         "`pip install pandas`.\n")
        sys.exit(1)

    # --- connect ---
    provider = ccdb.AlchemyProvider()
    provider.connect(args.connection)
    provider.authentication.current_user_name = "anonymous"  # for logs

    # --- resolve the table (fail early on a bad path) ---
    try:
        table = provider.get_type_table(args.table)
    except ObjectIsNotFoundInDbError:
        sys.stderr.write("Table not found in CCDB: {}\n".format(args.table))
        sys.exit(1)

    sys.stderr.write("Reading '{}' for runs {}..{} (variation '{}')\n"
                     .format(table.path, args.run_min, args.run_max,
                             args.variation))

    # --- collect ---
    index, rows = collect_data(provider, table, args.run_min, args.run_max,
                               args.variation, args.date,
                               no_repeat=args.no_repeat,
                               save_strings=args.save_strings)

    # Build the DataFrame. Passing the row dicts preserves column order
    # (metadata first, then data) as inserted.
    df = pd.DataFrame(rows, index=index)
    df.index.name = "run"

    # --- output ---
    if args.output:
        save_dataframe(df, args.output)
    else:
        # Print everything to stdout
        with pd.option_context("display.max_rows", None,
                               "display.max_columns", None,
                               "display.width", None):
            print(df)


if __name__ == "__main__":
    main()
