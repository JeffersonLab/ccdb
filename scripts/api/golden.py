"""API golden checks: every value the API serves for the fixture, against SQL on the fixture and against the web GUI.

Usage:
    python scripts/api/golden.py --space DIR --label LABEL [--phase N]

The expected values are read from the fixture database with SQL each run, so nothing is stored to go stale:
- the data forms of every assignment in pages.DATA_ASSIGNMENTS: data.json and data.txt byte-identical to the web
  GUI's; the raw `data` equal to constantSets.vault; X-CCDB-SHA256, the ETag and SHA-256 over the served bytes all
  equal to constantSets.sha256, X-CCDB-Size to constantSets.size;
- the columns, units and assignment counts of the tables in pages.py, the tags and their UTC times;
- the comparison JSON and diff equal to the web GUI's;
- the cache rule of each address form;
- a bundle by tag reads, for every table, what the fixture reads with that tag.
Writes <space>/reports/api_golden_[phase<N>_]<label>.json; exits with 1 on any failure.
"""
import argparse
import hashlib
import json
import os
import sqlite3
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "webgui"))      # workspace.py; pages.py below must be this directory's
sys.path.insert(0, str(HERE))
import pages  # noqa: E402
import workspace  # noqa: E402
from urllib.parse import unquote

IMMUTABLE = "public, max-age=31536000, immutable"
HOURLY = "public, max-age=3600"
SHORT = "public, max-age=60"


