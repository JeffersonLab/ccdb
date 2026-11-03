#!/usr/bin/env python3
"""Runs the [http] and [http_cache] tests of ccdb_tests (test_HTTPProvider.cc) against the CCDB HTTP API.

    python cpp/src/tests/http_harness.py --tests <build>/ccdb_tests --db sqlite:////path/time.sqlite [--work DIR]

The database is the one scripts/time/make_time_db.py writes. The harness starts the API on it twice, on free ports of
127.0.0.1, the second answering with a wrong X-CCDB-SHA256 header (their output goes to api.log and
api_bad_sha256.log in the work directory); runs the [http] tests with an empty cache directory; stops both servers;
then runs the [http_cache] tests, which read the bundles the first run left in that
cache. The exit code is 0 when both runs pass. Needs the api extra (FastAPI, uvicorn).
"""
import argparse
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request


def free_port():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def wrong_sha256(app):
    """The application with every X-CCDB-SHA256 header replaced by 64 zeros"""
    async def wrapped(scope, receive, send):
        async def rewrite(message):
            if message["type"] == "http.response.start":
                message["headers"] = [(name, b"0" * 64 if name.lower() == b"x-ccdb-sha256" else value)
                                      for name, value in message["headers"]]
            await send(message)
        await app(scope, receive, rewrite)
    return wrapped


def serve(db, port, bad_sha256):
    import uvicorn
    from ccdb.api import create_app
    app = create_app(db)
    uvicorn.run(wrong_sha256(app) if bad_sha256 else app, host="127.0.0.1", port=port, log_level="warning")


def start(db, port, bad_sha256, env, log_path):
    """The API in a process of its own, its output in log_path; returns the process and its base URL once it answers"""
    command = [sys.executable, os.path.abspath(__file__), "serve", "--db", db, "--port", str(port)]
    log = open(log_path, "w")
    process = subprocess.Popen(command + (["--bad-sha256"] if bad_sha256 else []), env=env, stdout=log, stderr=subprocess.STDOUT)
    url = "http://127.0.0.1:{0}/api/v1".format(port)
    no_proxy = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    deadline, last_error = time.time() + 120, None
    while time.time() < deadline:
        if process.poll() is not None:
            break
        try:
            with no_proxy.open(url + "/health", timeout=5):
                return process, url
        except OSError as error:
            last_error = error
            time.sleep(0.2)
    if process.poll() is None:
        process.terminate()
        process.wait(timeout=30)
    log.close()
    with open(log_path) as output:
        raise RuntimeError("the API on port {0} did not answer (exit code {1}, last error {2}); its output:\n{3}".format(
            port, process.returncode, last_error, output.read()[-4000:]))


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command")
    run = sub.add_parser("run")
    run.add_argument("--tests", required=True, help="the ccdb_tests executable")
    run.add_argument("--db", required=True, help="sqlite:///… of the time database")
    run.add_argument("--work", help="directory for the caches; a temporary one by default, removed after")
    one = sub.add_parser("serve")
    one.add_argument("--db", required=True)
    one.add_argument("--port", type=int, required=True)
    one.add_argument("--bad-sha256", action="store_true")
    arguments = sys.argv[1:]
    if arguments and arguments[0] not in ("run", "serve", "-h", "--help"):
        arguments = ["run"] + arguments
    args = parser.parse_args(arguments)

    if args.command == "serve":
        serve(args.db, args.port, args.bad_sha256)
        return 0

    work = args.work or tempfile.mkdtemp(prefix="ccdb_http_tests_")
    cache = os.path.join(work, "client_cache")
    shutil.rmtree(cache, ignore_errors=True)
    os.makedirs(cache)
    env = dict(os.environ, CCDB_API_CACHE_DIR=os.path.join(work, "api_cache"))
    servers = []
    try:
        good, url = start(args.db, free_port(), False, env, os.path.join(work, "api.log"))
        servers.append(good)
        bad, bad_url = start(args.db, free_port(), True, env, os.path.join(work, "api_bad_sha256.log"))
        servers.append(bad)
        tests_env = dict(os.environ, CCDB_TEST_HTTP_URL=url, CCDB_TEST_HTTP_BAD_URL=bad_url,
                         CCDB_TEST_TIME_SQLITE_CONNECTION=args.db, CCDB_HTTP_CACHE_DIR=cache)
        live = subprocess.call([args.tests, "[http]"], env=tests_env)
    finally:
        for server in servers:
            server.terminate()
            server.wait(timeout=30)
    cached = subprocess.call([args.tests, "[http_cache]"], env=tests_env)
    if not args.work:
        shutil.rmtree(work, ignore_errors=True)
    print("http_harness: [http] rc={0}, [http_cache] rc={1}".format(live, cached))
    return 0 if live == 0 and cached == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
