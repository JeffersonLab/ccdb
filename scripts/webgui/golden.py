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
import sqlite3
import sys
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pages  # noqa: E402
import workspace  # noqa: E402
from smoke import make_app  # noqa: E402  (the pages are requested the way the smoke suite does)

INFINITE_RUN = 2147483647


def golden_path(space):
    return space / "reports" / "golden.json"

SHOW_REQUESTS = {  # label in pages.py -> (table path, run, variation)
    "show_small": (pages.SMALL_TABLE, 0, "default"),
    "show_big": (pages.BIG_TABLE, 1500, "default"),
    "show_big_mc": (pages.BIG_TABLE, 1500, "mc"),
    "show_hostile": (pages.HOSTILE_TABLE, 0, "default"),
}
VERSIONS = {"versions_big": pages.BIG_TABLE, "versions_small": pages.SMALL_TABLE, "versions_deep": pages.DEEP_TABLE,
            "versions_hostile": pages.HOSTILE_TABLE, "versions_unicode": pages.UNICODE_TABLE}


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
        columns = [r["name"] for r in db.execute("SELECT name FROM columns WHERE typeId = ? ORDER BY \"order\"", (table_id,))]
        rows_count = db.execute("SELECT nRows FROM typeTables WHERE id = ?", (table_id,)).fetchone()[0]
        match = [r for r in assignments_of(db, table_id) if r["variation"] == variation and r["runMin"] <= run <= r["runMax"]]
        newest = match[0]  # assignments_of is newest first; the CLI picks the newest too
        cells = newest["vault"].split("|")
        data = [cells[i * len(columns):(i + 1) * len(columns)] for i in range(rows_count)]
        golden["show"][label] = {"path": path, "variation": variation, "created": shown_stamp(newest["created"]), "author": newest["author"],
                                 "run_min": newest["runMin"], "run_max": newest["runMax"], "comment": newest["comment"],
                                 "request": request_string(path, newest["runMin"], variation, parse_stamp(newest["created"])),
                                 "columns": columns, "data": data, "candidates": len(match)}

    logs = db.execute("SELECT l.created, l.action, l.description, u.name AS author FROM logs l JOIN users u ON u.id = l.authorId ORDER BY l.id DESC").fetchall()
    golden["logs"] = {"total": len(logs), "newest_first_1000": [{**dict(r), "created": shown_stamp(r["created"])} for r in logs[:1000]]}

    variations = db.execute("SELECT v.name, v.created, v.comment, p.name AS parent FROM variations v LEFT JOIN variations p ON p.id = v.parentId ORDER BY v.id").fetchall()
    golden["variations"] = [{**dict(r), "created": shown_stamp(r["created"])} for r in variations]

    table1 = db.execute("SELECT t.id, t.name, t.comment, u.name AS author FROM typeTables t JOIN users u ON u.id = t.authorId WHERE t.id = 1").fetchone()
    dir1 = db.execute("SELECT d.id, d.name, d.comment, u.name AS author FROM directories d JOIN users u ON u.id = d.authorId WHERE d.id = 1").fetchone()
    golden["table_info"] = {**dict(table1), "path": tables[1]}
    golden["dir_info"] = {**dict(dir1), "path": dirs[1]}
    golden_path(space).write_text(json.dumps(golden, indent=1, ensure_ascii=False))
    print(f"{golden_path(space)}: {len(dirs)} directories, {len(tables)} tables, logs {golden['logs']['total']}, "
          f"versions rows {[v['count'] for v in golden['versions'].values()]}")


# ----------------------------------------------------------------------------- page readers

class TableReader(HTMLParser):
    """Collects every <table> as a list of rows; each row is the list of its cell texts (th and td)."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables, self.row, self.cell, self.attrs = [], None, None, []

    def handle_starttag(self, tag, attrs):
        self.attrs.append(dict(attrs))
        if tag == "table":
            self.tables.append([])
        elif tag == "tr" and self.tables:
            self.row = []
        elif tag in ("td", "th") and self.row is not None:
            self.cell = []

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.cell is not None:
            self.row.append(" ".join("".join(self.cell).split()))
            self.cell = None
        elif tag == "tr" and self.row is not None:
            self.tables[-1].append(self.row)
            self.row = None

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)


class TreeReader(HTMLParser):
    """The tree marks every node with <li data-path="/path" data-kind="dir|table">."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.paths = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "li" and "data-path" in attrs:
            self.paths.append((attrs["data-path"], attrs.get("data-kind") == "dir"))