class Checks:
    def __init__(self):
        self.results = []

    def equal(self, name, got, expected):
        passed = got == expected
        self.results.append(dict(name=name, passed=passed, **({} if passed else {"got": repr(got)[:300], "expected": repr(expected)[:300]})))
        if not passed:
            print(f"FAIL {name}: got {repr(got)[:160]}, expected {repr(expected)[:160]}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    workspace.add_space_argument(parser)
    parser.add_argument("--label", required=True)
    parser.add_argument("--phase", type=int)
    args = parser.parse_args()
    space = workspace.resolve(args)
    fixture = workspace.fixture_path(space)
    connection = workspace.fixture_url(space)

    os.environ.setdefault("CCDB_API_CACHE_DIR", tempfile.mkdtemp(prefix="ccdb_api_golden_"))
    from fastapi.testclient import TestClient
    from ccdb import AlchemyProvider
    from ccdb.api import create_app
    from ccdb.webgui import cerate_ccdb_flask_app
    api = TestClient(create_app(connection))
    gui = cerate_ccdb_flask_app(connection).test_client()
    sql = sqlite3.connect("file:{0}?mode=ro".format(fixture), uri=True)
    checks = Checks()

    def get(url):
        return api.get(url, follow_redirects=False)

    for assignment_id in pages.DATA_ASSIGNMENTS:
        vault, sha256, size = sql.execute("SELECT c.vault, c.sha256, c.size FROM assignments a JOIN constantSets c "
                                          "ON c.id = a.constantSetId WHERE a.id = ?", (assignment_id,)).fetchone()
        raw = get(f"/api/v1/assignments/{assignment_id}/data")
        checks.equal(f"{assignment_id} data is the vault", raw.content, vault.encode("utf-8"))
        checks.equal(f"{assignment_id} served bytes hash", hashlib.sha256(raw.content).hexdigest(), sha256)
        checks.equal(f"{assignment_id} X-CCDB-SHA256", raw.headers["x-ccdb-sha256"], sha256)
        checks.equal(f"{assignment_id} ETag", raw.headers["etag"], f'"{sha256}"')
        checks.equal(f"{assignment_id} X-CCDB-Size", int(raw.headers["x-ccdb-size"]), size)
        checks.equal(f"{assignment_id} cache", raw.headers["cache-control"], IMMUTABLE)
        for form in ("data.json", "data.txt"):
            checks.equal(f"{assignment_id} {form} equals the GUI's", get(f"/api/v1/assignments/{assignment_id}/{form}").content,
                         gui.get(f"/assignments/{assignment_id}/{form}").get_data())
        info = get(f"/api/v1/assignments/{assignment_id}").json()
        checks.equal(f"{assignment_id} info sha256", info["sha256"], sha256)

    for label, url, kind in pages.PAGES:
        if not (url.startswith("/api/v1/tables/") and kind == "json" and "/versions" not in url and "/schema" not in url
                and "/card" not in url):
            continue
        path = unquote(url[len("/api/v1/tables"):])
        info = get(url).json()
        name = path.rsplit("/", 1)[1]
        rows = sql.execute("SELECT c.name, c.columnType, c.units FROM columns c JOIN typeTables t ON t.id = c.typeId "
                           "WHERE t.name = ? ORDER BY c.\"order\"", (name,)).fetchall()
        checks.equal(f"{label} columns", [(each["name"], each["type"], each["units"]) for each in info["columns"]],
                     [(column, kind_, units or None) for column, kind_, units in rows])
        count = sql.execute("SELECT COUNT(*) FROM assignments a JOIN constantSets c ON c.id = a.constantSetId JOIN typeTables t "
                            "ON t.id = c.constantTypeId WHERE t.name = ?", (name,)).fetchone()[0]
        checks.equal(f"{label} assignment count", info["assignments"], count)

    # Data cards: versions, coverage per variation, authors, the newest assignment and the covering tags, by SQL
    for label, url, kind in pages.PAGES:
        if not (kind == "json" and url.endswith("/card")):
            continue
        path = unquote(url[len("/api/v1/tables"):-len("/card")])
        card = get(url).json()
        directory_id = 0
        for part in path.strip("/").split("/")[:-1]:
            directory_id = sql.execute("SELECT id FROM directories WHERE name = ? AND parentId = ?", (part, directory_id)).fetchone()[0]
        table_id = sql.execute("SELECT id FROM typeTables WHERE name = ? AND directoryId = ?", (path.rsplit("/", 1)[1], directory_id)).fetchone()[0]
        rows = sql.execute("SELECT v.name, r.runMin, r.runMax, u.name, a.created, a.variationId FROM assignments a "
                           "JOIN constantSets s ON a.constantSetId = s.id JOIN variations v ON a.variationId = v.id "
                           "JOIN runRanges r ON a.runRangeId = r.id LEFT JOIN users u ON a.authorId = u.id "
                           "WHERE s.constantTypeId = ? ORDER BY a.created, a.id", (table_id,)).fetchall()
        ranges, authors = {}, {}
        for variation, run_min, run_max, author, _, _ in rows:
            ranges.setdefault(variation, []).append((run_min, run_max))
            authors[author or ""] = authors.get(author or "", 0) + 1
        coverage = []
        for name, found in sorted(ranges.items()):
            merged = []
            for low, high in sorted(found):
                if merged and low <= merged[-1][1] + 1:
                    merged[-1][1] = max(merged[-1][1], high)
                else:
                    merged.append([low, high])
            coverage.append({"name": name, "versions": len(found), "runs": merged})
        covering = []
        for tag, variation_id, snapshot in sql.execute("SELECT name, variationId, snapshotTime FROM tags ORDER BY name").fetchall():
            chain, current = [], variation_id
            while current:
                chain.append(current)
                current = sql.execute("SELECT parentId FROM variations WHERE id = ?", (current,)).fetchone()[0]
            if any(row[5] in chain and row[4] <= snapshot for row in rows):
                covering.append(tag)
        checks.equal(f"{label} versions", card["versions"], len(rows))
        checks.equal(f"{label} coverage", card["variations"], coverage)
        checks.equal(f"{label} authors", card["authors"],
                     [{"name": name, "assignments": n} for name, n in sorted(authors.items(), key=lambda item: (-item[1], item[0]))])
        checks.equal(f"{label} tags", card["tags"], covering)
        if rows:
            checks.equal(f"{label} last change", (card["last_change"]["author"], card["last_change"]["variation"]),
                         (rows[-1][3] or "", rows[-1][0]))

    # The readiness profile: the counts that need no time window, straight from SQL
    profile = get("/api/v1/readiness").json()
    for group, field, query in (
            ("metadata", "columns", "SELECT COUNT(*) FROM columns"),
            ("metadata", "columns_with_units", "SELECT COUNT(*) FROM columns WHERE TRIM(COALESCE(units, '')) <> ''"),
            ("metadata", "tables", "SELECT COUNT(*) FROM typeTables"),
            ("metadata", "tables_with_description", "SELECT COUNT(*) FROM typeTables WHERE TRIM(COALESCE(comment, '')) <> ''"),
            ("metadata", "versions", "SELECT COUNT(*) FROM assignments"),
            ("metadata", "versions_with_comment", "SELECT COUNT(*) FROM assignments WHERE TRIM(COALESCE(comment, '')) <> ''"),
            ("history", "open_ended_run_ranges", "SELECT COUNT(*) FROM assignments a JOIN runRanges r ON r.id = a.runRangeId "
                                                 "WHERE r.runMax = 2147483647 AND r.runMin > 0"),
            ("history", "versions_by_anonymous", "SELECT COUNT(*) FROM assignments a JOIN users u ON u.id = a.authorId "
                                                 "WHERE u.name = 'anonymous'"),
            ("history", "deprecated_tables", "SELECT COUNT(*) FROM typeTables WHERE isDeprecated = 1"),
            ("history", "tags", "SELECT COUNT(*) FROM tags"),
            ("data", "constant_sets", "SELECT COUNT(*) FROM constantSets"),
            ("data", "shared_sets", "SELECT COUNT(*) FROM (SELECT constantSetId FROM assignments GROUP BY constantSetId "
                                    "HAVING COUNT(*) > 1)")):
        checks.equal(f"readiness {group}.{field}", profile[group][field], sql.execute(query).fetchone()[0])

    # The card as schema.org JSON-LD: one variableMeasured per column, with its units, in column order
    for label, url, kind in pages.PAGES:
        if not (kind == "json" and url.endswith("/card?format=jsonld")):
            continue
        name = unquote(url[len("/api/v1/tables"):-len("/card?format=jsonld")]).rsplit("/", 1)[1]
        record = get(url).json()
        rows = sql.execute("SELECT c.name, c.units FROM columns c JOIN typeTables t ON t.id = c.typeId WHERE t.name = ? "
                           "ORDER BY c.\"order\"", (name,)).fetchall()
        checks.equal(f"{label} variableMeasured", [(each["name"], each.get("unitText")) for each in record["variableMeasured"]],
                     [(column, units or None) for column, units in rows])
        checks.equal(f"{label} type", (record["@context"], record["@type"]), ("https://schema.org", "Dataset"))

    # The change feed: the newest log records, newest first
    from xml.etree import ElementTree
    feed = ElementTree.fromstring(get("/api/v1/logs.atom").content)
    atom = "{http://www.w3.org/2005/Atom}"
    newest = [row[0] for row in sql.execute("SELECT id FROM logs ORDER BY id DESC LIMIT 50")]
    checks.equal("feed entries are the newest log records", [int(entry.find(atom + "id").text.rsplit(":", 1)[1])
                                                              for entry in feed.findall(atom + "entry")], newest)

    big_total = sql.execute("SELECT COUNT(*) FROM assignments a JOIN constantSets c ON c.id = a.constantSetId JOIN typeTables t "
                            "ON t.id = c.constantTypeId WHERE t.name = 'gains'").fetchone()[0]
    checks.equal("versions total of the big table", get("/api/v1/tables" + pages.BIG_TABLE + "/versions").json()["total"], big_total)

    tags = sorted((name, snapshot) for name, snapshot in sql.execute("SELECT name, snapshotTime FROM tags"))
    served = sorted((each["name"], each["time"]) for each in get("/api/v1/tags").json())
    checks.equal("tags and their UTC times", served,
                 [(name, snapshot.replace(" ", "T") + ("" if "." in snapshot else ".000000") + "Z") for name, snapshot in tags])

    checks.equal("compare JSON equals the GUI's", get("/api/v1/compare?a=3612&b=3613").content,
                 gui.get("/compare/data.json?a=3612&b=3613&changed=0").get_data())
    checks.equal("compare diff equals the GUI's", get("/api/v1/compare.diff?a=3612&b=3613").content,
                 gui.get("/compare/data.diff?a=3612&b=3613").get_data())

    for label, url, kind in pages.PAGES:
        response = get(url)
        if kind == "redirect":
            checks.equal(f"{label} redirect cache", response.headers.get("cache-control"), SHORT)
        elif label in ("tables", "variations", "tags", "logs", "versions_big"):
            checks.equal(f"{label} list cache", response.headers.get("cache-control"), SHORT)
        elif label in ("readiness", "readiness_window"):
            checks.equal(f"{label} hourly cache", response.headers.get("cache-control"), HOURLY)
        elif label in ("assignment", "assignment_exact", "assignment_tag", "bundle_tag"):
            checks.equal(f"{label} immutable", response.headers.get("cache-control"), IMMUTABLE)

    bundle = get("/api/v1/bundle?run=1500&tag=fixture_past")
    checks.equal("bundle hash header", bundle.headers.get("x-ccdb-sha256"), hashlib.sha256(bundle.content).hexdigest())
    with tempfile.TemporaryDirectory() as directory:
        path = os.path.join(directory, "bundle.sqlite")
        with open(path, "wb") as stream:
            stream.write(bundle.content)
        source, copy = AlchemyProvider(), AlchemyProvider()
        source.connect(connection)
        copy.connect("sqlite:///" + path)
        source.get_root_directory()
        compared = 0
        for table in source.search_type_tables("*"):
            try:
                expected = source.get_assignment_by_request("{0}:1500@fixture_past".format(table.path)).constant_set.vault
            except Exception:
                expected = None
            try:
                got = copy.get_assignment_by_request("{0}:1500@fixture_past".format(table.path)).constant_set.vault
            except Exception:
                got = None
            checks.equal(f"bundle by tag {table.path}", got, expected)
            compared += expected is not None
        checks.equal("bundle by tag has constants", compared > 0, True)
        source.disconnect()
        copy.disconnect()

    passed = sum(each["passed"] for each in checks.results)
    failed = len(checks.results) - passed
    out = space / "reports" / workspace.report_name("api_golden", args.phase, args.label)
    out.write_text(json.dumps(dict(label=args.label, phase=args.phase, taken=time.strftime("%Y-%m-%dT%H:%M:%S"),
                                   passed=passed, failed=failed, results=checks.results), indent=1, ensure_ascii=False))
    print(f"{passed} passed, {failed} failed -> {out}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
