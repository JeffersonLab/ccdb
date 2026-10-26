"""Golden data: what each page must show, computed from SQL on the fixture, independent of the web layer.

Usage:
  python golden.py --space DIR compute                        -> <space>/reports/golden.json
  python golden.py --space DIR compare --label L [--phase N]  -> <space>/reports/golden_compare_[phase<N>_]<L>.json

`compute` reads the fixture with the sqlite3 module only (no ORM), so a provider bug cannot leak into
the expectation. `compare` requests the pages through the Flask test client, parses the HTML with the
standard html.parser, and reports every check as pass or fail with a sample of the mismatches;
its exit code is 1 when a check fails, so it serves as a gate.

The parsers in the "page readers" section know the current markup (column order, the data-path
attribute on tree items). When the templates change, update the readers; the golden values themselves do not change.
"""
import argparse
import datetime
import json
import re
import sqlite3
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pages  # noqa: E402
import workspace  # noqa: E402
from smoke import make_app  # noqa: E402  (the pages are requested the way the smoke suite does)
from ccdb.webgui.views import natural_key  # noqa: E402  (the order the tree is rendered in)

INFINITE_RUN = 2147483647


def golden_path(space):
    return space / "reports" / "golden.json"

SHOW_REQUESTS = {  # label in pages.py -> (table path, run, variation)
    "show_small": (pages.SMALL_TABLE, 0, "default"),
    "show_big": (pages.BIG_TABLE, 1500, "default"),
    "show_big_mc": (pages.BIG_TABLE, 1500, "mc"),
    "show_hostile": (pages.HOSTILE_TABLE, 0, "default"),
    "show_kv": (pages.KV_TABLE, 0, "default"),
}
SHOW_LAYOUTS = {  # pages that show one of the assignments above in another data layout -> its golden key
    "show_kv_horizontal": "show_kv",
    "show_big_vertical": "show_big",
    "show_big_horizontal": "show_big",
    "assignment_by_id_vertical": "show_small",
}
DIFFS = {  # golden key -> (assignment id of side a, of side b); the diff is computed from the two vault blobs
    "channels": (3612, 3613),   # 600 rows × 4 columns, seven cells differ
    "parms": (3610, 3611),      # one row × six columns, two cells differ
    "same": (3612, 3612),       # no cell differs
}
DIFF_PAGES = {  # label in pages.py -> (golden key, view, the lines the page renders (rows: one line per row, columns: one per column), changed rows only, page number)
    "diff_channels": ("channels", "cells", "rows", False, 1),
    "diff_by_id": ("channels", "cells", "rows", False, 1),
    "diff_changed_only": ("channels", "cells", "rows", True, 1),
    "diff_vertical": ("channels", "cells", "rows", True, 1),           # the switch's Vertical is one line per row
    "diff_horizontal": ("channels", "cells", "columns", True, 1),      # Horizontal is one line per column
    "diff_page3": ("channels", "cells", "rows", False, 3),
    "diff_parms": ("parms", "cells", "columns", False, 1),             # one row, six columns: auto is one line per column
    "diff_parms_mixed": ("parms", "cells", "columns", False, 1),
    "diff_same": ("same", "cells", "rows", False, 1),
    "diff_columns": ("channels", "columns", "rows", True, 1),
    "diff_columns_vertical": ("parms", "columns", "columns", False, 1),
    "diff_tables": ("channels", "tables", "rows", True, 1),
    "diff_tables_vertical": ("parms", "tables", "columns", False, 1),
}
DIFF_PAGE_SIZE = 200
LOG_RECORDS = {"log_record": 2414, "log_record_hostile": 14, "log_record_directory": 13, "log_record_table": 2415,
               "log_record_variation": 2416, "log_record_deleted": 2417}   # label in pages.py -> log id
VERSIONS = {"versions_big": pages.BIG_TABLE, "versions_small": pages.SMALL_TABLE, "versions_deep": pages.DEEP_TABLE,
            "versions_hostile": pages.HOSTILE_TABLE, "versions_unicode": pages.UNICODE_TABLE}
COMPARES = {  # label in pages.py -> (variation, parent or None for the direct parent, run, time text as the page takes it)
    "compare_calib_v2": ("calib_v2", None, None, None),
    "compare_calib_v2_default": ("calib_v2", "default", None, None),
    "compare_run": ("calib_v2", None, 1500, None),
    "compare_time": ("calib_v2", "default", None, "2020-01-02"),
    "compare_subsubtest": ("subsubtest", None, None, None),
}


# ----------------------------------------------------------------------------- compute from SQL

