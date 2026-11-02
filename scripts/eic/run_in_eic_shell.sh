#!/usr/bin/env bash
# Runs one command inside the ePIC software image (eic-shell) with this repository mounted at /ccdb.
#
#   scripts/eic/run_in_eic_shell.sh 'jana -v'
#   scripts/eic/run_in_eic_shell.sh scripts/eic/jana2_tests.sh
#
# The image ships JANA2, DD4hep and EICrecon at the versions ePIC uses (ccdb-2.5.md, D3).
# CCDB_EIC_IMAGE overrides the image; the default is the tag the CCDB 2.5 program pins.
# The command runs as the calling user, so files it writes into the checkout (build trees) stay yours.
# CI runs the same command through eic-shell on CVMFS instead (see .github/workflows/cpp-tests.yml).
set -euo pipefail

if [ $# -eq 0 ]; then
    echo "usage: $0 <command> [args...]" >&2
    exit 2
fi

image="${CCDB_EIC_IMAGE:-eicweb/eic_xl:26.10.0-stable}"
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

exec docker run --rm \
    --user "$(id -u):$(id -g)" \
    --env HOME=/tmp \
    --volume "$repo":/ccdb \
    --workdir /ccdb \
    "$image" \
    bash -c "$*"
