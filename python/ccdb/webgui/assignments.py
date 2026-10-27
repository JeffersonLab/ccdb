"""Assignment addressing and data: one resolver for both URL forms, and the data as a dict or as text.

The CCDB request string (`/FCAL/gains:30000:default:2017-11-16_10-03-20`) is the primary identifier:
the CLI, the C++ and Python APIs and users' notes use it. The database id is a second, short form.
Every assignment view goes through resolve_assignment(), so both forms give the same answer.

A request string without a timestamp can match several assignments; the newest wins, as in the CLI.
"""
import datetime
from dataclasses import dataclass

from flask import abort

import ccdb
from ccdb.path_utils import parse_request, ParseRequestResult
from ccdb.webgui import diff

INFINITE_RUN = 2147483647
EXAMPLE_REQUEST = "/test/test_vars/test_table:0:default"
LAYOUTS = ("auto", "horizontal", "vertical")


@dataclass
class Resolved:
    """An assignment plus whether the address named it exactly (an id, or a request with a timestamp)."""
    assignment: ccdb.Assignment
    exact: bool


def parse_request_or_400(text):
    """The parsed CCDB request string; empty, malformed, or carrying an out-of-range run → 400."""
    if not text:
        abort(400, "The 'request' parameter is empty. Expected a CCDB request such as " + EXAMPLE_REQUEST)
    try:
        parsed = parse_request(text)
    except ValueError as error:
        abort(400, "Bad request string '{0}': {1}".format(text, error))
    assert isinstance(parsed, ParseRequestResult)
    # parse_request() accepts any whole number as the run, including one wider than the `runRanges` columns,
    # which raises in the driver and answers 500. The same range the run query parameter allows applies here.
    if not 0 <= parsed.run <= INFINITE_RUN:
        abort(400, "The run in a request must be between 0 and {0}, got {1}".format(INFINITE_RUN, parsed.run))
    return parsed


def compose_request(args):
    """The request string from the request form's parts: path, run (default 0), variation (default `default`), time."""
    path = args.get("path", "").strip()
    run = args.get("run", "").strip() or "0"
    variation = args.get("variation", "").strip() or "default"
    time = args.get("time", "").strip()
    return "{0}:{1}:{2}".format(path, run, variation) + (":" + time if time else "")


def resolve_assignment(db, request_string=None, assignment_id=None):
    """The assignment behind a request string or a database id; unknown → 404, malformed → 400."""
    if assignment_id is not None:
        return Resolved(db.get_assignment_by_id(assignment_id), exact=True)  # not found → ObjectIsNotFoundInDbError → 404
    parsed = parse_request_or_400(request_string)
    time = parsed.time if parsed.time_is_parsed else None
    try:
        assignments = db.get_assignments(parsed.path, parsed.run, parsed.variation, time)
    except ValueError as error:  # the provider rejects a path without a directory part, such as "garbage"
        abort(400, "Bad request string: {0}".format(error))
    if not assignments:
        abort(404, "No assignment matches the request '{0}:{1}:{2}'".format(parsed.path, parsed.run, parsed.variation))
    # A timestamp in the past pins the answer; a future or unparseable one (parse_request turns "notadate"
    # into the year 2137) still resolves to the newest assignment, so it must not be cached as exact.
    exact = parsed.time_is_parsed and parsed.time <= datetime.datetime.now()
    return Resolved(assignments[0], exact=exact)


def previous_assignment(db, assignment):
    """The assignment the same request string resolved to before this one was added: the newest one of the same
    table, run and variation created at least a second earlier; None when there is none.

    Request strings carry seconds, so an assignment created in the same second as this one is not "previous":
    the two are one to a request string, and this returns what came before both.
    """
    before = assignment.created - datetime.timedelta(seconds=1)
    earlier = db.get_assignments(assignment.constant_set.type_table.path, assignment.run_range.min, assignment.variation.name, before)
    return earlier[0] if earlier else None


def column_lines(layout, row_count, column_count):
    """Whether the data table is shown with one line per column.

    The switch names the forms by the shape the user sees on a many-row table: Vertical is one line per row,
    Horizontal one line per column (the wide form). `ccdb cat -pv` prints one line per column, so the words
    are the opposite of the CLI flags; a user decision of 2026-10-25. `auto` picks one line per column for a
    single row with more than two columns, the shape of a key-value parameter table, where one wide line
    reads badly; everything else is one line per row.
    """
    if layout == "auto":
        return row_count == 1 and column_count > 2
    return layout == "horizontal"


def run_range_text(assignment):
    """`min - max`, with `inf.` for the open-ended sentinel, as the CLI prints it."""
    high = assignment.run_range.max
    return "{0} - {1}".format(assignment.run_range.min, "inf." if high == INFINITE_RUN else high)


def assignment_dict(assignment):
    """The assignment's metadata and data as plain values; `jsonify` turns it into the JSON view.

    Cells stay the strings CCDB stores, so a value reads back exactly as it was added.
    """
    table = assignment.constant_set.type_table
    return {
        "id": assignment.id,
        "request": assignment.request,
        "table": table.path,
        "variation": assignment.variation.name,
        "run_min": assignment.run_range.min,
        "run_max": assignment.run_range.max,
        "created": str(assignment.created),
        "author": assignment.author.name if assignment.author else "",
        "comment": assignment.comment,
        "columns": [{"name": column.name, "type": column.type} for column in table.columns],
        "rows": assignment.constant_set.data_table,
    }


def assignment_text(assignment):
    """The data in the `ccdb dump` text format: `#` comment lines, then one row per line with padded cells.

    Same layout as `ccdb cat --no-borders --no-header --comments --horizontal`: each cell is left-aligned in
    a field at least 10 characters wide (wider when the column name is longer), the row layout `diff.row_line`
    shares with the unified diff download. The first line names the request; `#` lines are comments to every
    CCDB text reader, so the file can go back in with `ccdb add`.
    """
    table = assignment.constant_set.type_table
    widths = diff.column_widths(column.name for column in table.columns)
    lines = ["#request: " + assignment.request]
    lines += ["#" + line for line in assignment.comment.split("\n")]
    for row in assignment.constant_set.data_table:
        lines.append(diff.row_line(widths, row))
    return "\n".join(lines) + "\n"
