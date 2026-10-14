#!/usr/bin/env python3
"""Browser check of the CCDB web GUI: a screenshot plus console, network and layout metrics per page.

Usage, from an environment that has ccdb, Flask and Playwright (the browsers come from `playwright install chromium firefox`):
    python browse.py --space DIR [--label ci] [--phase N] [--feature navbar] [--pages tree,variations] [--browser all] [--check]
    uv run --project {repo} --with playwright==<version of the installed browsers> python scripts/webgui/browse.py ...

The script starts the Flask app on the given database, visits every page from pages.BROWSER_PAGES
in each browser x viewport x color scheme, saves a screenshot per visit and stops the app at the end.
Screenshots go to <space>/plots/<phase or label>/<feature>/, the JSON report to <space>/reports/.

--check turns the run into a gate and exits with 1 on a failure: every page must answer 200 with no
console error, no page error, no failed request and no horizontal overflow; an edge page must answer
4xx, and its own status is the one failed response and the one Chromium console line allowed.
"""
import argparse
import json
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
import workspace  # noqa: E402
from pages import BROWSER_PAGES  # noqa: E402

VIEWPORTS = {
    "desktop": {"viewport": {"width": 1400, "height": 900}},
    "phone": {"viewport": {"width": 390, "height": 844}, "device_scale_factor": 2},
}
THEMES = ("light", "dark")
NAVIGATION_TIMEOUT_MS = 120_000  # the tree page renders every table and takes long


def port_open(port):
    with socket.socket() as sock:
        return sock.connect_ex(("127.0.0.1", port)) == 0


