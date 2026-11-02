#!/usr/bin/env bash
# Installs the C++ library from this checkout with the recipe in spack/spack_repo/ccdb, inside the spack
# container, then builds cpp/examples/consumer against the installed package and reads a table through it.
#
# CI runs it in .github/workflows/spack.yml; on a host with docker, from the repository root:
#     docker run --rm -v "$PWD":/ccdb:ro --entrypoint bash spack/ubuntu-noble:1.2.2 /ccdb/spack/check_recipe.sh
# An argument adds variants to the spec, e.g. "~mysql". The checkout is only read: the sources are copied.
set -euo pipefail
REPO=$(cd "$(dirname "$0")/.." && pwd)
VARIANTS=${1:-}
WORK=$(mktemp -d)

. /opt/spack/share/spack/setup-env.sh
apt-get update -qq
apt-get install -y -qq cmake libsqlite3-dev sqlite3 libmariadb-dev python3-venv > /dev/null

# The compiler, CMake and SQLite of the distribution; its MariaDB client stands in for mysql-client, which
# spack would otherwise build together with openssl, krb5 and curl
spack compiler find
spack external find --not-buildable cmake sqlite

mkdir -p "$WORK/src"
cp -r "$REPO/cpp" "$REPO/python" "$REPO/spack" "$REPO/pyproject.toml" "$REPO/README.md" "$REPO/LICENSE" "$WORK/src/"
rm -rf "$WORK/src/cpp/build"
spack repo add "$WORK/src/spack/spack_repo/ccdb"

# The checkout as the version "develop", built with its Catch2 suite (--test=root)
mkdir -p "$WORK/env"
cat > "$WORK/env/spack.yaml" <<YAML
spack:
  specs: ["ccdb@=develop$VARIANTS"]
  view: false
  packages:
    mariadb-c-client:
      buildable: false
      externals:
      - spec: mariadb-c-client@$(mariadb_config --cc_version)
        prefix: /usr
    mysql-client:
      require: mariadb-c-client
YAML
spack -e "$WORK/env" develop --no-clone --path "$WORK/src" "ccdb@=develop"
spack -e "$WORK/env" concretize -f
spack -e "$WORK/env" install --fail-fast --test=root
PREFIX=$(spack -e "$WORK/env" location -i ccdb)
ls "$PREFIX/lib/cmake/ccdb" "$PREFIX/bin"

# A test database from the Python package, then the consumer against the spack prefix
python3 -m venv "$WORK/venv"
"$WORK/venv/bin/pip" install -q "$WORK/src"
DB="sqlite:///$WORK/check.sqlite"
"$WORK/venv/bin/ccdb" -c "$DB" db init --init-i-am-sure > /dev/null
cmake -S "$WORK/src/cpp/examples/consumer" -B "$WORK/consumer" -DCMAKE_PREFIX_PATH="$PREFIX"
cmake --build "$WORK/consumer"
"$WORK/consumer/ccdb_consumer" "$DB" /test/test_vars/test_table | tee "$WORK/consumer.out"
grep -q "^/test/test_vars/test_table: 2 rows, 3 columns$" "$WORK/consumer.out"
grep -q "^2.2 2.3 2.4$" "$WORK/consumer.out"
echo "spack recipe check passed: ccdb@=develop$VARIANTS in $PREFIX"
