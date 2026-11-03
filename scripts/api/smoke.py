"""API smoke suite: request every URL in pages.py and record status, bytes, time and SQL query count.

Usage:
    python scripts/api/smoke.py --space DIR --label LABEL [--phase N] [--db CONNECTION] [--repeat 1] [--base-url URL] [--check]

Writes <space>/reports/api_smoke_[phase<N>_]<label>.json and prints one line per URL. Without --db the fixture
database of the workspace (scripts/webgui/make_fixture.py) is used, in-process through FastAPI's TestClient; with
--base-url a live server is requested instead, for example the container behind nginx (no query counts then).

--check exits with 1 when a status is outside what the URL's kind allows (pages.ALLOWED_STATUS), on any 5xx, or when
the stored OpenAPI document (scripts/api/openapi.json) differs from the served one: a change of the API is a
reviewed diff of that file (write it with --write-openapi).
"""
import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from sqlalchemy import event
from sqlalchemy.engine import Engine

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "webgui"))      # workspace.py; pages.py below must be this directory's
sys.path.insert(0, str(HERE))
import pages  # noqa: E402
import workspace  # noqa: E402

OPENAPI_FILE = HERE / "openapi.json"
query_count = [0]


@event.listens_for(Engine, "before_cursor_execute")
def count_query(conn, cursor, statement, parameters, context, executemany):
    query_count[0] += 1


class HttpClient:
    """The TestClient calls the suite needs, over HTTP for a live server; redirects are not followed"""

    class Response:
        def __init__(self, status, body, headers):
            self.status_code, self.content, self.headers = status, body, headers

    class _NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None

    def __init__(self, base_url):
        self.base_url = base_url.rstrip("/")
        self.opener = urllib.request.build_opener(self._NoRedirect())

    def get(self, url, follow_redirects=False):
        try:
            with self.opener.open(self.base_url + url, timeout=300) as response:
                return self.Response(response.status, response.read(), response.headers)
        except urllib.error.HTTPError as error:
            return self.Response(error.code, error.read(), error.headers)


def make_client(args, space):
    if args.base_url:
        return HttpClient(args.base_url)
    from fastapi.testclient import TestClient
    from ccdb.api import create_app
    return TestClient(create_app(args.db or workspace.fixture_url(space)))


def fetch(client, url):
    """A response, following one redirect for a bundle: its explicit form is what a job downloads"""
    response = client.get(url, follow_redirects=False)
    return response


def measure(client, url, repeat, live):
    best_ms, record = None, None
    for _ in range(repeat):
        query_count[0] = 0
        started = time.perf_counter()
        response = fetch(client, url)
        elapsed_ms = (time.perf_counter() - started) * 1000
        if record is None:
            record = dict(status=response.status_code, bytes=len(response.content), content_type=response.headers.get("content-type"),
                          cache=response.headers.get("cache-control"), etag=response.headers.get("etag"),
                          queries=None if live else query_count[0], location=response.headers.get("location"))
        best_ms = elapsed_ms if best_ms is None else min(best_ms, elapsed_ms)
    record["ms"] = round(best_ms, 1)
    return record


def problem(kind, status):
    if status >= 500:
        return "server error"
    if kind in pages.ALLOWED_STATUS and status not in pages.ALLOWED_STATUS[kind]:
        return "expected " + " or ".join(str(each) for each in pages.ALLOWED_STATUS[kind])
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    workspace.add_space_argument(parser)
    parser.add_argument("--label", required=True)
    parser.add_argument("--phase", type=int)
    parser.add_argument("--db", help="connection string (default: the fixture database of the workspace)")
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--base-url", help="request a live server (http://host:port) instead of the in-process app")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--write-openapi", action="store_true", help="store the served OpenAPI document as scripts/api/openapi.json")
    args = parser.parse_args()

    space = workspace.resolve(args)
    client = make_client(args, space)
    results = []
    print(f"{'label':24} {'status':>6} {'ms':>9} {'kB':>8} {'queries':>7}  cache")
    for label, url, kind in pages.PAGES:
        record = dict(label=label, url=url, kind=kind, **measure(client, url, args.repeat, bool(args.base_url)))
        results.append(record)
        print(f"{label:24} {record['status']:>6} {record['ms']:>9.1f} {record['bytes'] / 1024:>8.1f} {str(record['queries']):>7}  {record['cache']}")

    out = space / "reports" / workspace.report_name("api_smoke", args.phase, args.label)
    summary = dict(phase=args.phase, label=args.label, db=args.base_url or args.db or workspace.fixture_url(space), repeat=args.repeat,
                   taken=time.strftime("%Y-%m-%dT%H:%M:%S"), total_ms=round(sum(r["ms"] for r in results), 1),
                   status_counts={}, results=results)
    for record in results:
        summary["status_counts"][str(record["status"])] = summary["status_counts"].get(str(record["status"]), 0) + 1
    out.write_text(json.dumps(summary, indent=1, ensure_ascii=False))
    print(f"total {summary['total_ms']:.0f} ms, statuses {summary['status_counts']} -> {out}")

    served = json.loads(client.get("/api/v1/openapi.json").content)
    if args.write_openapi:
        OPENAPI_FILE.write_text(json.dumps(served, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
        print(f"wrote {OPENAPI_FILE}")
    if args.check:
        failures = [(r["label"], r["status"], problem(r["kind"], r["status"])) for r in results if problem(r["kind"], r["status"])]
        stored = json.loads(OPENAPI_FILE.read_text()) if OPENAPI_FILE.exists() else None
        for label, status, why in failures:
            print(f"FAIL {label}: status {status}, {why}")
        if stored != served:
            print(f"FAIL openapi: the served document differs from {OPENAPI_FILE}; review the change and rerun with --write-openapi")
            failures.append(("openapi", None, "differs"))
        if failures:
            sys.exit(1)


if __name__ == "__main__":
    main()
