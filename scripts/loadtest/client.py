#!/usr/bin/env python3
"""Load test client: N jobs that start within a window and read the constants of their run (docs/deployment/scaling.md).

    python scripts/loadtest/client.py api    --base http://127.0.0.1:8080/api/v1 --manifest m.json --jobs 1000 --out r.json
    python scripts/loadtest/client.py bundle --base http://127.0.0.1:8080/api/v1 --manifest m.json --jobs 1000 --out r.json
    python scripts/loadtest/client.py mysql  --db mysql://ccdb_user@127.0.0.1:33083/ccdb_loadtest --manifest m.json ...
    python scripts/loadtest/client.py sqlite --db sqlite:////path/loadtest.sqlite --manifest m.json ...

Job i starts at a random moment of the window (--window seconds; the moments come from --seed), reads the constants of
run number i % R of R runs spread over the manifest's run numbers (--runs-used R), at the campaign time of the
manifest, in the default variation, for --tables M tables (the same M for every job, drawn with the seed), one
table after the other as a job does at its first event:
- api: GET /assignments/data?request=/path:run:default:time per table, a URL that names one assignment for good
- bundle: GET /bundle?run=…&variation=default&time=… once, in the URL form of the API's own redirect
- mysql: one connection per job; the variation and directory lookups, then per table the table lookup and the
  assignment query the C++ library sends; then the connection closes
- sqlite: the same queries on the file, opened read-only per job

--procs P processes split the jobs (job i goes to process i % P). HTTP jobs run concurrently on asyncio with at most
--connections connections per process, response bodies streamed and dropped, so a process holds no job's data; mysql and sqlite jobs run on at most --threads threads per process. A job
that starts later than its moment waited for the client, not the server: the report gives that skew, and a growing
skew means the run measured the client. --max-wall seconds after the start, jobs that have not started are abandoned
and jobs still reading stop; both count as failed, so an overloaded configuration ends.

The report (JSON): the configuration, the host (CPU count, load average), request and job latency percentiles, a
histogram of job durations, errors by kind, the client's peak memory (the sum over its processes), backend requests (HTTP: answers whose X-Cache-Status is not HIT, every
answer when there is no such header; mysql and sqlite: queries), requests per second.
"""
import argparse
import asyncio
import bisect
import collections
import json
import math
import multiprocessing
import os
import random
import resource
import sqlite3
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote, urlencode

UNFINISHED = "unfinished at the client's time limit"

# Job duration histogram: 61 edges from 1 ms to 1000 s, ten per decade
HISTOGRAM_EDGES = [10 ** (exponent / 10.0) for exponent in range(-30, 31)]

ASSIGNMENT_QUERY = (
    "SELECT `assignments`.`id`, `constantSets`.`vault` FROM `assignments` "
    "INNER JOIN `runRanges` ON `assignments`.`runRangeId` = `runRanges`.`id` "
    "INNER JOIN `constantSets` ON `assignments`.`constantSetId` = `constantSets`.`id` "
    "WHERE `runRanges`.`runMin` <= {p} AND `runRanges`.`runMax` >= {p} AND `assignments`.`variationId` = {p} "
    "AND `constantSets`.`constantTypeId` = {p} AND `assignments`.`created` <= {p} "
    "ORDER BY `assignments`.`id` DESC LIMIT 1")


# ---------------------------------------------------------------- the plan of the jobs

