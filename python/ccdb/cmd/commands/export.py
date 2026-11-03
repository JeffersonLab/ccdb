import importlib.util
import logging
import os

from ccdb.cmd import CliCommandBase, UtilityArgumentParser
from ccdb.path_utils import parse_time

log = logging.getLogger("ccdb.cmd.commands.export")

# Columns every exported row starts with: the assignment it comes from and the row's index in that assignment
METADATA_COLUMNS = ["assignment_id", "run_min", "run_max", "variation", "created", "author", "comment", "sha256", "row"]


def file_name(table_path):
    """The file of a table: its path without the leading slash, '/' as '.', e.g. epic.HCal.adc_calib.parquet"""
    return table_path.strip("/").replace("/", ".") + ".parquet"


def arrow_schema(table, request_text):
    """The Parquet schema of a table's export: the metadata columns, then the data columns with their units and
    comments as field metadata; the table path, its comment and the request as schema metadata"""
    import pyarrow
    data_types = {"int": pyarrow.int64(), "long": pyarrow.int64(), "uint": pyarrow.uint64(), "ulong": pyarrow.uint64(),
                  "double": pyarrow.float64(), "bool": pyarrow.bool_(), "string": pyarrow.string()}
    fields = [pyarrow.field("assignment_id", pyarrow.int64(), nullable=False),
              pyarrow.field("run_min", pyarrow.int64(), nullable=False),
              pyarrow.field("run_max", pyarrow.int64(), nullable=False),
              pyarrow.field("variation", pyarrow.string(), nullable=False),
              pyarrow.field("created", pyarrow.timestamp("us", tz="UTC"), nullable=False),
              pyarrow.field("author", pyarrow.string()),
              pyarrow.field("comment", pyarrow.string()),
              pyarrow.field("sha256", pyarrow.string(), nullable=False),
              pyarrow.field("row", pyarrow.int32(), nullable=False)]
    for column in table.columns:
        metadata = {b"units": (column.units or "").encode("utf-8"), b"comment": (column.comment or "").encode("utf-8"),
                    b"ccdb_type": column.type.encode("utf-8")}
        fields.append(pyarrow.field(column.name, data_types[column.type], metadata=metadata))
    metadata = {b"ccdb.table": table.path.encode("utf-8"), b"ccdb.comment": (table.comment or "").encode("utf-8"),
                b"ccdb.request": request_text.encode("utf-8")}
    return pyarrow.schema(fields, metadata=metadata)


def export_table(provider, table, assignments, directory, request_text):
    """Writes one Parquet file with the rows of the assignments; returns its path and the number of rows"""
    import pyarrow
    import pyarrow.parquet
    from ccdb.frames import assignment_metadata, typed_columns

    schema = arrow_schema(table, request_text)
    columns = {name: [] for name in schema.names}
    for assignment in assignments:
        metadata = assignment_metadata(assignment)
        data = typed_columns(assignment)
        rows = len(data[0][2]) if data else 0
        for name, key in (("assignment_id", "id"), ("run_min", "run_min"), ("run_max", "run_max"), ("variation", "variation"),
                          ("created", "created"), ("author", "author"), ("comment", "comment"), ("sha256", "sha256")):
            columns[name].extend([metadata[key]] * rows)
        columns["row"].extend(range(rows))
        for name, _, values in data:
            columns[name].extend(values)
    path = os.path.join(directory, file_name(table.path))
    pyarrow.parquet.write_table(pyarrow.Table.from_pydict(columns, schema=schema), path)
    return path, len(columns["row"])


class Export(CliCommandBase):
    """Exports tables to files for analysis"""

    command = "export"
    name = "Export"
    short_descr = "Exports tables to Parquet files (needs the export extra: pip install ccdb[export])"
    uses_db = True

    def execute(self, args):
        args = self.process_arguments(args)
        if importlib.util.find_spec("pyarrow") is None:
            log.critical("ccdb export parquet needs the export extra: pip install 'ccdb[export]' (no module pyarrow)")
            return False
        if args.tag and (args.variation or args.time):
            raise ValueError("A tag gives the variation and the time; remove -v/--variation and -t/--time")
        provider = self.context.provider
        tag = provider.get_tag(args.tag) if args.tag else None
        time = parse_time(args.time) if args.time else None
        os.makedirs(args.output, exist_ok=True)

        for raw_path in args.tables:
            table = provider.get_type_table(self.context.prepare_path(raw_path))
            if args.run is not None:
                # the assignment the run resolves to, as `ccdb cat` resolves it
                variation = "" if tag else (args.variation or self.context.current_variation or "default")
                assignments = [provider.get_assignment(table, args.run, variation, time, tag=tag)]
            else:
                # every version: of one variation with -v, of every variation without it; a time or a tag limits them
                assignments = provider.get_assignments(table, -1, args.variation or "", time, tag=tag)
            request_text = " ".join(["export parquet", table.path] + (["-r", str(args.run)] if args.run is not None else []) +
                                    (["-v", args.variation] if args.variation else []) + (["-t", args.time] if args.time else []) +
                                    (["--tag", args.tag] if args.tag else []))
            path, rows = export_table(provider, table, assignments, args.output, request_text)
            print("{0}: {1} assignments, {2} rows -> {3}".format(table.path, len(assignments), rows, path))
        return True

    @staticmethod
    def process_arguments(args):
        parser = UtilityArgumentParser(prog="ccdb export")
        parser.add_argument("format", choices=["parquet"])
        parser.add_argument("tables", nargs="+", help="table paths")
        parser.add_argument("-o", "--output", required=True, help="directory for the files, one per table")
        parser.add_argument("-r", "--run", type=int, help="only the assignment this run resolves to")
        parser.add_argument("-v", "--variation", default="")
        parser.add_argument("-t", "--time", help="only assignments created at or before this time (as in cat -t)")
        parser.add_argument("--tag", help="a tag instead of -v and -t")
        return parser.parse_args(args)

    def print_help(self):
        print("""Exports tables to Parquet files, one file per table (needs the export extra: pip install ccdb[export])

Usage:
    export parquet <table> [<table> ...] -o <directory> [-r <run>] [-v <variation>] [-t <time>] [--tag <tag>]

Each row of the file is one row of one assignment's data, after the columns that name the assignment:
assignment_id, run_min, run_max, variation, created (UTC, microseconds), author, comment, sha256, and the
row's index. The data columns keep the table's types; their units and comments are in the field metadata.

    -r  only the assignment the run resolves to (with the variation's parents, as cat), else every version
    -v  the variation (with -r: resolved from it; without -r: only its versions)
    -t  only assignments created at or before this time
    --tag  the tag's variation and time instead of -v and -t

Examples:
    > export parquet /epic/HCal/adc_calib -o exports                    # every version of the table
    > export parquet /epic/HCal/adc_calib -r 1500 -o exports            # what run 1500 reads now
    > export parquet /epic/HCal/adc_calib --tag campaign_demo -o exports
""")
