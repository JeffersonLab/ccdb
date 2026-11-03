#!/usr/bin/env bash
# Builds the C++ library with the JANA2 service and runs the [jana2] tests. Runs inside the eic-shell image:
#
#   scripts/eic/run_in_eic_shell.sh scripts/eic/jana2_tests.sh            # on a host with docker
#   scripts/eic/jana2_tests.sh                                            # already inside eic-shell (CI)
#
# CCDB_JANA2_BUILD_DIR sets the build tree (default build/jana2 in the checkout; build/ is ignored by git).
set -euo pipefail

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
build="${CCDB_JANA2_BUILD_DIR:-$repo/build/jana2}"
jobs="$(( $(nproc) > 4 ? $(nproc) - 2 : $(nproc) ))"

cmake -S "$repo/cpp" -B "$build" -DCCDB_BUILD_JANA2=ON -DCMAKE_BUILD_TYPE=RelWithDebInfo
cmake --build "$build" --target ccdb_tests ccdb_epic_demo -j "$jobs"

test_db="$build/jana2_tests.sqlite"
python3 "$repo/scripts/eic/make_jana2_test_db.py" "$test_db"

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