def directory_paths(db):
    """id -> absolute path, built from parentId links (0 is the root)."""
    rows = db.execute("SELECT id, name, parentId FROM directories ORDER BY id").fetchall()
    by_id = {row["id"]: row for row in rows}
    paths = {}

    def path_of(dir_id):
        if dir_id == 0:
            return ""
        if dir_id not in paths:
            row = by_id[dir_id]
            paths[dir_id] = path_of(row["parentId"]) + "/" + row["name"]
        return paths[dir_id]

    return {dir_id: path_of(dir_id) for dir_id in by_id}


def table_paths(db, dirs):
    return {row["id"]: dirs[row["directoryId"]] + "/" + row["name"] for row in db.execute("SELECT id, name, directoryId FROM typeTables")}


def request_string(path, run_min, variation, created):
    return f"{path}:{run_min}:{variation}:{created.strftime('%Y-%m-%d_%H-%M-%S')}"


def parse_stamp(text):
    return datetime.datetime.fromisoformat(text)


def shown_stamp(text):
    """Timestamps as the pages print them: str(datetime) drops a zero microsecond part that SQLite stores as .000000."""
    return str(parse_stamp(text))


def assignments_of(db, table_id):
    sql = """SELECT a.id, a.created, a.comment, r.runMin, r.runMax, v.name AS variation, u.name AS author, c.vault
             FROM assignments a JOIN constantSets c ON c.id = a.constantSetId JOIN runRanges r ON r.id = a.runRangeId
             JOIN variations v ON v.id = a.variationId JOIN users u ON u.id = a.authorId
             WHERE c.constantTypeId = ? ORDER BY a.id DESC"""
    return db.execute(sql, (table_id,)).fetchall()


