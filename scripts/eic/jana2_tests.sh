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
cmake --build "$build" --target ccdb_tests -j "$jobs"

test_db="$build/jana2_tests.sqlite"
python3 "$repo/scripts/eic/make_jana2_test_db.py" "$test_db"

CCDB_TEST_JANA2_SQLITE="$test_db" "$build/src/tests/ccdb_tests" "[jana2]"
