#!/usr/bin/env bash
# Builds the C++ library with the JANA2 service and runs the [jana2] tests. Runs inside the eic-shell image:
#
#   scripts/eic/run_in_eic_shell.sh scripts/eic/jana2_tests.sh            # on a host with docker
#   scripts/eic/jana2_tests.sh                                            # already inside eic-shell (CI)
#
# CCDB_JANA2_BUILD_DIR sets the build tree (default build/jana2 in the checkout; build/ is ignored by git).
# CCDB_TEST_JANA2_HTTP_URL adds the HTTP case: the HTTP API on the demo tables (scripts/demo/make_epic_tables.py),
# e.g. the demo stack (docker/demo) or `ccdb -c sqlite:///demo.sqlite api --port 8765`; the [jana2] tests and
# ccdb_epic_demo then also read through it.
# For the http(s) resources of CCDB_service::GetResource the script serves the test resource directory itself
# with `python3 -m http.server` on 127.0.0.1 (a free port) and sets CCDB_TEST_JANA2_HTTP_RESOURCE_BASE to it.
set -euo pipefail

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
build="${CCDB_JANA2_BUILD_DIR:-$repo/build/jana2}"
jobs="$(( $(nproc) > 4 ? $(nproc) - 2 : $(nproc) ))"

cmake -S "$repo/cpp" -B "$build" -DCCDB_BUILD_JANA2=ON -DCMAKE_BUILD_TYPE=RelWithDebInfo
cmake --build "$build" --target ccdb_tests ccdb_epic_demo -j "$jobs"

test_db="$build/jana2_tests.sqlite"

# The resources served over HTTP: a free loopback port, the tables point at it, then the server on the directory
# the database script writes (<db>.resource). The port is chosen before the server binds it; nothing else binds
# loopback ports in this script, and the tests wait until the server answers.
http_port="$(python3 -c 'import socket; s = socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1])')"
export CCDB_TEST_JANA2_HTTP_RESOURCE_BASE="http://127.0.0.1:$http_port"
python3 "$repo/scripts/eic/make_jana2_test_db.py" "$test_db"

http_log="$build/http_resource_server.log"
python3 -m http.server "$http_port" --bind 127.0.0.1 --directory "$test_db.resource" > "$http_log" 2>&1 &
http_pid=$!
trap 'kill "$http_pid" 2>/dev/null || true' EXIT
python3 - "$CCDB_TEST_JANA2_HTTP_RESOURCE_BASE/weights.bin" <<'PY'
import sys, time, urllib.request
for _ in range(100):
    try:
        urllib.request.urlopen(sys.argv[1], timeout=1).read(1)
        sys.exit(0)
    except Exception:
        time.sleep(0.1)
sys.exit("the resource http.server did not answer within 10 s")
PY
echo "resources served at $CCDB_TEST_JANA2_HTTP_RESOURCE_BASE (log $http_log)"

if [ -n "${CCDB_TEST_JANA2_HTTP_URL:-}" ]; then
    export CCDB_HTTP_CACHE_DIR="$build/http_cache"
    rm -rf "$CCDB_HTTP_CACHE_DIR"
fi
CCDB_TEST_JANA2_SQLITE="$test_db" "$build/src/tests/ccdb_tests" "[jana2]"

# The ePIC demo application on the demo tables: once by variation and run, once by the campaign tag
demo_db="$build/epic_demo.sqlite"
python3 "$repo/scripts/demo/make_epic_tables.py" "sqlite:///$demo_db" > /dev/null
newest="$("$build/jana2/ccdb_epic_demo" "sqlite:///$demo_db")"
tagged="$("$build/jana2/ccdb_epic_demo" "sqlite:///$demo_db" campaign_demo)"
echo "$newest"; echo "$tagged"
echo "$newest" | grep -q "run 1500  /epic/TOFBarrel/lgad_calibration  cSlope=1.18760244e-06  tSlope=0.02456308082  tIntercept=0.05114"
echo "$tagged" | grep -q "run 1500  /epic/TOFBarrel/lgad_calibration  cSlope=1.18760244e-06  tSlope=0.02456308082  tIntercept=0.04314"
echo "$newest" | grep -q "run 500  /epic/TOFBarrel/lgad_calibration  cSlope=1.175844e-06  tSlope=0.024319882  tIntercept=0.04314"
echo "ccdb_epic_demo: the constants switch at run 1000 and the tag keeps the earlier offset"

if [ -n "${CCDB_TEST_JANA2_HTTP_URL:-}" ]; then
    # the same application through the HTTP API: the same lines
    newest_http="$("$build/jana2/ccdb_epic_demo" "$CCDB_TEST_JANA2_HTTP_URL")"
    tagged_http="$("$build/jana2/ccdb_epic_demo" "$CCDB_TEST_JANA2_HTTP_URL" campaign_demo)"
    [ "$(echo "$newest_http" | grep '^run ')" = "$(echo "$newest" | grep '^run ')" ]
    [ "$(echo "$tagged_http" | grep '^run ')" = "$(echo "$tagged" | grep '^run ')" ]
    echo "ccdb_epic_demo through $CCDB_TEST_JANA2_HTTP_URL: the same constants as from the file"
fi