def compute(space):
    db = sqlite3.connect(str(workspace.fixture_path(space)))
    db.row_factory = sqlite3.Row
    dirs = directory_paths(db)
    tables = table_paths(db, dirs)
    table_id_by_path = {path: table_id for table_id, path in tables.items()}
    golden = {"tree": {"directories": sorted(dirs.values()), "tables": sorted(tables.values())}}

    golden["versions"] = {}
    for label, path in VERSIONS.items():
        rows = assignments_of(db, table_id_by_path[path])
        golden["versions"][label] = {"path": path, "count": len(rows), "rows": [
            {"run_min": r["runMin"], "run_max": r["runMax"], "created": shown_stamp(r["created"]), "variation": r["variation"],
             "request": request_string(path, r["runMin"], r["variation"], parse_stamp(r["created"]))} for r in rows]}

    golden["show"] = {}
    for label, (path, run, variation) in SHOW_REQUESTS.items():
        table_id = table_id_by_path[path]
        column_rows = db.execute("SELECT name, columnType FROM columns WHERE typeId = ? ORDER BY \"order\"", (table_id,)).fetchall()
        columns, types = [r["name"] for r in column_rows], [r["columnType"] for r in column_rows]
        rows_count = db.execute("SELECT nRows FROM typeTables WHERE id = ?", (table_id,)).fetchone()[0]
        match = [r for r in assignments_of(db, table_id) if r["variation"] == variation and r["runMin"] <= run <= r["runMax"]]
        newest = match[0]  # assignments_of is newest first; the CLI picks the newest too
        cells = newest["vault"].split("|")
        data = [cells[i * len(columns):(i + 1) * len(columns)] for i in range(rows_count)]
        golden["show"][label] = {"path": path, "variation": variation, "created": shown_stamp(newest["created"]), "author": newest["author"],
                                 "run_min": newest["runMin"], "run_max": newest["runMax"], "comment": newest["comment"],
                                 "request": request_string(path, newest["runMin"], variation, parse_stamp(newest["created"])),
                                 "columns": columns, "types": types, "data": data, "candidates": len(match)}

    logs = db.execute("SELECT l.created, l.action, l.description, u.name AS author FROM logs l JOIN users u ON u.id = l.authorId ORDER BY l.id DESC").fetchall()
    golden["logs"] = {"total": len(logs), "newest_first_1000": [{**dict(r), "created": shown_stamp(r["created"])} for r in logs[:1000]],
                      "newest_ids": [r[0] for r in db.execute("SELECT id FROM logs ORDER BY id DESC LIMIT 50")]}

    # log record pages: the whole row, the comment unshortened, the affected objects as the page prints them
    golden["log_record"] = {}
    for label, log_id in LOG_RECORDS.items():
        row = db.execute("SELECT l.id, l.created, l.action, l.description, l.comment, l.affectedIds, u.name AS author FROM logs l JOIN users u ON u.id = l.authorId WHERE l.id = ?", (log_id,)).fetchone()
        # the page names the objects as users know them: a table or directory by path, a variation by name, the rest by id
        variation_names = {v_id: name for v_id, name in db.execute("SELECT id, name FROM variations")}
        words = []
        for kind, number in re.findall(r"(assignments|variations|typeTables|directories|users)_?(\d+)", row["affectedIds"]):
            number = int(number)
            if kind == "typeTables" and number in tables:
                words.append("table " + tables[number])
            elif kind == "directories" and number in dirs:
                words.append("directory " + dirs[number])
            elif kind == "variations" and number in variation_names:
                words.append("variation " + variation_names[number])
            else:
                words.append("{0} {1}".format({"typeTables": "table", "assignments": "assignment", "directories": "directory", "variations": "variation", "users": "user"}[kind], number))
        affected = ", ".join(words)
        golden["log_record"][label] = {"id": row["id"], "created": shown_stamp(row["created"]), "action": row["action"], "description": row["description"],
                                       "comment": row["comment"] or "", "author": row["author"], "affected": affected or "none",
                                       "object_links": [f"/versions{tables[int(n)]}" for n in re.findall(r"typeTables_?(\d+)", row["affectedIds"]) if int(n) in tables]
                                                       + [f"/tree?filter={dirs[int(n)]}" for n in re.findall(r"directories_?(\d+)", row["affectedIds"]) if int(n) in dirs],
                                       "variation_link": any(int(n) in variation_names for n in re.findall(r"variations_?(\d+)", row["affectedIds"])),
                                       "assignment_link": "/assignments/{0}".format(re.search(r"assignments_?(\d+)", row["affectedIds"]).group(1)) if row["action"] in ("create", "update") and "assignments" in row["affectedIds"] else None}

    variations = db.execute("SELECT v.name, v.created, v.comment, p.name AS parent FROM variations v LEFT JOIN variations p ON p.id = v.parentId ORDER BY v.id").fetchall()
    golden["variations"] = [{**dict(r), "created": shown_stamp(r["created"])} for r in variations]

    # compare variations: the chain segment from SQL on parentId links, then the grouped assignment counts
    parents = {r["name"]: r["parent"] for r in db.execute("SELECT v.name, p.name AS parent FROM variations v LEFT JOIN variations p ON p.id = v.parentId")}
    golden["compare"] = {}
    for label, (variation, parent, run, time_text) in COMPARES.items():
        chain, level = [], variation
        while level is not None:
            chain.insert(0, level)
            level = parents[level]
        parent = parent or (chain[-2] if len(chain) > 1 else None)
        segment = chain[chain.index(parent) + 1:] if parent else []
        sql = ("SELECT c.constantTypeId AS table_id, v.name AS variation, COUNT(*) AS n FROM assignments a "
               "JOIN constantSets c ON c.id = a.constantSetId JOIN variations v ON v.id = a.variationId JOIN runRanges r ON r.id = a.runRangeId "
               f"WHERE v.name IN ({','.join('?' * len(segment))})")
        params = list(segment)
        if run is not None:
            sql += " AND r.runMin <= ? AND r.runMax >= ?"
            params += [run, run]
        if time_text:  # a date alone means its end, as in a request string
            sql += " AND a.created <= ?"
            params.append(time_text + " 23:59:59")
        affected = {}
        for row in db.execute(sql + " GROUP BY c.constantTypeId, v.name", params):
            affected.setdefault(tables[row["table_id"]], {})[row["variation"]] = row["n"]
        golden["compare"][label] = {"segment": segment, "tables": affected}

    # compare assignments: the cell-by-cell diff of two assignments straight from their vault blobs
    golden["diff"] = {}
    for key, (a_id, b_id) in DIFFS.items():
        sides = [db.execute("SELECT c.vault, c.constantTypeId AS table_id FROM assignments a JOIN constantSets c ON c.id = a.constantSetId WHERE a.id = ?", (each,)).fetchone() for each in (a_id, b_id)]
        column_rows = db.execute("SELECT name, columnType FROM columns WHERE typeId = ? ORDER BY \"order\"", (sides[0]["table_id"],)).fetchall()
        width = len(column_rows)
        a_cells, b_cells = sides[0]["vault"].split("|"), sides[1]["vault"].split("|")
        rows = [[[a_cells[i], b_cells[i]] for i in range(row_i * width, (row_i + 1) * width)] for row_i in range(len(a_cells) // width)]
        golden["diff"][key] = {"a": a_id, "b": b_id, "columns": [r["name"] for r in column_rows], "rows": rows,
                               "changed_cells": sum(a != b for row in rows for a, b in row),
                               "changed_rows": [row_i for row_i, row in enumerate(rows) if any(a != b for a, b in row)]}

    # the paged data table of the 600-row assignment: its rows from the vault blob, by row index
    channels = golden["diff"]["channels"]
    golden["show_paged"] = {"id": channels["b"], "rows": [[b for _, b in row] for row in channels["rows"]]}

    table1 = db.execute("SELECT t.id, t.name, t.comment, u.name AS author FROM typeTables t JOIN users u ON u.id = t.authorId WHERE t.id = 1").fetchone()
    dir1 = db.execute("SELECT d.id, d.name, d.comment, u.name AS author FROM directories d JOIN users u ON u.id = d.authorId WHERE d.id = 1").fetchone()

    def activity(table_ids):
        """Assignment count and the newest assignment (date, author) over the tables, as the info boxes show them."""
        marks = ",".join("?" * len(table_ids))
        count = db.execute(f"SELECT COUNT(*) FROM assignments a JOIN constantSets c ON c.id = a.constantSetId WHERE c.constantTypeId IN ({marks})", table_ids).fetchone()[0]
        newest = db.execute(f"""SELECT a.created, u.name FROM assignments a JOIN constantSets c ON c.id = a.constantSetId JOIN users u ON u.id = a.authorId
                                WHERE c.constantTypeId IN ({marks}) ORDER BY a.created DESC, a.id DESC LIMIT 1""", table_ids).fetchone()
        return {"assignments": count, "last": f"{shown_stamp(newest['created'])} by {newest['name']}" if newest else "none"}

    tables_under_dir1 = [table_id for table_id, path in tables.items() if path.startswith(dirs[1] + "/")]
    golden["table_info"] = {**dict(table1), "path": tables[1], **activity([1])}
    golden["dir_info"] = {**dict(dir1), "path": dirs[1], "tables": len(tables_under_dir1), **activity(tables_under_dir1)}
    golden_path(space).write_text(json.dumps(golden, indent=1, ensure_ascii=False))
    print(f"{golden_path(space)}: {len(dirs)} directories, {len(tables)} tables, logs {golden['logs']['total']}, "
          f"versions rows {[v['count'] for v in golden['versions'].values()]}")


# ----------------------------------------------------------------------------- page readers

class TableReader(HTMLParser):
    """Collects every <table> as a list of rows; each row is the list of its cell texts (th and td).

    `cell_attrs` mirrors `tables` with the attributes of every cell (the data table marks its columns with
    data-column and data-type), and `table_attrs` holds each table's own attributes (data-lines).
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables, self.cell_attrs, self.table_attrs = [], [], []
        self.row, self.row_attrs, self.cell, self.current_attrs = None, None, None, None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "table":
            self.tables.append([])
            self.cell_attrs.append([])
            self.table_attrs.append(attrs)
        elif tag == "tr" and self.tables:
            self.row, self.row_attrs = [], []
        elif tag in ("td", "th") and self.row is not None:
            self.cell, self.current_attrs = [], attrs

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.cell is not None:
            self.row.append(" ".join("".join(self.cell).split()))
            self.row_attrs.append(self.current_attrs)
            self.cell = None
        elif tag == "tr" and self.row is not None:
            self.tables[-1].append(self.row)
            self.cell_attrs[-1].append(self.row_attrs)
            self.row = None

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)


class TreeReader(HTMLParser):
    """The tree marks every node with <li data-path="/path" data-kind="dir|table">; on the compare page a table
    node holds badges <a data-variation=".." data-count="..">, collected per table path."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.paths, self.badges = [], {}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "li" and "data-path" in attrs:
            self.paths.append((attrs["data-path"], attrs.get("data-kind") == "dir"))
        elif tag == "a" and "data-variation" in attrs and self.paths:
            self.badges.setdefault(self.paths[-1][0], {})[attrs["data-variation"]] = int(attrs["data-count"])


class LogCommentReader(HTMLParser):
    """The log record page shows the comment in <pre class="log-comment"> (absent when the comment is empty) and the
    affected objects as links inside the table #log-meta; collects the comment text and those hrefs, percent-decoded."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.comment, self.hrefs, self.inside, self.in_meta = "", [], False, False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "pre" and "log-comment" in (attrs.get("class") or ""):
            self.inside = True
        elif tag == "table" and attrs.get("id") == "log-meta":
            self.in_meta = True
        elif tag == "a" and attrs.get("href") and self.in_meta:
            self.hrefs.append(unquote(attrs["href"]))

    def handle_endtag(self, tag):
        if tag == "pre":
            self.inside = False
        elif tag == "table":
            self.in_meta = False

    def handle_data(self, data):
        if self.inside:
            self.comment += data


class PageInfoReader(HTMLParser):
    """The paginated pages carry <p data-total=".." data-pages=".."> under their table."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.total, self.pages = None, None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "data-total" in attrs:
            self.total, self.pages = int(attrs["data-total"]), int(attrs["data-pages"])


class DiffSummaryReader(HTMLParser):
    """The compare page carries <p id="diff-summary" data-cells=".." data-changed-cells=".." data-changed-rows="..">."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.values = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get("id") == "diff-summary":
            self.values = {"cells": int(attrs["data-cells"]), "changed_cells": int(attrs["data-changed-cells"]), "changed_rows": int(attrs["data-changed-rows"])}


def diff_grid(rows, attrs, lines, pair):
    """{row index: [(text, changed), ...]} of one data table of the compare page, whichever form it is rendered in.

    A body row starts with a <th scope="row">: the row index (one line per row) or the column name (one line per
    column). One line per row: the cells follow, two per column (A then B) when `pair`. One line per column: the
    first header row holds the row indexes after `column` and `type`, and a body line holds one column's values
    in the same order.
    """
    body = [(r, a) for r, a in zip(rows, attrs) if a and a[0].get("scope") == "row"]

    def cells(values, cell_attrs):
        if pair:
            return [(f"{values[i]} {values[i + 1]}", "data-changed" in cell_attrs[i]) for i in range(0, len(values), 2)]
        return [(value, "data-changed" in cell_attr) for value, cell_attr in zip(values, cell_attrs)]

    if lines == "rows":
        return {r[0]: cells(r[1:], a[1:]) for r, a in body}
    header = next(r for r, a in zip(rows, attrs) if a and a[0].get("scope") == "col")
    lines = [cells(r[2:], a[2:]) for r, a in body]  # one line per column
    return {index: [line[i] for line in lines] for i, index in enumerate(header[2:])}


def expected_grid(expected, view, side, row_indexes):
    """What diff_grid() must read for the golden diff: per cell view, a changed cell shows B then A; per column view,
    A then B; table to table, the side's own value."""
    def text(a, b):
        if view == "cells":
            return f"{b} {a}" if a != b else b
        if view == "columns":
            return f"{a} {b}"
        return b if side == "b" else a
    return {str(row_i): [(text(a, b), a != b) for a, b in expected["rows"][row_i]] for row_i in row_indexes}


def main_table(reader):
    """The table a paginated page is about: the one marked id="versions-table" when present (the versions page also
    carries the info block's table, which comes first in the document), otherwise the first table."""
    for table, attrs in zip(reader.tables, reader.table_attrs):
        if attrs.get("id") == "versions-table":
            return table
    return reader.tables[0]


def walk_pages(get, url, max_rows=None):
    """Rows of the main table of every page of a paginated route (per_page=200), the first status, and the shown total."""
    rows, page_number, status = [], 1, None
    separator = "&" if "?" in url else "?"
    while True:
        page_status, html = get(f"{url}{separator}per_page=200&page={page_number}")
        status = page_status if status is None else status
        info = PageInfoReader()
        info.feed(html)
        page = read_page(html)
        rows += data_rows(main_table(page)) if page.tables else []
        if info.pages is None or page_number >= info.pages or (max_rows and len(rows) >= max_rows):
            return status, rows, info.total
        page_number += 1


def read_tables(html):
    return read_page(html).tables


def read_page(html):
    reader = TableReader()
    reader.feed(html)
    return reader


def shown_data_table(reader, index=1):
    """Columns, types and rows of the assignment data table, whichever layout the page rendered it in."""
    rows, attrs, lines = reader.tables[index], reader.cell_attrs[index], reader.table_attrs[index].get("data-lines")
    if lines == "columns":  # one line per column: name, type, then the value of row 0, 1, ...; transpose it back
        body = rows[1:]
        values_per_column = [line[2:] for line in body]
        return [line[0] for line in body], [line[1] for line in body], [list(row) for row in zip(*values_per_column)]
    header = attrs[0]
    columns = [cell["data-column"] for cell in header if "data-column" in cell]
    types = [cell["data-type"] for cell in header if "data-type" in cell]
    return columns, types, [row[1:] for row in rows[1:]]  # the first cell of a body row is the row index


def data_rows(table):
    """Rows of a table without header rows (rows made of <th> only) — the reader does not tell th from td,
    so the header is taken as the first row."""
    return table[1:]


# ----------------------------------------------------------------------------- compare

def check(results, name, expected, actual, sample=None):
    ok = expected == actual
    results.append({"check": name, "pass": ok, "expected": expected if ok or sample is None else sample, "actual": None if ok else actual if sample is None else sample})
    return ok


def compare(space, phase, label, db_url):
    golden = json.loads(golden_path(space).read_text())
    client = make_app(db_url).test_client()
    urls = {p[0]: p[1] for p in pages.PAGES}
    results = []

    def get(label_or_url):
        response = client.get(urls.get(label_or_url, label_or_url))
        return response.status_code, response.get_data(as_text=True)

    # tree: every directory and table path present exactly once
    status, html = get("tree")
    reader = TreeReader()
    reader.feed(html)
    check(results, "tree.status", 200, status)
    shown_dirs = sorted(p for p, is_dir in reader.paths if is_dir)
    shown_tables = sorted(p for p, is_dir in reader.paths if not is_dir)
    check(results, "tree.directories", golden["tree"]["directories"], shown_dirs, sample=f"{len(golden['tree']['directories'])} expected, {len(shown_dirs)} shown; missing {sorted(set(golden['tree']['directories']) - set(shown_dirs))[:5]}")
    check(results, "tree.tables", golden["tree"]["tables"], shown_tables, sample=f"{len(golden['tree']['tables'])} expected, {len(shown_tables)} shown; missing {sorted(set(golden['tree']['tables']) - set(shown_tables))[:5]}")
    # tree order: under every parent, directories before tables and each kind in natural name order — the order the
    # page is rendered in (views.by_name) and the one tree.js restores with Sort A…Z
    siblings = {}
    for path, is_dir in reader.paths:  # document order
        parent, _, name = path.rpartition("/")
        siblings.setdefault(parent, []).append((0 if is_dir else 1, natural_key(name)))
    unsorted = sorted(parent or "/" for parent, keys in siblings.items() if keys != sorted(keys))
    check(results, "tree.order", [], unsorted[:5])

    # versions: row set, count and newest-first order
    for label_, expected in golden["versions"].items():
        status, rows, shown_total = walk_pages(get, urls[label_])
        check(results, f"{label_}.total", expected["count"], shown_total)
        def run_value(text):  # the versions page prints the open-ended run sentinel as ∞
            return INFINITE_RUN if text == "∞" else int(text) if text.isdigit() else text
        shown = [{"run_min": run_value(r[0]), "run_max": run_value(r[1]), "created": r[2], "variation": r[3]} for r in rows if len(r) >= 4]
        wanted = [{k: row[k] for k in ("run_min", "run_max", "created", "variation")} for row in expected["rows"]]
        check(results, f"{label_}.status", 200, status)
        check(results, f"{label_}.count", expected["count"], len(shown))
        key = lambda d: json.dumps(d, sort_keys=True)  # noqa: E731
        check(results, f"{label_}.rows", sorted(map(key, wanted)), sorted(map(key, shown)), sample=f"first expected {wanted[:1]}, first shown {shown[:1]}")
        check(results, f"{label_}.newest_first", [w["created"] for w in wanted[:3]], [s["created"] for s in shown[:3]])

    # show_request: metadata and data, in every layout the page offers
    for label_, golden_key in [(key, key) for key in golden["show"]] + list(SHOW_LAYOUTS.items()):
        expected = golden["show"][golden_key]
        status, html = get(label_)
        page = read_page(html)
        tables = page.tables
        meta = {row[0]: row[1] for row in (tables[0] if tables else []) if len(row) == 2}
        check(results, f"{label_}.status", 200, status)
        check(results, f"{label_}.variation", expected["variation"], meta.get("Variation"))
        check(results, f"{label_}.created", expected["created"], meta.get("Created"))
        check(results, f"{label_}.author", expected["author"], meta.get("Author"))
        run_max = "inf." if expected["run_max"] == INFINITE_RUN else str(expected["run_max"])
        check(results, f"{label_}.run_range", f"{expected['run_min']} - {run_max}", meta.get("Run Range"))
        check(results, f"{label_}.request", expected["request"], meta.get("Exact ID"))
        columns, types, data = shown_data_table(page) if len(tables) > 1 else (None, None, None)
        check(results, f"{label_}.columns", expected["columns"], columns)
        check(results, f"{label_}.types", expected["types"], types)
        check(results, f"{label_}.data", expected["data"], data)

    # assignment JSON through both addressing forms, against the same golden values as the page
    for label_, expected in golden["show"].items():
        by_request = client.get(urls[label_].replace("/show_request?", "/assignments/data.json?"))
        check(results, f"{label_}.json.status", 200, by_request.status_code)
        data = json.loads(by_request.get_data(as_text=True)) if by_request.status_code == 200 else {}
        for key in ("variation", "created", "author", "run_min", "run_max", "comment", "request", "columns", "data"):
            shown = data.get("rows") if key == "data" else [c["name"] for c in data.get("columns", [])] if key == "columns" else data.get(key)
            check(results, f"{label_}.json.{key}", expected[key], shown)
        if "id" in data:
            by_id = client.get(f"/assignments/{data['id']}/data.json")
            check(results, f"{label_}.json.same_by_id", by_request.get_data(as_text=True), by_id.get_data(as_text=True), sample="byte-identical bodies")

    # the paged data table: page 3 of the 600-row assignment holds rows 400–599 with their true indexes; page size 50 and page 12 the last 50
    expected = golden["show_paged"]
    for label_, first, last in (("assignment_channels_page3", 400, 600), ("assignment_channels_per_page50", 550, 600), ("assignment_channels_page9999", 400, 600)):
        status, html = get(label_)
        page = read_page(html)
        check(results, f"{label_}.status", 200, status)
        _, _, data = shown_data_table(page) if len(page.tables) > 1 else (None, None, None)
        check(results, f"{label_}.rows", expected["rows"][first:last], data, sample=f"rows {first}–{last - 1}")
        check(results, f"{label_}.indexes", [str(i) for i in range(first, last)], [row[0] for row in page.tables[1][1:]] if len(page.tables) > 1 else None)

    # logs: the page shows the newest 1000, newest first
    status, rows, shown_total = walk_pages(get, urls["logs"], max_rows=1000)
    shown = [{"created": r[0], "action": r[1], "description": r[2], "author": r[3]} for r in rows if len(r) >= 4][:1000]
    check(results, "logs.status", 200, status)
    check(results, "logs.count", 1000, len(shown))
    check(results, "logs.total", golden["logs"]["total"], shown_total)
    check(results, "logs.rows", golden["logs"]["newest_first_1000"], shown, sample=f"expected first {golden['logs']['newest_first_1000'][:1]}, shown first {shown[:1]}")
    check(results, "logs.newest_first", [r["created"] for r in golden["logs"]["newest_first_1000"][:2]], [r["created"] for r in shown[:2]])

    # log record pages against the database row; the list's rows link to the newest records
    for label_, expected in golden["log_record"].items():
        status, html = get(label_)
        page = read_page(html)
        meta = {row[0]: row[1] for row in (page.tables[0] if page.tables else []) if len(row) == 2}
        reader = LogCommentReader()
        reader.feed(html)
        check(results, f"{label_}.status", 200, status)
        for key, heading in (("created", "Created"), ("action", "Action"), ("author", "Author"), ("description", "Description"), ("affected", "Affected")):
            check(results, f"{label_}.{key}", expected[key], meta.get(heading))
        check(results, f"{label_}.id", str(expected["id"]), meta.get("Database id"))
        check(results, f"{label_}.comment", expected["comment"], reader.comment, sample=f"{len(expected['comment'])} characters expected, {len(reader.comment)} shown")
        check(results, f"{label_}.assignment_link", expected["assignment_link"] is not None, expected["assignment_link"] in reader.hrefs if expected["assignment_link"] else False)
        # a table, directory or variation that exists links to its page; a deleted one has no link
        check(results, f"{label_}.object_links", expected["object_links"], [h for h in reader.hrefs if h.startswith("/versions") or h.startswith("/tree?filter=")])
        check(results, f"{label_}.variation_link", expected["variation_link"], any(h.startswith("/vars") for h in reader.hrefs))
    status, html = get("logs")
    check(results, "logs.row_links", [f"/logs/{log_id}" for log_id in golden["logs"]["newest_ids"]], re.findall(r'<tr data-href="([^"]+)"', html))

    # variations: names and comments; parents are not shown today
    status, html = get("variations")
    tables = read_tables(html)
    rows = data_rows(tables[0]) if tables else []
    check(results, "variations.status", 200, status)
    check(results, "variations.names", [v["name"] for v in golden["variations"]], [r[0] for r in rows])
    check(results, "variations.comments", [" ".join((v["comment"] or "").split()) for v in golden["variations"]], [r[2] for r in rows if len(r) > 2])

    # compare variations: the affected tables with their badges, and only their ancestor directories
    for label_, expected in golden["compare"].items():
        status, html = get(label_)
        reader = TreeReader()
        reader.feed(html)
        shown_tables = sorted(p for p, is_dir in reader.paths if not is_dir)
        shown_dirs = sorted(p for p, is_dir in reader.paths if is_dir)
        ancestors = sorted({p[:i] for p in shown_tables for i in range(1, len(p)) if p[i] == "/"})
        check(results, f"{label_}.status", 200, status)
        check(results, f"{label_}.tables", sorted(expected["tables"]), shown_tables)
        check(results, f"{label_}.badges", expected["tables"], {p: reader.badges.get(p, {}) for p in shown_tables})
        check(results, f"{label_}.directories", ancestors, shown_dirs)

    # compare assignments: the summary and every data table of each view and layout against the diff of the vault blobs
    for label_, (key, view, lines, changed_only, page_number) in DIFF_PAGES.items():
        expected = golden["diff"][key]
        status, html = get(label_)
        check(results, f"{label_}.status", 200, status)
        summary = DiffSummaryReader()
        summary.feed(html)
        check(results, f"{label_}.summary", {"cells": len(expected["rows"]) * len(expected["columns"]), "changed_cells": expected["changed_cells"], "changed_rows": len(expected["changed_rows"])}, summary.values)
        kept = expected["changed_rows"] if changed_only else list(range(len(expected["rows"])))
        shown_rows = kept[(page_number - 1) * DIFF_PAGE_SIZE:page_number * DIFF_PAGE_SIZE]
        page = read_page(html)
        data_tables = [(table, attrs, table_attrs) for table, attrs, table_attrs in zip(page.tables, page.cell_attrs, page.table_attrs) if "data-view" in table_attrs]
        check(results, f"{label_}.tables", [(view, lines)] * (2 if view == "tables" else 1), [(t[2]["data-view"], t[2]["data-lines"]) for t in data_tables])
        for table, attrs, table_attrs in data_tables:
            side = table_attrs.get("data-side", "b")
            wanted = expected_grid(expected, view, side, shown_rows)
            shown = diff_grid(table, attrs, lines, pair=(view == "columns"))
            check(results, f"{label_}.grid.{side}" if view == "tables" else f"{label_}.grid", wanted, shown,
                  sample=f"{len(wanted)} rows expected, {len(shown)} shown; first expected {list(wanted.items())[:1]}, first shown {list(shown.items())[:1]}")

    # the comparison as JSON: the changed rows of the channels pair, byte-identical through both addressing forms
    expected = golden["diff"]["channels"]
    by_id = client.get(urls["diff_json"])
    check(results, "diff_json.status", 200, by_id.status_code)
    body = json.loads(by_id.get_data(as_text=True)) if by_id.status_code == 200 else {}
    check(results, "diff_json.changed_cells", expected["changed_cells"], body.get("changed_cells"))
    check(results, "diff_json.rows", [{"row": row_i, "cells": [{"a": a, "b": b, "changed": a != b} for a, b in expected["rows"][row_i]]} for row_i in expected["changed_rows"]], body.get("rows"))
    check(results, "diff_json.same_by_request", by_id.get_data(as_text=True), client.get(urls["diff_json_by_request"]).get_data(as_text=True), sample="byte-identical bodies")

    # info modals
    for label_, expected in (("table_info", golden["table_info"]), ("dir_info", golden["dir_info"])):
        status, html = get(label_)
        tables = read_tables(html)
        meta = {row[0]: row[1] for row in (tables[0] if tables else []) if len(row) == 2}
        check(results, f"{label_}.status", 200, status)
        check(results, f"{label_}.path", expected["path"], meta.get("Full path"))
        check(results, f"{label_}.author", expected["author"], meta.get("Author"))
        check(results, f"{label_}.id", str(expected["id"]), meta.get("DB ID"))
        check(results, f"{label_}.assignments", str(expected["assignments"]), meta.get("Assignments"))
        check(results, f"{label_}.last_assignment", expected["last"], meta.get("Last assignment"))
    check(results, "dir_info.tables", str(golden["dir_info"]["tables"]), meta.get("Tables"))

    out = space / "reports" / workspace.report_name("golden_compare", phase, label)
    passed = sum(1 for r in results if r["pass"])
    out.write_text(json.dumps({"phase": phase, "label": label, "passed": passed, "failed": len(results) - passed, "results": results}, indent=1, ensure_ascii=False))
    for r in results:
        if not r["pass"]:
            print(f"FAIL {r['check']}: expected {str(r['expected'])[:90]} | actual {str(r['actual'])[:90]}")
    print(f"{passed} passed, {len(results) - passed} failed -> {out}")
    return passed, len(results) - passed


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    workspace.add_space_argument(parser)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("compute", help="write golden.json from SQL on the fixture database")
    cmp = sub.add_parser("compare", help="request the pages and compare them with golden.json")
    cmp.add_argument("--label", required=True, help="part of the report name")
    cmp.add_argument("--phase", type=int, help="phase number inside a program run, part of the report name")
    cmp.add_argument("--db", help="connection string (default: the fixture database of the workspace)")
    args = parser.parse_args()
    space = workspace.resolve(args)
    if args.command == "compute":
        compute(space)
    else:
        _, failed = compare(space, args.phase, args.label, args.db or workspace.fixture_url(space))
        sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
