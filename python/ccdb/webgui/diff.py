"""The difference between the data of two assignments, cell by cell.

Pure Python over the strings CCDB stores: no Flask, no database. The compare page renders a TableDiff
in its three views, the JSON view serializes it, and a command-line `ccdb diff` could use it as is.

Two sides are called `a` and `b`; which assignment is which is the caller's choice. A cell is changed
when its two strings differ. `1.0` and `1` are therefore changed: the APIs hand the strings out as
stored, and the page shows what they return. For a changed pair of numbers the difference `b - a` and
the change relative to `a` come along for the cell tooltip.

Every assignment of a table holds the table's rows × columns cells, so two sides of one table always
have the same shape; a mismatch is bad data and raises ValueError.
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


def delta_text(cell):
    """The tooltip of a changed cell: `a → b`, and for numbers `Δ +0.005 (+2.56 %)`."""
    text = "{0} → {1}".format(cell.a, cell.b)
    if cell.delta is not None:
        text += "  Δ {0:+.6g}".format(cell.delta)
        if cell.relative is not None:
            text += " ({0:+.3g} %)".format(cell.relative * 100)
    return text
