#!/usr/bin/env python3
"""Read-only size and duplicate survey of a CCDB MySQL or MariaDB database.

Measures what the schema 6 upgrade will meet on a real instance: the server settings, the
engine and size of every table, the number and size of constant sets per CCDB table, and the
constant sets that are byte-identical inside one CCDB table (the duplicates `ccdb db dedup`
would merge). Writes a JSON report and prints a short summary.

    survey.py mysql://ccdb_user@hallddb.jlab.org/ccdb --out survey.json                 # sizes only
    survey.py mysql://... --out survey.json --duplicates 20      # duplicates in the 20 tables with most sets
    survey.py mysql://... --out survey.json --duplicates all --numeric       # every table; local copies only

Every statement is a SELECT inside a READ ONLY transaction. The size pass reads the length of
every vault on the server once. --duplicates computes SHA2 of every vault in the chosen tables on
the server and transfers only the hashes. --numeric transfers the vaults of the chosen tables to
this process to count sets that differ in bytes but hold the same numbers (1.0 against 1.00); it
refuses a server other than 127.0.0.1 or localhost, since it reads every blob over the network.
"""
import argparse
import hashlib
import json
import sys
import time
from collections import defaultdict

import sqlalchemy

from compare import engine_for

SERVER_VARIABLES = ["version", "innodb_buffer_pool_size", "innodb_log_file_size", "innodb_flush_log_at_trx_commit",
                    "character_set_server", "collation_server", "sql_mode", "max_allowed_packet"]


def rows(conn, sql, **params):
    return conn.execute(sqlalchemy.text(sql), params).fetchall()


def table_paths(conn):
    """CCDB table id -> full path such as /FCAL/gains, from directories and typeTables."""
    dirs = {row[0]: (row[1], row[2]) for row in rows(conn, "SELECT id, parentId, name FROM directories")}

    def dir_path(dir_id):
        parts = []
        while dir_id in dirs:
            parent, name = dirs[dir_id]
            parts.append(name)
            dir_id = parent
        return "/" + "/".join(reversed(parts))

    paths = {}
    for table_id, dir_id, name in rows(conn, "SELECT id, directoryId, name FROM typeTables"):
        base = dir_path(dir_id) if dir_id in dirs else ""
        paths[table_id] = base.rstrip("/") + "/" + name
    return paths


def numeric_key(vault):
    """The vault with every cell parsed as a number where it parses: '1.00|2' and '1.0|2.0' share a key."""
    cells = []
    for cell in vault.split("|"):
        try:
            cells.append(float(cell))
        except ValueError:
            cells.append(cell)
    return tuple(cells)


