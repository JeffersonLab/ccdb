#!/usr/bin/env bash
# Builds the C++ library with the DD4hep plugins and runs the [dd4hep] tests. Runs inside the eic-shell image:
#
#   scripts/eic/run_in_eic_shell.sh scripts/eic/dd4hep_tests.sh            # on a host with docker
#   scripts/eic/dd4hep_tests.sh                                            # already inside eic-shell (CI)
#
# CCDB_DD4HEP_BUILD_DIR sets the build tree (default build/dd4hep in the checkout; build/ is ignored by git).
set -euo pipefail

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
build="${CCDB_DD4HEP_BUILD_DIR:-$repo/build/dd4hep}"
jobs="$(( $(nproc) > 4 ? $(nproc) - 2 : $(nproc) ))"

cmake -S "$repo/cpp" -B "$build" -DCCDB_BUILD_DD4HEP=ON -DCMAKE_BUILD_TYPE=RelWithDebInfo
cmake --build "$build" --target ccdb_dd4hep Components_ccdb_dd4hep ccdb_dd4hep_tests -j "$jobs"

test_db="$build/dd4hep_tests.sqlite"
python3 "$repo/scripts/eic/make_dd4hep_test_db.py" "$test_db"

# DD4hep's plugin manager finds CCDB_Constants and CCDB_ConditionsLoader through the .components file on LD_LIBRARY_PATH;
# the test program does not link the plugin library, so this is the only way it can find them
components="$build/lib/CCDB/dd4hep"
test -s "$components/libccdb_dd4hep.components" || { echo "$components/libccdb_dd4hep.components was not generated" >&2; exit 1; }
grep -q CCDB_Constants "$components/libccdb_dd4hep.components" || { echo "libccdb_dd4hep.components lists no CCDB_Constants" >&2; exit 1; }
LD_LIBRARY_PATH="$components:${LD_LIBRARY_PATH:-}" CCDB_TEST_DD4HEP_SQLITE="$test_db" "$build/dd4hep/ccdb_dd4hep_tests"

# The tutorial, end to end (docs/apis/dd4hep-tutorial.md): the database made with the ccdb commands of the page,
# the example program run for two runs and a tag, its printed values checked
CCDB_DD4HEP_BUILD_DIR="$build" "$repo/scripts/eic/dd4hep_example.sh"
