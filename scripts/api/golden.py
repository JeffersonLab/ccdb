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

IMMUTABLE = "public, max-age=31536000, immutable"
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
        if not (url.startswith("/api/v1/tables/") and kind == "json" and "/versions" not in url and "/schema" not in url):
            continue
        from urllib.parse import unquote
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
