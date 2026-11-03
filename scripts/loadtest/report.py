#!/usr/bin/env python3
"""The tables and charts of docs/deployment/scaling.md, from the load test results (client.py reports).

    python scripts/loadtest/report.py [RESULTS_DIR]            # rewrite the page's generated part and the charts
    python scripts/loadtest/report.py [RESULTS_DIR] --check    # exit 1 when the page or a chart differs

RESULTS_DIR (default scripts/loadtest/results, the published runs) holds <configuration>_<jobs>.json. The page's text
between the markers loadtest:begin and loadtest:end is generated: the three figures of figures.py (docs/images/
scaling_*.svg, light and dark) and one table per configuration. Everything else on the page is written by hand. The output depends only on the JSON, so the docs' numbers are the measured ones.
"""
import argparse
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import figures  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
PAGE = os.path.join(REPO, "docs", "deployment", "scaling.md")
IMAGES = os.path.join(REPO, "docs", "images")
BEGIN, END = "<!-- loadtest:begin -->", "<!-- loadtest:end -->"

# The configurations in the page's order, with their headings
CONFIGURATIONS = [
    ("mysql", "MySQL directly"),
    ("api", "HTTP API, no cache"),
    ("api-nginx", "HTTP API behind nginx, a request per table"),
    ("bundle-nginx", "HTTP API behind nginx, a run bundle per job"),
    ("sqlite", "SQLite snapshot on a local file system"),
    ("sqlite-analyze", "SQLite snapshot with ANALYZE statistics"),
]
SKEW_LIMIT_S = 1.0      # a job that started this much later than planned waited for the client

def load(directory):
    """{configuration: [report, …] by jobs}"""
    runs = {}
    for path in sorted(glob.glob(os.path.join(directory, "*.json"))):
        with open(path) as stream:
            report = json.load(stream)
        if "label" not in report:              # a manifest of make_db.py, not a client report
            continue
        runs.setdefault(report["label"], []).append(report)
    for reports in runs.values():
        reports.sort(key=lambda report: report["jobs"])
    return runs


def seconds(value):
    if value is None:
        return "–"
    if value < 0.01:
        return "{0:.1f} ms".format(value * 1000)
    if value < 1:
        return "{0:.0f} ms".format(value * 1000)
    if value < 100:
        return "{0:.1f} s".format(value)
    return "{0:.0f} s".format(value)


def count(value):
    return "{0:,}".format(value).replace(",", " ")


def table(reports):
    lines = ["| jobs | failed jobs | job waits, median | p99 | request p99 | requests/s | backend requests | start skew p99 |",
             "|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for report in reports:
        result = report["result"]
        skew = result["start_skew_s"]["p99"] or 0
        lines.append("| {0} | {1} | {2} | {3} | {4} | {5} | {6} | {7}{8} |".format(
            count(report["jobs"]),
            "{0} ({1:.1%})".format(count(result["failed_jobs"]), result["error_rate"] or 0),
            seconds(result["job_duration_s"]["median"]), seconds(result["job_duration_s"]["p99"]),
            seconds(result["request_latency_s"]["p99"]), count(round(result["requests_per_s"] or 0)),
            count(result["backend_requests"]), seconds(skew), " ‡" if skew > SKEW_LIMIT_S else ""))
    errors = {}
    for report in reports:
        for kind, number in report["result"]["errors"].items():
            errors.setdefault(kind, {})[report["jobs"]] = number
    text = "\n".join(lines)
    if errors:
        text += "\n\nErrors: " + "; ".join("{0} ({1})".format(kind, ", ".join("{0} at {1} jobs".format(count(n), count(jobs))
                                                                               for jobs, n in sorted(by_jobs.items())))
                                          for kind, by_jobs in sorted(errors.items())) + "."
    return text


def generated(runs):
    parts = ["![Scaling with the number of jobs: a, the share of jobs that got their constants; b, the median wait per job; "
             "c, the requests that reached the database](../images/scaling.svg)"]
    for name, title in CONFIGURATIONS:
        if name in runs:
            parts.append("### {0}\n\n{1}".format(title, table(runs[name])))
    return "\n\n".join(parts)


def outputs(directory):
    """{path: text} of everything this script writes"""
    runs = load(directory)
    with open(PAGE) as stream:
        page = stream.read()
    pattern = re.compile(re.escape(BEGIN) + ".*?" + re.escape(END), re.S)
    if not pattern.search(page):
        raise SystemExit("{0} has no {1} … {2} block".format(PAGE, BEGIN, END))
    result = {PAGE: pattern.sub(lambda _: BEGIN + "\n" + generated(runs) + "\n" + END, page)}
    for name, text in figures.figure_files(runs).items():
        result[os.path.join(IMAGES, name)] = text
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("results", nargs="?", default=os.path.join(HERE, "results"),
                        help="directory of client.py reports (default: scripts/loadtest/results)")
    parser.add_argument("--check", action="store_true", help="compare instead of writing; exit 1 on a difference")
    args = parser.parse_args()
    different = []
    for path, text in outputs(args.results).items():
        current = open(path).read() if os.path.exists(path) else None
        if current != text:
            different.append(path)
            if not args.check:
                with open(path, "w") as stream:
                    stream.write(text)
    if args.check:
        for path in different:
            print("differs from the results: " + os.path.relpath(path, REPO))
        sys.exit(1 if different else 0)
    print("written: " + (", ".join(os.path.relpath(path, REPO) for path in different) or "nothing changed"))


if __name__ == "__main__":
    main()