def job_plan(manifest, jobs, window, runs_used, tables, seed):
    """Start moments (seconds after the start), run numbers and the table paths every job reads"""
    rng = random.Random(seed)
    starts = [rng.random() * window for _ in range(jobs)]
    step = manifest["runs"] // runs_used
    runs = [(index % runs_used) * step + step // 2 for index in range(jobs)]
    paths = [table["path"] for table in rng.sample(manifest["tables"], min(tables, len(manifest["tables"])))]
    return starts, runs, paths


def api_time(campaign_time):
    """The campaign time as the API reads a bundle time: YYYY-MM-DDThh:mm:ss.ffffff"""
    return campaign_time.replace(" ", "T") + ".000000"


def job_urls(mode, base, run, paths, campaign_time):
    if mode == "bundle":
        return [base + "/bundle?" + urlencode({"run": run, "variation": "default", "time": api_time(campaign_time)})]
    return [base + "/assignments/data?request=" + quote("{0}:{1}:default:{2}".format(path, run, campaign_time), safe="/:")
            for path in paths]


# ---------------------------------------------------------------- one process

class Tally:
    """What one process measured"""

    def __init__(self):
        self.request_latencies = []
        self.job_durations = []
        self.skews = []
        self.errors = collections.Counter()
        self.backend = 0
        self.requests = 0
        self.bytes = 0
        self.failed_jobs = 0
        self.abandoned = 0
        self.last_end = 0.0
        self.lock = threading.Lock()

    def as_dict(self):
        return {"request_latencies": self.request_latencies, "job_durations": self.job_durations, "skews": self.skews,
                "errors": dict(self.errors), "backend": self.backend, "requests": self.requests, "bytes": self.bytes,
                "failed_jobs": self.failed_jobs, "abandoned": self.abandoned, "last_end": self.last_end}


async def http_process(config, mine, tally):
    import httpx
    limits = httpx.Limits(max_connections=config["connections"], max_keepalive_connections=config["connections"])
    timeout = httpx.Timeout(config["timeout"])
    loop = asyncio.get_running_loop()
    offset = time.time() - loop.time()                  # wall clock = loop.time() + offset

    async with httpx.AsyncClient(limits=limits, timeout=timeout) as client:
        async def one_job(start, run):
            await asyncio.sleep(max(0.0, config["t0"] + start - offset - loop.time()))
            began = loop.time() + offset
            if began > config["t0"] + config["max_wall"]:
                tally.abandoned += 1
                return
            tally.skews.append(began - (config["t0"] + start))
            failed = False
            for url in job_urls(config["mode"], config["base"], run, config["paths"], config["campaign_time"]):
                if loop.time() + offset > config["t0"] + config["max_wall"]:
                    tally.errors[UNFINISHED] += 1           # the client's time limit ends the run
                    failed = True
                    break
                sent = loop.time()
                try:
                    # the body is counted as it streams in and never kept: a job does not hold its bundle in memory
                    size = 0
                    async with client.stream("GET", url) as response:
                        async for chunk in response.aiter_bytes():
                            size += len(chunk)
                    tally.request_latencies.append(loop.time() - sent)
                    tally.requests += 1
                    tally.bytes += size
                    if response.headers.get("x-cache-status", "MISS") != "HIT":
                        tally.backend += 1
                    if response.status_code != 200:
                        tally.errors["http {0}".format(response.status_code)] += 1
                        failed = True
                except httpx.HTTPError as error:
                    tally.request_latencies.append(loop.time() - sent)
                    tally.requests += 1
                    tally.errors[type(error).__name__] += 1
                    failed = True
            ended = loop.time() + offset
            tally.job_durations.append(ended - began)
            tally.last_end = max(tally.last_end, ended)
            tally.failed_jobs += failed

        await asyncio.gather(*(one_job(start, run) for start, run in mine))


def sql_job(config, start, run, tally):
    """One job on MySQL or SQLite: connect, look up, one query per table, close"""
    time.sleep(max(0.0, config["t0"] + start - time.time()))
    began = time.time()
    if began > config["t0"] + config["max_wall"]:
        with tally.lock:
            tally.abandoned += 1
        return
    queries, failed, error_kind = 0, False, None
    marker = "%s" if config["mode"] == "mysql" else "?"
    query = ASSIGNMENT_QUERY.format(p=marker)
    if config["mode"] == "sqlite":
        query = query.replace("`", '"')
    connection = None
    latencies = []

    def execute(cursor, sql, parameters=()):
        nonlocal queries
        sent = time.time()
        cursor.execute(sql, parameters)
        rows = cursor.fetchall()
        latencies.append(time.time() - sent)
        queries += 1
        return rows

    size = 0
    try:
        if config["mode"] == "mysql":
            import pymysql
            connection = pymysql.connect(connect_timeout=config["timeout"], read_timeout=config["timeout"], **config["mysql"])
        else:
            connection = sqlite3.connect("file:{0}?mode=ro".format(config["sqlite"]), uri=True, timeout=config["timeout"],
                                         check_same_thread=False)
        cursor = connection.cursor()
        variation = execute(cursor, "SELECT id FROM variations WHERE name = 'default'")[0][0]
        directories = {}
        for directory_id, name, parent in execute(cursor, "SELECT id, name, parentId FROM directories"):
            directories[directory_id] = (name, parent)
        paths = {}
        for directory_id in directories:
            parts, current = [], directory_id
            while current in directories:
                parts.append(directories[current][0])
                current = directories[current][1]
            paths["/" + "/".join(reversed(parts))] = directory_id
        for path in config["paths"]:
            if time.time() > config["t0"] + config["max_wall"]:
                raise TimeoutError(UNFINISHED)          # the client's time limit ends the run
            directory, name = path.rsplit("/", 1)
            table = execute(cursor, "SELECT id FROM typeTables WHERE directoryId = {0} AND name = {0}".format(marker),
                            (paths[directory], name))[0][0]
            rows = execute(cursor, query, (run, run, variation, table, config["campaign_time_text"]))
            if not rows:
                raise LookupError("no assignment")
            size += len(rows[0][1])
    except Exception as error:                          # any failure is a failed job, counted by its kind
        failed = True
        code = getattr(error, "args", [None])[0]
        error_kind = UNFINISHED if str(error) == UNFINISHED else \
            "{0} {1}".format(type(error).__name__, code if isinstance(code, int) else "").strip()
    finally:
        if connection is not None:
            try:
                connection.close()
            except Exception:
                pass
    ended = time.time()
    with tally.lock:
        tally.skews.append(began - (config["t0"] + start))
        tally.request_latencies.extend(latencies)
        tally.requests += queries
        tally.backend += queries
        tally.bytes += size
        tally.job_durations.append(ended - began)
        tally.last_end = max(tally.last_end, ended)
        if failed:
            tally.failed_jobs += 1
            tally.errors[error_kind] += 1


def run_process(config):
    starts, runs = config["starts"], config["runs"]
    mine = [(starts[index], runs[index]) for index in range(config["process"], len(starts), config["procs"])]
    tally = Tally()
    if config["mode"] in ("api", "bundle"):
        asyncio.run(http_process(config, mine, tally))
    else:
        with ThreadPoolExecutor(max_workers=config["threads"]) as pool:
            for start, run in sorted(mine):
                pool.submit(sql_job, config, start, run, tally)
    result = tally.as_dict()
    result["peak_rss_mb"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0     # this process's peak memory
    return result


# ---------------------------------------------------------------- the report

def percentile(sorted_values, share):
    """Nearest-rank percentile of sorted values; None for none"""
    if not sorted_values:
        return None
    rank = max(1, math.ceil(share / 100.0 * len(sorted_values)))
    return sorted_values[rank - 1]


def histogram(values):
    """Counts per bin of HISTOGRAM_EDGES: bin k holds values in [edge k-1, edge k); first and last bins are open"""
    counts = [0] * (len(HISTOGRAM_EDGES) + 1)
    for value in values:
        counts[bisect.bisect_right(HISTOGRAM_EDGES, value)] += 1
    return counts


def summarize(parts, t0):
    """The report numbers of the processes' tallies"""
    requests = sorted(value for part in parts for value in part["request_latencies"])
    jobs = sorted(value for part in parts for value in part["job_durations"])
    skews = sorted(value for part in parts for value in part["skews"])
    errors = collections.Counter()
    for part in parts:
        errors.update(part["errors"])
    total_requests = sum(part["requests"] for part in parts)
    wall = max([part["last_end"] for part in parts] + [t0]) - t0

    def stats(values):
        return {"median": percentile(values, 50), "p90": percentile(values, 90), "p99": percentile(values, 99),
                "max": values[-1] if values else None}

    abandoned = sum(part.get("abandoned", 0) for part in parts)
    failed = sum(part["failed_jobs"] for part in parts) + abandoned
    if abandoned:
        errors["abandoned: the client's time limit"] = abandoned
    return {"jobs": len(jobs) + abandoned, "failed_jobs": failed, "abandoned_jobs": abandoned,
            "requests": total_requests, "backend_requests": sum(part["backend"] for part in parts),
            "bytes": sum(part["bytes"] for part in parts), "errors": dict(sorted(errors.items())),
            "error_rate": failed / (len(jobs) + abandoned) if jobs or abandoned else None,
            "wall_s": wall, "requests_per_s": total_requests / wall if wall > 0 else None,
            "client_peak_rss_mb": sum(part.get("peak_rss_mb", 0) for part in parts),
            "request_latency_s": stats(requests), "job_duration_s": stats(jobs), "start_skew_s": stats(skews),
            "job_duration_histogram": histogram(jobs)}


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("mode", choices=["api", "bundle", "mysql", "sqlite"])
    parser.add_argument("--manifest", required=True, help="the manifest of make_db.py")
    parser.add_argument("--base", help="the API base URL, http://host:port/api/v1 (api, bundle)")
    parser.add_argument("--db", help="mysql://user@host:port/database or sqlite:////path (mysql, sqlite)")
    parser.add_argument("--jobs", type=int, default=1000)
    parser.add_argument("--window", type=float, default=600.0, help="seconds over which the jobs start (default 600)")
    parser.add_argument("--runs-used", type=int, default=100, help="distinct runs the jobs read (default 100)")
    parser.add_argument("--tables", type=int, default=200, help="tables per job (default 200)")
    parser.add_argument("--procs", type=int, default=max(1, (os.cpu_count() or 2) // 2))
    parser.add_argument("--connections", type=int, default=64, help="HTTP connections per process (default 64)")
    parser.add_argument("--threads", type=int, default=64, help="mysql and sqlite threads per process (default 64)")
    parser.add_argument("--timeout", type=float, default=120.0, help="seconds per request or connection (default 120)")
    parser.add_argument("--max-wall", type=float, help="seconds after which jobs that have not started are abandoned and "
                        "jobs still reading stop, both counted as failed (default three windows)")
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--label", default="", help="a name for the configuration, kept in the report")
    parser.add_argument("--out", required=True, help="the report JSON")
    args = parser.parse_args()

    with open(args.manifest) as stream:
        manifest = json.load(stream)
    starts, runs, paths = job_plan(manifest, args.jobs, args.window, args.runs_used, args.tables, args.seed)
    config = {"mode": args.mode, "base": (args.base or "").rstrip("/"), "paths": paths, "starts": starts, "runs": runs,
              "campaign_time": manifest["campaign_time"], "campaign_time_text": manifest["campaign_time"] + ".000000",
              "procs": args.procs, "connections": args.connections, "threads": args.threads, "timeout": args.timeout,
              "max_wall": args.max_wall or 3 * args.window}
    if args.mode == "mysql":
        from sqlalchemy.engine import make_url
        url = make_url(args.db.replace("mysql://", "mysql+pymysql://", 1))
        config["mysql"] = {"host": url.host, "port": url.port or 3306, "user": url.username, "password": url.password or "",
                           "database": url.database}
    if args.mode == "sqlite":
        config["sqlite"] = args.db[len("sqlite:///"):]

    load_before = os.getloadavg()
    config["t0"] = time.time() + 2.0                    # every process starts its clock at the same moment
    with multiprocessing.get_context("fork").Pool(args.procs) as pool:
        parts = pool.map(run_process, [dict(config, process=index) for index in range(args.procs)])
    report = {"label": args.label, "mode": args.mode, "jobs": args.jobs, "window_s": args.window, "runs_used": args.runs_used,
              "tables": len(paths), "procs": args.procs, "connections_per_proc": args.connections,
              "threads_per_proc": args.threads, "max_wall_s": config["max_wall"], "seed": args.seed,
              "database": {key: manifest[key] for key in ("scale", "seed", "runs", "assignments", "sets")},
              "host": {"cpus": os.cpu_count(), "load_before": load_before, "load_after": os.getloadavg()},
              "result": summarize(parts, config["t0"])}
    with open(args.out, "w") as stream:
        json.dump(report, stream, indent=1)
    result = report["result"]
    print("{0} {1}: jobs {2}, failed {3}, requests {4} ({5:.0f}/s), backend {6}, job median {7:.3f} s, p99 {8:.3f} s, "
          "skew p99 {9:.3f} s, errors {10}".format(
              args.mode, args.label, result["jobs"], result["failed_jobs"], result["requests"], result["requests_per_s"] or 0,
              result["backend_requests"], result["job_duration_s"]["median"] or 0, result["job_duration_s"]["p99"] or 0,
              result["start_skew_s"]["p99"] or 0, result["errors"]))


if __name__ == "__main__":
    main()
