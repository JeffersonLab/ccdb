"""The difference between the data of two assignments, cell by cell.

Pure Python over the strings CCDB stores: no Flask, no database. The compare page renders a TableDiff
in its three views, the JSON view serializes it, and a command-line `ccdb diff` could use it as is.

Two sides are called `a` and `b`; which assignment is which is the caller's choice. A cell is changed
when its two strings differ. `1.0` and `1` are therefore changed: the APIs hand the strings out as
stored, and the page shows what they return. For a changed pair of numbers the difference `b - a` and
the change relative to `a` come along for the cell tooltip.

Every assignment of a table holds the table's rows × columns cells, so two sides of one table always
have the same shape; a mismatch is bad data and raises ValueError.

`unified_diff` writes a TableDiff in the unified diff format (`diff -u`, `git diff`), the file every diff
viewer opens, with one line per row in the `ccdb dump` layout of the text download: the diff of the two
downloads and the served file agree hunk for hunk.
"""
import math
from dataclasses import dataclass


@dataclass
class Cell:
    a: str
    b: str
    changed: bool
    delta: float = None       # b - a, when both are numbers and differ
    relative: float = None    # delta / |a|, when a is not zero


@dataclass
class TableDiff:
    columns: list             # [{"name": ..., "type": ...}] of the table, in column order
    rows: list                # one list of Cell per row index
    changed_cells: int
    changed_rows: list        # row indexes with at least one changed cell, ascending
    changed_columns: list     # column indexes with at least one changed cell, ascending

    @property
    def cells(self):
        return len(self.rows) * len(self.columns)


def numeric_delta(a, b):
    """(b - a, (b - a) / |a|) when both strings are finite numbers; (None, None) otherwise or when a is zero
    for the relative part. `float()` accepts `nan` and `inf`, which make no useful difference, hence the finite check."""
    try:
        a_value, b_value = float(a), float(b)
    except ValueError:
        return None, None
    if not (math.isfinite(a_value) and math.isfinite(b_value)):
        return None, None
    delta = b_value - a_value
    return delta, (delta / abs(a_value) if a_value else None)


def diff_tables(a_rows, b_rows, columns):
    """The TableDiff of two data tables (lists of rows, each a list of cell strings) over the table's columns."""
    width = len(columns)
    if len(a_rows) != len(b_rows):
        raise ValueError("The two sides have {0} and {1} rows; assignments of one table hold the same number of rows".format(len(a_rows), len(b_rows)))
    rows, changed_cells, changed_rows, changed_columns = [], 0, [], set()
    for row_i, (a_row, b_row) in enumerate(zip(a_rows, b_rows)):
        if len(a_row) != width or len(b_row) != width:
            raise ValueError("Row {0} has {1} and {2} cells for {3} columns".format(row_i, len(a_row), len(b_row), width))
        cells = []
        for col_i, (a, b) in enumerate(zip(a_row, b_row)):
            changed = a != b
            delta, relative = numeric_delta(a, b) if changed else (None, None)
            cells.append(Cell(a, b, changed, delta, relative))
            if changed:
                changed_cells += 1
                changed_columns.add(col_i)
        if any(cell.changed for cell in cells):
            changed_rows.append(row_i)
        rows.append(cells)
    return TableDiff(list(columns), rows, changed_cells, changed_rows, sorted(changed_columns))


def kept_rows(diff, changed_only):
    """[(row index, cells)] of the rows a view shows: all of them, or only those with a change."""
    if changed_only:
        return [(row_i, diff.rows[row_i]) for row_i in diff.changed_rows]
    return list(enumerate(diff.rows))


def column_widths(names):
    """The field width of every column of the `ccdb dump` text layout: at least 10 characters, more when the
    column name is longer. Both sides of a comparison share the table, so they share the widths."""
    return [max(10, len(name)) for name in names]


def row_line(widths, row):
    """One data row as `ccdb cat --no-borders --no-header --horizontal` prints it: every cell left-aligned in its field."""
    return "".join("  %-*s " % (width, cell) for width, cell in zip(widths, row)) + " "


def unified_diff(diff, a_name, b_name, a_label="A", b_label="B", context=3):
    """The lines of a unified diff of the two sides, one data line per row, without line terminators.

    The two sides are aligned row by row, so the hunks are built from `diff.changed_rows` instead of a sequence
    match: a changed row is always one `-` line and one `+` line, never a shifted pair, and the work is linear
    in the rows. Hunk line numbers are 1-based as the format wants, so the line number of a hunk is the row
    index of the page plus one. Two changes with at most two contexts of unchanged rows between them share a hunk, as `diff -u` groups them.
    The two header lines name the sides by `a_name` and `b_name` (the request strings) and carry the labels
    after a tab, where the format puts the file date; they are written even when nothing differs, so the file
    says what it compared.
    """
    widths = column_widths(column["name"] for column in diff.columns)
    lines = ["--- {0}\t{1}".format(a_name, a_label), "+++ {0}\t{1}".format(b_name, b_label)]
    total = len(diff.rows)

    def line(side, row_i):
        return row_line(widths, [getattr(cell, side) for cell in diff.rows[row_i]])

    def span(start, length):  # the `start,length` part of a hunk header; a length of one is written as the start alone
        return "{0},{1}".format(start + 1, length) if length != 1 else str(start + 1)

    changed = diff.changed_rows
    i = 0
    while i < len(changed):
        first = max(0, changed[i] - context)
        j = i
        while j + 1 < len(changed) and changed[j + 1] - changed[j] - 1 <= 2 * context:  # at most 2×context unchanged rows between
            j += 1
        last = min(total - 1, changed[j] + context)
        lines.append("@@ -{0} +{1} @@".format(span(first, last - first + 1), span(first, last - first + 1)))
        hunk_changed = set(changed[i:j + 1])
        row_i = first
        while row_i <= last:
            if row_i not in hunk_changed:
                lines.append(" " + line("a", row_i))
                row_i += 1
                continue
            run_end = row_i  # a run of consecutive changed rows: all its `-` lines, then all its `+` lines
            while run_end + 1 <= last and run_end + 1 in hunk_changed:
                run_end += 1
            lines += ["-" + line("a", each) for each in range(row_i, run_end + 1)]
            lines += ["+" + line("b", each) for each in range(row_i, run_end + 1)]
            row_i = run_end + 1
        i = j + 1
    return lines


def delta_text(cell):
    """The tooltip of a changed cell: `a → b`, and for numbers `Δ +0.005 (+2.56 %)`."""
    text = "{0} → {1}".format(cell.a, cell.b)
    if cell.delta is not None:
        text += "  Δ {0:+.6g}".format(cell.delta)
        if cell.relative is not None:
            text += " ({0:+.3g} %)".format(cell.relative * 100)
    return text
