"""Smoke suite: request every URL in pages.py and record status, bytes, time, SQL query count.

Usage:
    python smoke.py --space DIR --label LABEL [--phase N] [--db CONNECTION] [--repeat 1] [--only a,b] [--base-url URL] [--check]

Writes <space>/reports/smoke_[phase<N>_]<label>.json and prints one line per URL. Without --db the
fixture database of the workspace is used; with --base-url a live server (gunicorn, a container) is
requested instead of the in-process app.

The app runs in-process through the Flask test client, so timings exclude the network and the
query counter sees every statement. Two traps: the counter listens on the Engine class and not on an
instance, so it sees whichever engine the app creates; and Flask's TESTING mode would re-raise
exceptions instead of returning 500, hiding exactly the failures this suite records.

--check turns the run into a gate and exits with 1 on a failure: a status of 500 or more fails any
URL; page and fragment URLs must answer 200; data URLs 200 or a 302 to the data; edge URLs anything
below 500.
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

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pages  # noqa: E402
import workspace  # noqa: E402

ALLOWED_STATUS = {"page": (200,), "fragment": (200,), "data": (200, 302)}

query_count = [0]


@event.listens_for(Engine, "before_cursor_execute")
def count_query(conn, cursor, statement, parameters, context, executemany):
    query_count[0] += 1


def make_app(connection_string):
    from ccdb.webgui import cerate_ccdb_flask_app
    return cerate_ccdb_flask_app(connection_string)


class HttpClient:
    """Flask-test-client lookalike over HTTP, for a live server. Redirects are not followed."""

    class Response:
        def __init__(self, status, body, headers):
            self.status_code, self._body, self.headers = status, body, headers
            self.content_type = headers.get("Content-Type")

        def get_data(self):
            return self._body

    def __init__(self, base_url):
        self.base_url = base_url.rstrip("/")
        self.opener = urllib.request.build_opener(_NoRedirect())

    def get(self, url):
        try:
            with self.opener.open(self.base_url + url, timeout=120) as response:
                return self.Response(response.status, response.read(), response.headers)
        except urllib.error.HTTPError as error:
            return self.Response(error.code, error.read(), error.headers)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def measure(client, url, repeat):
    """Request the URL `repeat` times; keep the fastest time and the first response's other numbers."""
    best_ms = None
    live = isinstance(client, HttpClient)  # over HTTP the query counter sees nothing
    for _ in range(repeat):
        query_count[0] = 0
        started = time.perf_counter()
        response = client.get(url)
        body = response.get_data()
        elapsed_ms = (time.perf_counter() - started) * 1000
        if best_ms is None:
            record = dict(status=response.status_code, bytes=len(body), content_type=response.content_type,
                          queries=None if live else query_count[0], location=response.headers.get("Location"))
        best_ms = elapsed_ms if best_ms is None else min(best_ms, elapsed_ms)
    record["ms"] = round(best_ms, 1)
    return record


def problem(kind, status):
    """Why a status fails --check, or None when it passes."""
    if status >= 500:
        return "server error"
    if kind in ALLOWED_STATUS and status not in ALLOWED_STATUS[kind]:
        return "expected " + " or ".join(str(s) for s in ALLOWED_STATUS[kind])
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    workspace.add_space_argument(parser)
    parser.add_argument("--label", required=True, help="part of the report name")
    parser.add_argument("--phase", type=int, help="phase number inside a program run, part of the report name")
    parser.add_argument("--db", help="connection string (default: the fixture database of the workspace)")
    parser.add_argument("--repeat", type=int, default=1, help="requests per URL; the fastest time is kept")
    parser.add_argument("--only", help="comma-separated labels from pages.py")
    parser.add_argument("--base-url", help="request a live server (http://host:port) instead of the in-process app")
    parser.add_argument("--check", action="store_true", help="exit with 1 when a status is outside what the URL's kind allows")
    args = parser.parse_args()

    space = workspace.resolve(args)
    db = args.db or workspace.fixture_url(space)
    client = HttpClient(args.base_url) if args.base_url else make_app(db).test_client()
    wanted = set(args.only.split(",")) if args.only else None
    results = []
    print(f"{'label':22} {'status':>6} {'ms':>9} {'kB':>8} {'queries':>7}  content-type")
    for label, url, kind in pages.PAGES:
        if wanted and label not in wanted:
            continue
        record = dict(label=label, url=url, kind=kind, **measure(client, url, args.repeat))
        results.append(record)
        print(f"{label:22} {record['status']:>6} {record['ms']:>9.1f} {record['bytes'] / 1024:>8.1f} {str(record['queries']):>7}  {record['content_type']}")

    out = space / "reports" / workspace.report_name("smoke", args.phase, args.label)
    summary = dict(phase=args.phase, label=args.label, db=args.base_url or db, repeat=args.repeat, taken=time.strftime("%Y-%m-%dT%H:%M:%S"),
                   total_ms=round(sum(r["ms"] for r in results), 1), status_counts={}, results=results)
    for r in results:
        summary["status_counts"][str(r["status"])] = summary["status_counts"].get(str(r["status"]), 0) + 1
    out.write_text(json.dumps(summary, indent=1, ensure_ascii=False))
    print(f"total {summary['total_ms']:.0f} ms, statuses {summary['status_counts']} -> {out}")

    if args.check:
        failures = [(r["label"], r["status"], problem(r["kind"], r["status"])) for r in results if problem(r["kind"], r["status"])]
        for label, status, why in failures:
            print(f"FAIL {label}: status {status}, {why}")
        print(f"check: {len(results) - len(failures)} passed, {len(failures)} failed")
        sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