def survey(connection, duplicates, numeric):
    engine = engine_for(connection)
    host = engine.url.host or "localhost"
    if numeric and host not in ("127.0.0.1", "localhost"):
        raise SystemExit(f"--numeric reads every blob of the chosen tables; refused for server {host}")
    report = {"connection": engine.url.render_as_string(hide_password=True), "taken": time.strftime("%Y-%m-%d %H:%M:%S")}
    timings = report["timings_s"] = {}

    with engine.connect() as conn:
        conn.execute(sqlalchemy.text("SET SESSION TRANSACTION READ ONLY"))
        conn.execute(sqlalchemy.text("START TRANSACTION READ ONLY"))
        schema = conn.execute(sqlalchemy.text("SELECT DATABASE()")).scalar()

        report["server"] = {name: conn.execute(sqlalchemy.text(f"SELECT @@{name}")).scalar() for name in SERVER_VARIABLES}
        report["server"] = {k: (int(v) if isinstance(v, int) or str(v).isdigit() else str(v)) for k, v in report["server"].items()}

        report["tables"] = [
            {"name": n, "engine": e, "rows_estimate": r, "data_bytes": d, "index_bytes": i, "collation": c}
            for n, e, r, d, i, c in rows(conn,
                "SELECT TABLE_NAME, ENGINE, TABLE_ROWS, DATA_LENGTH, INDEX_LENGTH, TABLE_COLLATION "
                "FROM information_schema.TABLES WHERE TABLE_SCHEMA = :s AND TABLE_TYPE = 'BASE TABLE' ORDER BY TABLE_NAME", s=schema)]
        report["row_counts"] = {t["name"]: rows(conn, f"SELECT COUNT(*) FROM `{t['name']}`")[0][0] for t in report["tables"]}

        paths = table_paths(conn)
        shapes = {row[0]: (row[1], row[2]) for row in rows(conn, "SELECT id, nRows, nColumns FROM typeTables")}
        assignment_counts = dict(rows(conn,
            "SELECT cs.constantTypeId, COUNT(*) FROM assignments a JOIN constantSets cs ON cs.id = a.constantSetId GROUP BY cs.constantTypeId"))

        started = time.time()
        per_table = {}
        for table_id, sets, total, largest in rows(conn,
                "SELECT constantTypeId, COUNT(*), SUM(LENGTH(vault)), MAX(LENGTH(vault)) FROM constantSets GROUP BY constantTypeId"):
            n_rows, n_cols = shapes.get(table_id, (None, None))
            per_table[table_id] = {"table_id": table_id, "path": paths.get(table_id, f"<no typeTables row {table_id}>"),
                                   "rows": n_rows, "columns": n_cols, "sets": sets, "bytes": int(total or 0),
                                   "largest_set_bytes": int(largest or 0), "assignments": assignment_counts.get(table_id, 0)}
        timings["size_pass"] = round(time.time() - started, 1)
        report["orphan_sets"] = rows(conn,
            "SELECT COUNT(*) FROM constantSets cs LEFT JOIN assignments a ON a.constantSetId = cs.id WHERE a.id IS NULL")[0][0]
        report["sets_with_several_assignments"] = rows(conn,
            "SELECT COUNT(*) FROM (SELECT constantSetId FROM assignments GROUP BY constantSetId HAVING COUNT(*) > 1) shared")[0][0]
        report["sets_by_size"] = [
            {"bucket": b, "sets": n, "bytes": int(s)} for b, n, s in rows(conn,
                "SELECT CASE WHEN LENGTH(vault) < 1024 THEN 'a <1 kB' WHEN LENGTH(vault) < 65536 THEN 'b 1-64 kB' "
                "WHEN LENGTH(vault) < 1048576 THEN 'c 64 kB-1 MB' ELSE 'd >=1 MB' END b, COUNT(*), SUM(LENGTH(vault)) "
                "FROM constantSets GROUP BY b ORDER BY b")]
        non_ascii = rows(conn, "SELECT COUNT(*), COUNT(DISTINCT constantTypeId) FROM constantSets WHERE vault REGEXP '[^ -~\\t\\n\\r]'")[0]
        report["non_ascii_sets"] = {"sets": non_ascii[0], "tables": non_ascii[1]}

        chosen = []
        if duplicates:
            by_sets = sorted(per_table.values(), key=lambda t: -t["sets"])
            chosen = by_sets if duplicates == "all" else by_sets[:int(duplicates)]
        started = time.time()
        for table in chosen:
            groups = rows(conn,
                "SELECT SHA2(CONVERT(vault USING utf8mb4), 256) h, COUNT(*), MIN(id), MAX(LENGTH(vault)) "
                "FROM constantSets WHERE constantTypeId = :t GROUP BY h HAVING COUNT(*) > 1", t=table["table_id"])
            table["duplicate_groups"] = len(groups)
            table["redundant_sets"] = sum(n - 1 for _, n, _, _ in groups)
            table["bytes_saved"] = sum((n - 1) * size for _, n, _, size in groups)
        timings["duplicate_pass"] = round(time.time() - started, 1)

        if numeric:
            started = time.time()
            for table in chosen:
                by_number = defaultdict(set)
                for (vault,) in conn.execute(sqlalchemy.text("SELECT vault FROM constantSets WHERE constantTypeId = :t"),
                                             {"t": table["table_id"]}):
                    by_number[numeric_key(vault)].add(hashlib.sha256(vault.encode("utf-8")).hexdigest())
                spread = [len(h) for h in by_number.values() if len(h) > 1]
                table["numeric_only_groups"] = len(spread)
                table["numeric_only_extra_sets"] = sum(n - 1 for n in spread)
            timings["numeric_pass"] = round(time.time() - started, 1)
        conn.execute(sqlalchemy.text("ROLLBACK"))
    engine.dispose()

    report["ccdb_tables"] = sorted(per_table.values(), key=lambda t: -t["sets"])
    report["duplicates_scope"] = "none" if not duplicates else ("all tables" if duplicates == "all" else f"{len(chosen)} tables with most sets")
    if chosen:
        report["duplicate_totals"] = {
            "tables_scanned": len(chosen),
            "sets_scanned": sum(t["sets"] for t in chosen),
            "tables_with_duplicates": sum(1 for t in chosen if t["duplicate_groups"]),
            "duplicate_groups": sum(t["duplicate_groups"] for t in chosen),
            "redundant_sets": sum(t["redundant_sets"] for t in chosen),
            "bytes_saved": sum(t["bytes_saved"] for t in chosen),
        }
        if numeric:
            report["duplicate_totals"]["numeric_only_groups"] = sum(t["numeric_only_groups"] for t in chosen)
            report["duplicate_totals"]["numeric_only_extra_sets"] = sum(t["numeric_only_extra_sets"] for t in chosen)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("connection")
    parser.add_argument("--out", required=True, help="JSON report path")
    parser.add_argument("--duplicates", default=None, help="N (tables with most sets) or 'all'")
    parser.add_argument("--numeric", action="store_true", help="also count numeric-only duplicates (local servers only)")
    args = parser.parse_args()
    if args.numeric and not args.duplicates:
        parser.error("--numeric needs --duplicates")

    report = survey(args.connection, args.duplicates, args.numeric)
    with open(args.out, "w") as f:
        json.dump(report, f, indent=1, default=str)
    sets = sum(t["sets"] for t in report["ccdb_tables"])
    total = sum(t["bytes"] for t in report["ccdb_tables"])
    print(f"{len(report['ccdb_tables'])} CCDB tables with sets, {sets} sets, {total / 1e6:.1f} MB of vault text, "
          f"{report['orphan_sets']} orphan sets, {report['non_ascii_sets']['sets']} sets with non-ASCII text")
    if "duplicate_totals" in report:
        print("duplicates:", json.dumps(report["duplicate_totals"]))
    print("timings:", json.dumps(report["timings_s"]), "->", args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
