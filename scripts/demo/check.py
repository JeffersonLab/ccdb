#!/usr/bin/env python3
"""Checks the running demo (docker/demo/compose.yml): waits for the API and the web GUI, then requests the demo's URLs.

    python scripts/demo/check.py [--api http://localhost:8080] [--gui http://localhost:5000] [--timeout 300]

Every URL must answer the status listed with it; the API's run bundle of the campaign tag must hold the tag's TOF
offset. Exit code 0 when everything answers as listed. No dependency beyond the Python standard library.
"""
import argparse
import json
import sqlite3
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

TOF = "/epic/TOFBarrel/lgad_calibration"

API_URLS = [
    ("/api/v1/health", 200),
    ("/api/v1/instance", 200),
    ("/api/v1/directories/epic", 200),
    ("/api/v1/tables/epic/HCal/adc_calib", 200),
    ("/api/v1/tables/epic/HCal/adc_calib/versions", 200),
    ("/api/v1/tags/campaign_demo", 200),
    ("/api/v1/assignments?request=" + urllib.parse.quote(TOF + ":1500"), 302),
    ("/api/v1/assignments/data.json?request=" + urllib.parse.quote(TOF + ":1500@campaign_demo"), 200),
    ("/api/v1/tables/epic/DRICH/quantum_efficiency/schema", 200),
    ("/api/v1/bundle?run=1500&tag=campaign_demo", 200),
    ("/api/v1/tables/epic/NoSuch/table", 404),
]
GUI_URLS = [
    ("/health", 200),
    ("/", 200),
    ("/versions/epic/TOFBarrel/lgad_calibration", 200),
    ("/tags/campaign_demo?run=1500", 200),
    ("/show_request?request=" + urllib.parse.quote(TOF + ":1500"), 200),
]


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


OPENER = urllib.request.build_opener(NoRedirect())


def get(url):
    try:
        with OPENER.open(url, timeout=120) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()


def wait_for(url, timeout):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if get(url)[0] == 200:
                return True
        except (urllib.error.URLError, ConnectionError, OSError):
            pass
        time.sleep(2)
    return False


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--api", default="http://localhost:8080")
    parser.add_argument("--gui", default="http://localhost:5000")
    parser.add_argument("--timeout", type=float, default=300)
    args = parser.parse_args()

    failures = []
    for base, health in ((args.api, "/api/v1/health"), (args.gui, "/health")):
        if not wait_for(base + health, args.timeout):
            print(f"FAIL {base}{health} did not answer 200 within {args.timeout:.0f} s")
            return 1
    for base, urls in ((args.api, API_URLS), (args.gui, GUI_URLS)):
        for path, expected in urls:
            status, body = get(base + path)
            mark = "ok  " if status == expected else "FAIL"
            print(f"{mark} {status} {base}{path}")
            if status != expected:
                failures.append(path)
            if path.startswith("/api/v1/bundle") and status == 200:
                with tempfile.NamedTemporaryFile(suffix=".sqlite") as bundle:
                    bundle.write(body)
                    bundle.flush()
                    with sqlite3.connect(bundle.name) as connection:
                        tags = [row[0] for row in connection.execute("SELECT name FROM tags")]
                print(f"     bundle {len(body)} bytes, tags {tags}")
                if tags != ["campaign_demo"]:
                    failures.append("bundle tag")
            if "campaign_demo" in path and "data.json" in path and status == 200:
                offset = json.loads(body)["rows"][0][3]
                print(f"     tIntercept under the tag: {offset}")
                if offset != "0.04314":
                    failures.append("tag offset")
    print(f"{len(failures)} failures")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