def start_server(db, port, log_path):
    """Flask's development server on ccdbweb:app, run with this script's interpreter from python/, where ccdbweb.py lives."""
    if port_open(port):
        sys.exit(f"port {port} is already in use; stop that server first")
    env = dict(os.environ, CCDB_CONNECTION=db)
    command = [sys.executable, "-m", "flask", "--app", "ccdbweb:app", "run", "-p", str(port)]
    with open(log_path, "ab") as log:
        proc = subprocess.Popen(command, cwd=workspace.REPO / "python", env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    for _ in range(300):
        if port_open(port):
            return proc
        if proc.poll() is not None:
            break
        time.sleep(0.1)
    stop_server(proc)
    sys.exit(f"Flask did not answer on port {port} within 30 s; see {log_path}")


def stop_server(proc):
    # The server runs in its own session: kill the whole group, so a child process does not outlive the wrapper.
    if proc.poll() is None:
        os.killpg(proc.pid, signal.SIGTERM)
        proc.wait(timeout=10)


def visit(page, url, offline=False, open_details=0):
    if offline:  # the CDN-blocked run: anything not served by the dev server is aborted and counted as failed
        page.route("**/*", lambda route: route.continue_() if route.request.url.startswith("http://127.0.0.1") else route.abort())
    console_errors, page_errors, failed, responses = [], [], [], []
    page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
    page.on("pageerror", lambda err: page_errors.append(str(err)))
    page.on("requestfailed", lambda req: failed.append(f"{req.url} {req.failure}"))
    page.on("response", lambda resp: responses.append(resp))
    started = time.monotonic()
    status, navigation_error = None, None
    try:
        main = page.goto(url, wait_until="networkidle", timeout=NAVIGATION_TIMEOUT_MS)
        status = main.status if main else None
    except Exception as err:  # a timeout is a measurement, not a crash of the whole run
        navigation_error = str(err).splitlines()[0]
    ms = round((time.monotonic() - started) * 1000)
    if open_details:  # show the tree with its first folders open, so the screenshot tells more than a closed list
        page.evaluate("n => document.querySelectorAll('#tree > ul > li > details').forEach((d, i) => { if (i < n) d.open = true })", open_details)
    failed += [f"{resp.url} {resp.status}" for resp in responses if resp.status >= 400]
    body_bytes = 0
    for resp in responses:
        try:
            body_bytes += resp.request.sizes()["responseBodySize"]
        except Exception:  # a request aborted mid-flight has no sizes
            pass
    return {
        "url": url, "status": status, "ms": ms, "bytes": body_bytes, "navigation_error": navigation_error,
        "console_errors": console_errors, "page_errors": page_errors, "failed_requests": failed,
        "horizontal_overflow": page.evaluate("document.scrollingElement.scrollWidth > window.innerWidth"),
        "dom_nodes": page.evaluate("document.getElementsByTagName('*').length"),
    }


def problems(record):
    """Why a visit fails --check; an empty list is a pass."""
    found = []
    edge = record["kind"] == "edge"
    status = record["status"]
    if record["navigation_error"]:
        found.append(f"navigation: {record['navigation_error']}")
    elif edge and not (status and 400 <= status < 500):
        found.append(f"status {status}, an edge page answers 4xx")
    elif not edge and status != 200:
        found.append(f"status {status}")
    # The edge page's own 4xx is expected: Playwright lists it as a failed response and Chromium logs it as a console error.
    own = f"{record['url']} {status}"
    found += [f"failed request {f}" for f in record["failed_requests"] if not (edge and f == own)]
    found += [f"console: {m}" for m in record["console_errors"] if not (edge and m.startswith("Failed to load resource"))]
    found += [f"page error: {e}" for e in record["page_errors"]]
    if record["horizontal_overflow"]:
        found.append("horizontal overflow")
    return found


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    workspace.add_space_argument(ap)
    ap.add_argument("--db", help="sqlite file or connection string (default: the fixture database of the workspace)")
    ap.add_argument("--label", help="part of the report name and, without --phase, of the screenshot directory")
    ap.add_argument("--phase", type=int, help="phase number inside a program run, part of the report and directory names")
    ap.add_argument("--feature", help="screenshot subdirectory, one per feature of the visual loop")
    ap.add_argument("--browser", default="chromium", choices=["chromium", "firefox", "all"])
    ap.add_argument("--offline", action="store_true", help="block every host except the dev server (the CDN-blocked gate run)")
    ap.add_argument("--open-details", type=int, default=0, help="open the first N top-level <details> of #tree before the screenshot")
    ap.add_argument("--pages", help="comma-separated labels from pages.BROWSER_PAGES; default all")
    ap.add_argument("--port", type=int, default=5057)
    ap.add_argument("--check", action="store_true", help="exit with 1 when a visit fails the gate rules")
    ap.add_argument("--out-json", help="override of the report path")
    ap.add_argument("--plots-dir", help="override of the screenshot directory")
    args = ap.parse_args()

    space = workspace.resolve(args)
    db = args.db or str(workspace.fixture_path(space))
    if "://" not in db:  # SQLAlchemy creates a missing sqlite file silently, and every page then fails
        if not Path(db).exists():
            sys.exit(f"database file not found: {db}")
        db = f"sqlite:///{Path(db).resolve()}"
    browsers = ["chromium", "firefox"] if args.browser == "all" else [args.browser]
    wanted = set(args.pages.split(",")) if args.pages else None
    pages = [p for p in BROWSER_PAGES if wanted is None or p[0] in wanted]
    # Report browse_phase2_navbar_gate.json inside a program run; browse_ci.json outside one.
    run_name = f"phase{args.phase}" if args.phase is not None else (args.label or "browse")
    name_parts = [run_name, args.feature, args.label if args.phase is not None else None]
    out_json = Path(args.out_json or space / "reports" / ("browse_" + "_".join(part for part in name_parts if part) + ".json"))
    plots = Path(args.plots_dir or space / "plots" / run_name / (args.feature or ""))
    plots.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)

    records = []
    server = start_server(db, args.port, space / "reports" / "browse_server.log")
    try:
        with sync_playwright() as pw:
            for browser_name in browsers:
                browser = getattr(pw, browser_name).launch()
                for viewport_name, viewport in VIEWPORTS.items():
                    for theme in THEMES:
                        context_args = dict(viewport, color_scheme=theme)
                        if viewport_name == "phone" and browser_name == "chromium":
                            context_args.update(is_mobile=True, has_touch=True)  # firefox rejects is_mobile
                        for label, path, kind in pages:
                            # One context per page: a shared context caches assets across pages, and Chromium then
                            # reports responseBodySize -1 for cached responses, which hides the real page weight.
                            context = browser.new_context(**context_args)
                            page = context.new_page()
                            record = visit(page, f"http://127.0.0.1:{args.port}{path}", args.offline, args.open_details)
                            shot = plots / f"{label}_{browser_name}_{viewport_name}_{theme}.png"
                            page.screenshot(path=shot)
                            page.close()
                            context.close()
                            record.update(label=label, kind=kind, browser=browser_name, viewport=viewport_name, theme=theme, screenshot=str(shot))
                            records.append(record)
                            print(f"{label:18} {browser_name:8} {viewport_name:7} {theme:5} {record['status'] or 'ERR':>4} {record['ms']:7} ms"
                                  f" {record['bytes'] // 1024:6} kB  errors {len(record['console_errors']) + len(record['page_errors']):3}"
                                  f"  failed {len(record['failed_requests']):3}  overflow {record['horizontal_overflow']}")
                browser.close()
    finally:
        stop_server(server)

    summary = {
        "db": db, "browsers": browsers, "records": len(records),
        "not_ok_status": sum(1 for r in records if not r["status"] or r["status"] >= 400),
        "console_errors": sum(len(r["console_errors"]) + len(r["page_errors"]) for r in records),
        "failed_requests": sum(len(r["failed_requests"]) for r in records),
        "horizontal_overflow": sum(1 for r in records if r["horizontal_overflow"]),
        "slowest_ms": max((r["ms"] for r in records), default=0),
    }
    out_json.write_text(json.dumps({"summary": summary, "records": records}, indent=1))
    print(f"summary: {json.dumps(summary)}\nreport: {out_json}\nscreenshots: {plots}")

    if args.check:
        failed = 0
        for record in records:
            for why in problems(record):
                failed += 1
                print(f"FAIL {record['label']} {record['browser']} {record['viewport']} {record['theme']}: {why}")
        print(f"check: {len(records)} visits, {failed} failures")
        sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
