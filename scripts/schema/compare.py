#!/usr/bin/env python3
"""Dump the structure of a CCDB database as sorted text, or compare two databases by that text.

The text lists tables with their engine, columns with type, nullability and default, and indexes
with their columns and uniqueness: one line per object, sorted, so two dumps compare with diff.
A fresh schema and an upgraded one must produce the same text.

    compare.py dump mysql://ccdb_user@127.0.0.1:33083/ccdb_test
    compare.py dump sqlite:////tmp/ccdb.sqlite --charset
    compare.py diff mysql://...fresh mysql://...upgraded      # exit 1 and a unified diff on a difference

Connection strings are the ones the ccdb command takes. MySQL and MariaDB are read through
information_schema, SQLite through pragmas. --charset adds the character set of text columns and
the table collation (MySQL only), used for drift inventories of production databases.
--ignore-table NAME (repeatable) leaves a table out, for tables a comparison must not see.
"""
import argparse
import difflib
import sys

import sqlalchemy


def engine_for(connection):
    """SQLAlchemy engine for a ccdb connection string (mysql://... uses the pymysql driver)."""
    if connection.startswith("mysql://"):
        connection = "mysql+pymysql://" + connection[len("mysql://"):]
    return sqlalchemy.create_engine(connection)


def mysql_lines(conn, with_charset):
    schema = conn.execute(sqlalchemy.text("SELECT DATABASE()")).scalar()
    lines = []
    tables = conn.execute(sqlalchemy.text(
        "SELECT TABLE_NAME, ENGINE, TABLE_COLLATION FROM information_schema.TABLES "
        "WHERE TABLE_SCHEMA = :s AND TABLE_TYPE = 'BASE TABLE'"), {"s": schema})
    for name, engine, collation in tables:
        extra = f" collation={collation}" if with_charset else ""
        lines.append(f"table {name} engine={engine}{extra}")

    columns = conn.execute(sqlalchemy.text(
        "SELECT TABLE_NAME, COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT, EXTRA, CHARACTER_SET_NAME "
        "FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = :s"), {"s": schema})
    for table, column, column_type, nullable, default, extra, charset in columns:
        # MariaDB reports a missing default as the string 'NULL' and quotes literal defaults;
        # MySQL reports None and leaves them unquoted. Normalize both to one spelling.
        if default is None or default == "NULL":
            default = "none"
        default = str(default).strip("'")
        line = f"column {table}.{column} type={column_type.lower()} null={nullable} default={default}"
        if extra:
            line += f" extra={extra.lower()}"
        if with_charset and charset:
            line += f" charset={charset}"
        lines.append(line)

    index_columns = {}
    rows = conn.execute(sqlalchemy.text(
        "SELECT TABLE_NAME, INDEX_NAME, NON_UNIQUE, SEQ_IN_INDEX, COLUMN_NAME FROM information_schema.STATISTICS "
        "WHERE TABLE_SCHEMA = :s ORDER BY TABLE_NAME, INDEX_NAME, SEQ_IN_INDEX"), {"s": schema})
    for table, index, non_unique, _, column in rows:
        key = (table, index, int(non_unique) == 0)
        index_columns.setdefault(key, []).append(column)
    for (table, index, unique), cols in index_columns.items():
        lines.append(f"index {table}.{index} unique={int(unique)} columns={','.join(cols)}")
    return lines


def sqlite_lines(conn):
    lines = []
    names = [row[0] for row in conn.execute(sqlalchemy.text(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"))]
    for table in names:
        lines.append(f"table {table} engine=sqlite")
        for _, column, column_type, notnull, default, pk in conn.execute(sqlalchemy.text(f'PRAGMA table_info("{table}")')):
            default = "none" if default is None else str(default).strip("'")
            null = "NO" if notnull or pk else "YES"
            line = f"column {table}.{column} type={column_type.lower()} null={null} default={default}"
            if pk:
                line += " extra=primary_key"
            lines.append(line)
        for _, index, unique, origin, _ in conn.execute(sqlalchemy.text(f'PRAGMA index_list("{table}")')):
            cols = [row[2] for row in conn.execute(sqlalchemy.text(f'PRAGMA index_info("{index}")'))]
            # Indexes SQLite creates itself (origin 'pk' or 'u') carry generated names; name them by columns.
            label = index if origin == "c" else f"auto_{origin}_{'_'.join(cols)}"
            lines.append(f"index {table}.{label} unique={unique} columns={','.join(cols)}")
    return lines


def dump(connection, with_charset=False, ignore_tables=()):
    engine = engine_for(connection)
    with engine.connect() as conn:
        if engine.dialect.name == "sqlite":
            lines = sqlite_lines(conn)
        else:
            lines = mysql_lines(conn, with_charset)
    engine.dispose()
    ignored = set(ignore_tables)
    kept = [line for line in lines if line.split()[1].split(".")[0] not in ignored]
    return sorted(kept)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("dump", "diff"):
        p = sub.add_parser(name)
        p.add_argument("connections", nargs=1 if name == "dump" else 2)
        p.add_argument("--charset", action="store_true", help="add column character sets and table collations (MySQL)")
        p.add_argument("--ignore-table", action="append", default=[], help="leave this table out (repeatable)")
    args = parser.parse_args()

    if args.command == "dump":
        print("\n".join(dump(args.connections[0], args.charset, args.ignore_table)))
        return 0

    a, b = (dump(c, args.charset, args.ignore_table) for c in args.connections)
    if a == b:
        print(f"same structure: {len(a)} lines")
        return 0
    sys.stdout.writelines(difflib.unified_diff([x + "\n" for x in a], [x + "\n" for x in b], "a", "b"))
    return 1


if __name__ == "__main__":
    sys.exit(main())
