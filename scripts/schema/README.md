# Schema checks

Scripts that check the CCDB database structure and measure real instances before a schema
upgrade. They read databases and never write to them.

| file | what it does |
|---|---|
| `compare.py` | `dump` prints the structure of a database (tables, engines, columns with type, nullability and default, indexes) as sorted lines; `diff` compares two databases and exits with 1 on a difference. A fresh schema and an upgraded one must give the same text, on MySQL, MariaDB and SQLite |
| `survey.py` | size and duplicate survey of a MySQL or MariaDB instance: server settings, table engines and sizes, constant sets per CCDB table, byte-identical sets inside one table; JSON report. Every statement is a `SELECT` in a read-only transaction |
| `compose.yml` | throwaway MySQL 8.3 and MariaDB 10.5 servers for the MySQL test suite on a host, the same versions CI runs |
| `test_users.sql` | the test users of both servers: `ccdb_user` with all rights on `ccdb_test*`, `ccdb_reader` with `SELECT` only |

## Running

```bash
docker compose -f scripts/schema/compose.yml up -d --wait
uv run python scripts/schema/compare.py diff mysql://ccdb_user@127.0.0.1:33083/ccdb_test mysql://ccdb_user@127.0.0.1:33105/ccdb_test
uv run python scripts/schema/survey.py mysql://ccdb_user@hallddb.jlab.org/ccdb --out survey.json
docker compose -f scripts/schema/compose.yml down
```

The size pass of `survey.py` reads the length of every vault once on the server. `--duplicates N`
hashes the vaults of the N tables with the most sets on the server and transfers only the hashes;
`--duplicates all` hashes every vault. `--numeric` transfers the vaults to count sets that differ
only in number formatting (`1.0` against `1.00`), and runs only against a server on localhost,
such as a local copy of a production dump.