class PageInfoReader(HTMLParser):
    """The paginated pages carry <p data-total=".." data-pages=".."> under their table."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.total, self.pages = None, None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "data-total" in attrs:
            self.total, self.pages = int(attrs["data-total"]), int(attrs["data-pages"])


def walk_pages(get, url, max_rows=None):
    """Rows of the first table of every page of a paginated route (per_page=200), the first status, and the shown total."""
    rows, page_number, status = [], 1, None
    separator = "&" if "?" in url else "?"
    while True:
        page_status, html = get(f"{url}{separator}per_page=200&page={page_number}")
        status = page_status if status is None else status
        info = PageInfoReader()
        info.feed(html)
        tables = read_tables(html)
        rows += data_rows(tables[0]) if tables else []
        if info.pages is None or page_number >= info.pages or (max_rows and len(rows) >= max_rows):
            return status, rows, info.total
        page_number += 1


def read_tables(html):
    reader = TableReader()
    reader.feed(html)
    return reader.tables


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

    # show_request: metadata and data
    for label_, expected in golden["show"].items():
        status, html = get(label_)
        tables = read_tables(html)
        meta = {row[0]: row[1] for row in (tables[0] if tables else []) if len(row) == 2}
        check(results, f"{label_}.status", 200, status)
        check(results, f"{label_}.variation", expected["variation"], meta.get("Variation"))
        check(results, f"{label_}.created", expected["created"], meta.get("Created"))
        check(results, f"{label_}.author", expected["author"], meta.get("Author"))
        run_max = "inf." if expected["run_max"] == INFINITE_RUN else str(expected["run_max"])
        check(results, f"{label_}.run_range", f"{expected['run_min']} - {run_max}", meta.get("Run Range"))
        check(results, f"{label_}.request", expected["request"], meta.get("Exact ID"))
        data_table = tables[1] if len(tables) > 1 else []
        check(results, f"{label_}.columns", expected["columns"], data_table[0] if data_table else None)
        check(results, f"{label_}.data", expected["data"], data_rows(data_table))

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

    # logs: the page shows the newest 1000, newest first
    status, rows, shown_total = walk_pages(get, urls["logs"], max_rows=1000)
    shown = [{"created": r[0], "action": r[1], "description": r[2], "author": r[3]} for r in rows if len(r) >= 4][:1000]
    check(results, "logs.status", 200, status)
    check(results, "logs.count", 1000, len(shown))
    check(results, "logs.total", golden["logs"]["total"], shown_total)
    check(results, "logs.rows", golden["logs"]["newest_first_1000"], shown, sample=f"expected first {golden['logs']['newest_first_1000'][:1]}, shown first {shown[:1]}")
    check(results, "logs.newest_first", [r["created"] for r in golden["logs"]["newest_first_1000"][:2]], [r["created"] for r in shown[:2]])

    # variations: names and comments; parents are not shown today
    status, html = get("variations")
    tables = read_tables(html)
    rows = data_rows(tables[0]) if tables else []
    check(results, "variations.status", 200, status)
    check(results, "variations.names", [v["name"] for v in golden["variations"]], [r[0] for r in rows])
    check(results, "variations.comments", [" ".join((v["comment"] or "").split()) for v in golden["variations"]], [r[2] for r in rows if len(r) > 2])

    # info modals
    for label_, expected in (("table_info", golden["table_info"]), ("dir_info", golden["dir_info"])):
        status, html = get(label_)
        tables = read_tables(html)
        meta = {row[0]: row[1] for row in (tables[0] if tables else []) if len(row) == 2}
        check(results, f"{label_}.status", 200, status)
        check(results, f"{label_}.path", expected["path"], meta.get("Full path"))
        check(results, f"{label_}.author", expected["author"], meta.get("Author"))
        check(results, f"{label_}.id", str(expected["id"]), meta.get("DB ID"))

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
