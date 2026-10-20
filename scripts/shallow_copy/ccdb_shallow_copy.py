#!/usr/bin/env python3
"""
Shallow copy of a CCDB database: only the constants that a run period, a point in time and a set
of variations need.

The copy answers a lookup the same way the source does when the lookup asks for a copied variation,
a run inside the period, and no time or a time at or after --time. A lookup for a run outside the
period, or for a variation that was not copied, fails with "no assignment" instead of returning
constants the source would not return.

What the copy holds:
  - schema version, users, directories, tables and their columns: all of them.
    Passwords are blanked unless --copy-passwords is given.
  - variations: the listed ones and all their parents.
  - assignments: for every table, listed variation and run of the period, the one that
    AlchemyProvider.get_assignment returns: the highest assignment id created at or before --time,
    falling back to the parent variation while a variation has none. Their constant sets are copied whole.
  - run ranges: clipped to the period. A range that lies inside the period keeps its row; any other
    range gets a new clipped row, so lookups outside the period find nothing.
  - one log record with the copy parameters. Logs, tags and event ranges are not copied.
  - every column of the source; a column the target schema lacks is added to it.

--full copies every row of every table instead (users' passwords are still blanked by default).
--per-run selects assignments with one get_assignment call per table, variation and run: the
reference method, slow on real databases, used to check the default one.

Examples:
  ccdb_shallow_copy.py mysql://ccdb_user@hallddb.jlab.org/ccdb sqlite:///ccdb_140k.sqlite \\
      --run-min 140000 --run-max 140901 --variations default,mc
  ccdb_shallow_copy.py mysql://ccdb_user@hallddb.jlab.org/ccdb sqlite:///ccdb_full.sqlite --full
"""

import argparse
import datetime
import json
import logging
import os
import sys
import time
from collections import namedtuple

from sqlalchemy import bindparam, create_engine, event, inspect, text
from sqlalchemy.orm import sessionmaker

from ccdb.model import INFINITE_RUN, TypeTable
from ccdb.path_utils import parse_time
from ccdb.provider import AlchemyProvider
from ccdb.sql.mysql_schema import mysql_tables
from ccdb.sql.sqlite_schema import _iter_statements, sqlite_init_script

log = logging.getLogger("ccdb_shallow_copy")

SUPPORTED_SCHEMA_VERSION = 5

# Tables copied by every mode, in an order that keeps references valid
METADATA_TABLES = ["schemaVersions", "users", "directories", "typeTables", "columns"]

# Every CCDB table; --full copies all of them in this order
ALL_TABLES = METADATA_TABLES + ["variations", "runRanges", "eventRanges", "constantSets", "assignments",
                                "logs", "tags", "variations_has_tags"]

# Rows per INSERT batch and ids per "IN (...)" list
CHUNK_SIZE = 500

# One assignment that may win some run: everything the selection needs, no constants
Candidate = namedtuple("Candidate", "id created variation_id run_range_id run_min run_max table_id")


class CopyError(Exception):
    """A problem with the arguments or the databases that stops the copy before it writes data"""


class TimeLimitReached(Exception):
    """--time-limit ran out; the message says where the copy stopped"""


# --------------------------------------------------------------------------------------------------
# Connections and values
# --------------------------------------------------------------------------------------------------

def open_engine(connection_string):
    """Opens an engine the way AlchemyProvider.connect does: mysql:// falls back to pymysql"""
    try:
        return create_engine(connection_string)
    except ImportError as err:
        if connection_string.startswith("mysql://") and "MySQLdb" in repr(err):
            return create_engine(connection_string.replace("mysql://", "mysql+pymysql://", 1))
        raise


def hide_password(connection_string):
    """Connection string without the password, for logs and the provenance record"""
    try:
        from sqlalchemy.engine import make_url
        return make_url(connection_string).render_as_string(hide_password=True)
    except Exception:
        return connection_string.split("@")[-1]


def is_sqlite(engine):
    return engine.dialect.name == "sqlite"


def as_datetime(value):
    """Timestamps arrive as datetime from MySQL and as text from SQLite"""
    if isinstance(value, datetime.datetime):
        return value
    if value is None or str(value).startswith("0000-00-00"):
        return datetime.datetime.min
    text_value = str(value).replace("T", " ")
    try:
        return datetime.datetime.fromisoformat(text_value)
    except ValueError:
        # fromisoformat of Python < 3.11 accepts only 3 or 6 fraction digits
        whole, _, fraction = text_value.partition(".")
        result = datetime.datetime.strptime(whole, "%Y-%m-%d %H:%M:%S")
        return result.replace(microsecond=int((fraction + "000000")[:6])) if fraction else result


def to_sqlite_value(value):
    """SQLite stores timestamps as text; this is the format C++ compares against
    (`created` <= datetime(?, 'unixepoch', 'localtime') gives 'YYYY-MM-DD HH:MM:SS')"""
    if isinstance(value, datetime.datetime):
        return value.isoformat(sep=" ")
    if isinstance(value, datetime.date):
        return value.isoformat()
    return value


def chunks(items, size=CHUNK_SIZE):
    items = list(items)
    for start in range(0, len(items), size):
        yield items[start:start + size]


# --------------------------------------------------------------------------------------------------
# Row copier: source columns -> target columns, in batches
# --------------------------------------------------------------------------------------------------

class RowCopier:
    """Copies rows of CCDB tables between two engines with plain SQL.

    The column list of each table is the source's. Columns the target lacks are added to it first
    (extend_target_columns), so nothing the source holds is dropped silently.
    """

    def __init__(self, source, target):
        self.source = source
        self.target = target
        self.quote_source = source.dialect.identifier_preparer.quote
        self.quote_target = target.dialect.identifier_preparer.quote
        source_inspector = inspect(source)
        self.source_tables = set(source_inspector.get_table_names())
        self.source_columns = {name: source_inspector.get_columns(name) for name in ALL_TABLES if name in self.source_tables}

    def column_names(self, table):
        return [column["name"] for column in self.source_columns[table]]

    def extend_target_columns(self):
        """Adds to the target every source column it lacks. Returns ['table.column', ...] added."""
        target_inspector = inspect(self.target)
        added = []
        with self.target.begin() as connection:
            for table, columns in self.source_columns.items():
                if table not in target_inspector.get_table_names():
                    continue
                target_names = {column["name"] for column in target_inspector.get_columns(table)}
                for column in columns:
                    if column["name"] in target_names:
                        continue
                    sql_type = self._target_type(column["type"])
                    connection.execute(text("ALTER TABLE {0} ADD COLUMN {1} {2}".format(
                        self.quote_target(table), self.quote_target(column["name"]), sql_type)))
                    added.append(table + "." + column["name"])
        return added

    def _target_type(self, source_type):
        """A loose type for an added column; a MySQL type does not always compile for SQLite"""
        try:
            return source_type.compile(dialect=self.target.dialect)
        except Exception:
            python_type = getattr(source_type, "python_type", str)
            if python_type in (int, bool):
                return "INTEGER"
            if python_type is datetime.datetime:
                return "TIMESTAMP"
            return "TEXT"

    def select_sql(self, table, where=""):
        columns = ", ".join(self.quote_source(name) for name in self.column_names(table))
        sql = "SELECT {0} FROM {1}".format(columns, self.quote_source(table))
        return sql + (" WHERE " + where if where else "")

    def insert_rows(self, connection, table, rows):
        """Inserts rows (tuples in column_names(table) order) into the target"""
        if not rows:
            return
        names = self.column_names(table)
        sql = "INSERT INTO {0} ({1}) VALUES ({2})".format(
            self.quote_target(table),
            ", ".join(self.quote_target(name) for name in names),
            ", ".join(":c{0}".format(i) for i in range(len(names))))
        convert = to_sqlite_value if is_sqlite(self.target) else (lambda value: value)
        params = [{"c{0}".format(i): convert(value) for i, value in enumerate(row)} for row in rows]
        connection.execute(text(sql), params)

    def copy(self, table, where="", params=None, row_hook=None, stream=False):
        """Copies the rows of `table` matching `where`; row_hook(dict) may change a row in place.
        Returns the number of rows copied."""
        names = self.column_names(table)
        query = text(self.select_sql(table, where))
        for name, value in (params or {}).items():
            if isinstance(value, (list, tuple, set)):
                query = query.bindparams(bindparam(name, expanding=True))
        count = 0
        with self.source.connect() as source_connection, self.target.begin() as target_connection:
            if stream:
                source_connection = source_connection.execution_options(stream_results=True, yield_per=CHUNK_SIZE)
            result = source_connection.execute(query, params or {})
            while True:
                batch = result.fetchmany(CHUNK_SIZE)
                if not batch:
                    break
                rows = []
                for row in batch:
                    if row_hook:
                        values = dict(zip(names, row))
                        row_hook(values)
                        row = tuple(values[name] for name in names)
                    rows.append(tuple(row))
                self.insert_rows(target_connection, table, rows)
                count += len(rows)
        return count

    def copy_ids(self, table, ids, row_hook=None):
        """Copies the rows of `table` whose id is in `ids`"""
        count = 0
        for id_chunk in chunks(sorted(ids)):
            count += self.copy(table, "id IN :ids", {"ids": id_chunk}, row_hook)
        return count


# --------------------------------------------------------------------------------------------------
# Target preparation
# --------------------------------------------------------------------------------------------------

def prepare_target(target_connection_string, overwrite):
    """Checks that the target holds no CCDB tables (or removes an SQLite file with --overwrite),
    creates the schema without the test content of the repository scripts, returns the engine."""
    engine = open_engine(target_connection_string)
    if is_sqlite(engine):
        path = engine.url.database
        if path and path != ":memory:" and os.path.exists(path) and os.path.getsize(path) > 0:
            if not overwrite:
                raise CopyError("Target file exists: {0}. Use --overwrite to replace it.".format(path))
            engine.dispose()
            for suffix in ("", "-journal", "-wal", "-shm"):
                if os.path.exists(path + suffix):
                    os.remove(path + suffix)
            engine = open_engine(target_connection_string)

        @event.listens_for(engine, "connect")
        def fast_build(dbapi_connection, _record):
            # A crash leaves a half-built file anyway; durability buys nothing during the build
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA synchronous=OFF")
            cursor.execute("PRAGMA journal_mode=MEMORY")
            cursor.close()
    else:
        existing = set(inspect(engine).get_table_names()) & set(ALL_TABLES)
        if existing:
            raise CopyError("Target database already has CCDB tables ({0}). Use an empty database; "
                            "--overwrite works with SQLite files only.".format(", ".join(sorted(existing))))

    with engine.begin() as connection:
        if is_sqlite(engine):
            for statement in _iter_statements(sqlite_init_script):
                if not statement.lstrip().upper().startswith("INSERT"):
                    connection.execute(text(statement))
        else:
            for table in mysql_tables.values():
                if "create" in table:
                    connection.execute(text(table["create"]))
    return engine


def finish_target(engine):
    """ANALYZE gives the SQLite query planner real row counts"""
    if not is_sqlite(engine):
        return
    with engine.begin() as connection:
        connection.execute(text("ANALYZE"))


# --------------------------------------------------------------------------------------------------
# Variations
# --------------------------------------------------------------------------------------------------

def load_variations(source):
    """{id: (name, parent_id)} of every variation in the source"""
    with source.connect() as connection:
        rows = connection.execute(text('SELECT id, name, parentId FROM variations')).fetchall()
    return {row[0]: (row[1], row[2]) for row in rows}


def variation_chains(variations, requested_names):
    """Lookup chain of every requested variation: [id of the variation, id of its parent, ...].

    Mirrors AlchemyProvider.get_assignment: the walk stops after 'default' or when the parent row is
    missing. Returns {name: [ids]}. requested_names == ['*'] means every variation.
    """
    ids_by_name = {}
    for variation_id, (name, _parent) in variations.items():
        ids_by_name.setdefault(name, []).append(variation_id)

    names = sorted(ids_by_name) if requested_names == ["*"] else requested_names
    unknown = [name for name in names if name not in ids_by_name]
    if unknown:
        raise CopyError("Variations not found in the source: " + ", ".join(unknown))

    chains = {}
    for name in names:
        chain = []
        variation_id = ids_by_name[name][0]
        while variation_id in variations and variation_id not in chain:
            chain.append(variation_id)
            variation_name, parent_id = variations[variation_id]
            if variation_name == "default":
                break
            variation_id = parent_id
        chains[name] = chain

    # The provider looks variations up by name: two rows with one name would merge their assignments
    for name in {variations[variation_id][0] for chain in chains.values() for variation_id in chain}:
        if len(ids_by_name[name]) > 1:
            raise CopyError("Variation name '{0}' is used by several rows (ids {1}); lookups by name are ambiguous"
                            .format(name, ids_by_name[name]))
    return chains


# --------------------------------------------------------------------------------------------------
# Assignment selection
# --------------------------------------------------------------------------------------------------

def load_candidates(source, variation_ids, run_min, run_max):
    """Every assignment of the given variations whose run range overlaps the period, grouped by table.

    One query for the whole database. The time filter is applied later in Python, on parsed
    timestamps, so that MySQL datetimes and SQLite text compare the same way.
    """
    query = text(
        "SELECT a.id, a.created, a.variationId, a.runRangeId, r.runMin, r.runMax, c.constantTypeId "
        "FROM assignments a "
        "JOIN runRanges r ON r.id = a.runRangeId "
        "JOIN constantSets c ON c.id = a.constantSetId "
        "WHERE a.variationId IN :variation_ids AND r.runMin <= :run_max AND r.runMax >= :run_min"
    ).bindparams(bindparam("variation_ids", expanding=True))
    by_table = {}
    with source.connect() as connection:
        rows = connection.execute(query, {"variation_ids": sorted(variation_ids), "run_min": run_min, "run_max": run_max})
        for row in rows:
            candidate = Candidate(row[0], as_datetime(row[1]), row[2], row[3], row[4], row[5], row[6])
            by_table.setdefault(candidate.table_id, []).append(candidate)
    return by_table


def pick_winners(candidates, chains, run_min, run_max, max_time=None):
    """Assignments that win at least one (variation, run) of the period: {assignment id: Candidate}.

    For each requested variation the period starts unresolved. Each level of the variation chain
    hands out the unresolved runs to its assignments in descending id order, so a run goes to the
    highest id that covers it, and only runs no assignment of a level covers fall to the parent.
    This is AlchemyProvider.get_assignment for every run at once.
    """
    by_variation = {}
    for candidate in candidates:
        if max_time is None or candidate.created <= max_time:
            by_variation.setdefault(candidate.variation_id, []).append(candidate)
    for variation_candidates in by_variation.values():
        variation_candidates.sort(key=lambda candidate: candidate.id, reverse=True)

    winners = {}
    for chain in chains.values():
        unresolved = [(run_min, run_max)]
        for variation_id in chain:
            for candidate in by_variation.get(variation_id, []):
                unresolved, claimed = claim_runs(unresolved, candidate.run_min, candidate.run_max)
                if claimed:
                    winners[candidate.id] = candidate
                if not unresolved:
                    break
            if not unresolved:
                break
    return winners


def claim_runs(segments, first_run, last_run):
    """Removes [first_run, last_run] from the run segments. Returns (remaining segments, claimed anything)"""
    remaining = []
    claimed = False
    for segment_min, segment_max in segments:
        if last_run < segment_min or first_run > segment_max:
            remaining.append((segment_min, segment_max))
            continue
        claimed = True
        if segment_min < first_run:
            remaining.append((segment_min, first_run - 1))
        if last_run < segment_max:
            remaining.append((last_run + 1, segment_max))
    return remaining, claimed


class PerRunSelector:
    """Reference selection: one AlchemyProvider.get_assignment call per table, variation and run"""

    def __init__(self, source):
        self.provider = AlchemyProvider()
        self.provider.attach(source, sessionmaker(bind=source)())

    def pick_winners(self, table_id, variation_names, run_min, run_max, max_time, deadline, where):
        table = self.provider.session.get(TypeTable, table_id)
        winners = {}
        for name in variation_names:
            for run in range(run_min, run_max + 1):
                if deadline and time.monotonic() > deadline:
                    raise TimeLimitReached("{0}, variation {1}, run {2}".format(where, name, run))
                assignment = lookup(self.provider, table, run, name, max_time)
                if assignment is not None and assignment.id not in winners:
                    run_range = assignment.run_range
                    winners[assignment.id] = Candidate(assignment.id, as_datetime(assignment.created), assignment.variation_id,
                                                       run_range.id, run_range.min, run_range.max, table_id)
        return winners


def lookup(provider, table, run, variation_name, max_time):
    """provider.get_assignment, with "nothing found" as None. A variation chain that ends at a root
    other than 'default' makes the provider fail on a None parent; that is also "nothing found"."""
    from sqlalchemy.orm.exc import NoResultFound
    try:
        return provider.get_assignment(table, run, variation_name, max_time)
    except (NoResultFound, AssertionError, AttributeError):
        return None


# --------------------------------------------------------------------------------------------------
# The copy
# --------------------------------------------------------------------------------------------------

class RunRangeClipper:
    """Run ranges of the copy. A range inside the period keeps its row; any other range gets one new
    clipped row (ids above the source maximum), shared by every assignment that used the original."""

    def __init__(self, copier, run_min, run_max):
        self.copier = copier
        self.run_min = run_min
        self.run_max = run_max
        self.target_ids = {}          # source run range id -> target run range id
        with copier.source.connect() as connection:
            self.next_id = (connection.execute(text("SELECT MAX(id) FROM runRanges")).scalar() or 0) + 1

    def target_id(self, candidate):
        """Target run range id for the candidate's range; the row is written by write_new()"""
        if candidate.run_range_id not in self.target_ids:
            if self.run_min <= candidate.run_min and candidate.run_max <= self.run_max:
                self.target_ids[candidate.run_range_id] = candidate.run_range_id
            else:
                self.target_ids[candidate.run_range_id] = self.next_id
                self.next_id += 1
        return self.target_ids[candidate.run_range_id]

    def write(self, source_ids):
        """Writes the rows of the given source run ranges that are not in the target yet"""
        kept = [source_id for source_id in source_ids if self.target_ids[source_id] == source_id]
        clipped = [source_id for source_id in source_ids if self.target_ids[source_id] != source_id]
        self.copier.copy_ids("runRanges", kept)
        self.copier.copy_ids("runRanges", clipped, row_hook=self._clip)

    def _clip(self, row):
        original = "run range {0} '{1}' ({2}-{3})".format(row["id"], row["name"] or "", row["runMin"], row["runMax"])
        row["id"] = self.target_ids[row["id"]]
        row["runMin"] = max(row["runMin"], self.run_min)
        row["runMax"] = min(row["runMax"], self.run_max)
        row["name"] = ""
        row["comment"] = "Clipped to runs {0}-{1} by a shallow copy from {2}".format(self.run_min, self.run_max, original)


def table_paths(source):
    """{table id: '/dir/sub/table'} for progress and error messages"""
    with source.connect() as connection:
        directories = {row[0]: (row[1], row[2]) for row in connection.execute(text("SELECT id, name, parentId FROM directories"))}
        tables = connection.execute(text("SELECT id, name, directoryId FROM typeTables ORDER BY id")).fetchall()

    def directory_path(directory_id, depth=0):
        if directory_id not in directories or depth > 100:
            return ""
        name, parent_id = directories[directory_id]
        return directory_path(parent_id, depth + 1) + "/" + name

    return {row[0]: directory_path(row[2]) + "/" + row[1] for row in tables}


def copy_metadata(copier, copy_passwords):
    """Tables every copy holds whole. Returns {table: rows copied}"""
    def blank_password(row):
        row["password"] = None

    counts = {}
    for table in METADATA_TABLES:
        hook = blank_password if table == "users" and not copy_passwords else None
        counts[table] = copier.copy(table, row_hook=hook)
    return counts


def check_source(source):
    with source.connect() as connection:
        version = connection.execute(text("SELECT schemaVersion FROM schemaVersions")).scalar()
    if version != SUPPORTED_SCHEMA_VERSION:
        raise CopyError("Source has CCDB schema version {0}; this script supports version {1}".format(version, SUPPORTED_SCHEMA_VERSION))


def write_log_record(target, description, comment):
    """The provenance record of the copy, as log id 1 by the anonymous user (id 1)"""
    with target.begin() as connection:
        next_id = (connection.execute(text("SELECT MAX(id) FROM logs")).scalar() or 0) + 1
        now = datetime.datetime.now().replace(microsecond=0)
        connection.execute(text("INSERT INTO logs (id, created, affectedIds, action, description, comment, authorId) "
                                "VALUES (:id, :created, '', 'create', :description, :comment, 1)"),
                           {"id": next_id, "created": to_sqlite_value(now) if is_sqlite(target) else now,
                            "description": description[:255], "comment": comment})


def shallow_copy(source_url, target_url, run_min, run_max, variations=("default",), max_time=None,
                 overwrite=False, per_run=False, copy_passwords=False, time_limit=None):
    """Makes the shallow copy. Returns a report dict; report['complete'] is False when time_limit ran out."""
    started = time.monotonic()
    deadline = started + time_limit if time_limit else None
    if run_min > run_max:
        raise CopyError("run-min {0} is greater than run-max {1}".format(run_min, run_max))
    if run_min < 0 or run_max > INFINITE_RUN:
        raise CopyError("Runs must lie within 0-{0}".format(INFINITE_RUN))

    source = open_engine(source_url)
    check_source(source)
    all_variations = load_variations(source)
    chains = variation_chains(all_variations, list(variations))
    copied_variation_ids = {variation_id for chain in chains.values() for variation_id in chain}

    target = prepare_target(target_url, overwrite)
    copier = RowCopier(source, target)
    report = {"source": hide_password(source_url), "target": hide_password(target_url), "run_min": run_min, "run_max": run_max,
              "variations": sorted(chains), "copied_variations": sorted(all_variations[i][0] for i in copied_variation_ids),
              "time": max_time.isoformat(sep=" ") if max_time else "latest", "method": "per-run" if per_run else "bulk",
              "added_columns": copier.extend_target_columns()}

    report["metadata_rows"] = copy_metadata(copier, copy_passwords)
    report["metadata_rows"]["variations"] = copier.copy_ids("variations", copied_variation_ids)
    report["seconds_metadata"] = round(time.monotonic() - started, 2)

    paths = table_paths(source)
    selection_started = time.monotonic()
    candidates_by_table = {} if per_run else load_candidates(source, copied_variation_ids, run_min, run_max)
    report["candidates"] = sum(len(candidates) for candidates in candidates_by_table.values())
    report["seconds_candidates"] = round(time.monotonic() - selection_started, 2)
    per_run_selector = PerRunSelector(source) if per_run else None

    clipper = RunRangeClipper(copier, run_min, run_max)
    totals = {"tables_done": 0, "tables_with_data": 0, "assignments": 0, "constant_sets": 0, "run_ranges": 0}
    slowest = []
    stopped_at = None
    for table_index, table_id in enumerate(sorted(paths), 1):
        table_started = time.monotonic()
        where = "table {0}/{1} {2}".format(table_index, len(paths), paths[table_id])
        try:
            if deadline and time.monotonic() > deadline:
                raise TimeLimitReached(where)
            if per_run:
                winners = per_run_selector.pick_winners(table_id, sorted(chains), run_min, run_max, max_time, deadline, where)
            else:
                winners = pick_winners(candidates_by_table.pop(table_id, []), chains, run_min, run_max, max_time)
        except TimeLimitReached as stop:
            stopped_at = str(stop)
            break

        if winners:
            # New run range ids follow the source range ids, so both selection methods give identical files
            new_range_ids = sorted({winner.run_range_id for winner in winners.values()} - set(clipper.target_ids))
            ranges_by_source_id = {winner.run_range_id: winner for winner in winners.values()}
            for range_id in new_range_ids:
                clipper.target_id(ranges_by_source_id[range_id])
            assignment_ranges = {winner.id: clipper.target_ids[winner.run_range_id] for winner in winners.values()}
            clipper.write(new_range_ids)
            constant_set_count = copy_constant_sets(copier, winners)
            copier.copy_ids("assignments", winners, row_hook=lambda row: row.update(runRangeId=assignment_ranges[row["id"]]))
            totals["tables_with_data"] += 1
            totals["assignments"] += len(winners)
            totals["constant_sets"] += constant_set_count
            totals["run_ranges"] += len(new_range_ids)
        with target.begin() as connection:
            connection.execute(text('UPDATE typeTables SET nAssignments = :count WHERE id = :id'), {"count": len(winners), "id": table_id})
        totals["tables_done"] += 1
        slowest.append((round(time.monotonic() - table_started, 3), paths[table_id], len(winners)))
        if table_index % 50 == 0:
            log.info("%s: %d assignments so far, %.0f s", where, totals["assignments"], time.monotonic() - started)

    report.update(totals)
    report["tables"] = len(paths)
    report["complete"] = stopped_at is None
    report["stopped_at"] = stopped_at
    report["slowest_tables"] = sorted(slowest, reverse=True)[:10]

    description = "Shallow copy: runs {0}-{1}, variations {2}, time {3}{4}".format(
        run_min, run_max, ",".join(sorted(chains)), report["time"], "" if report["complete"] else " (INCOMPLETE)")
    comment = "Source: {0}\nMethod: {1}\nCopied variations: {2}\nCopied {3} assignments of {4} tables".format(
        report["source"], report["method"], ", ".join(report["copied_variations"]), totals["assignments"], totals["tables_with_data"])
    if stopped_at:
        comment += "\nStopped by the time limit at " + stopped_at
    write_log_record(target, description, comment)
    finish_started = time.monotonic()
    finish_target(target)
    report["seconds_indexes"] = round(time.monotonic() - finish_started, 2)
    report["seconds_total"] = round(time.monotonic() - started, 2)
    report["target_bytes"] = sqlite_file_size(target)
    report["peak_memory_mb"] = peak_memory_mb()
    source.dispose()
    target.dispose()
    return report


def copy_constant_sets(copier, winners):
    """Constant sets of the winning assignments. Returns the number copied."""
    with copier.source.connect() as connection:
        set_ids = set()
        for id_chunk in chunks(sorted(winners)):
            query = text("SELECT constantSetId FROM assignments WHERE id IN :ids").bindparams(bindparam("ids", expanding=True))
            set_ids.update(row[0] for row in connection.execute(query, {"ids": id_chunk}))
    return copier.copy_ids("constantSets", set_ids)


def full_copy(source_url, target_url, overwrite=False, copy_passwords=False):
    """Copies every row of every CCDB table. Returns a report dict."""
    started = time.monotonic()
    source = open_engine(source_url)
    check_source(source)
    target = prepare_target(target_url, overwrite)
    copier = RowCopier(source, target)
    report = {"source": hide_password(source_url), "target": hide_password(target_url), "method": "full",
              "added_columns": copier.extend_target_columns(), "rows": {}, "seconds": {}}
    for table in ALL_TABLES:
        if table not in copier.source_tables:
            continue
        table_started = time.monotonic()
        hook = (lambda row: row.update(password=None)) if table == "users" and not copy_passwords else None
        report["rows"][table] = copier.copy(table, row_hook=hook, stream=True)
        report["seconds"][table] = round(time.monotonic() - table_started, 2)
        log.info("%s: %d rows, %.0f s", table, report["rows"][table], report["seconds"][table])
    finish_started = time.monotonic()
    finish_target(target)
    report["seconds_indexes"] = round(time.monotonic() - finish_started, 2)
    report["seconds_total"] = round(time.monotonic() - started, 2)
    report["target_bytes"] = sqlite_file_size(target)
    report["peak_memory_mb"] = peak_memory_mb()
    source.dispose()
    target.dispose()
    return report


def peak_memory_mb():
    """Peak resident memory of this process (Linux and macOS); None where unavailable"""
    try:
        import resource
    except ImportError:
        return None
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return round(peak / (1024 * 1024 if sys.platform == "darwin" else 1024), 1)


def sqlite_file_size(engine):
    path = engine.url.database if is_sqlite(engine) else None
    return os.path.getsize(path) if path and path != ":memory:" and os.path.exists(path) else None


# --------------------------------------------------------------------------------------------------
# Command line
# --------------------------------------------------------------------------------------------------

def parse_arguments(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0].strip(),
                                     epilog=__doc__.split("\n\n", 1)[1], formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("source", help="source connection string, e.g. mysql://ccdb_user@hallddb.jlab.org/ccdb")
    parser.add_argument("target", help="target connection string, e.g. sqlite:///ccdb_shallow.sqlite (an empty database)")
    parser.add_argument("--run-min", type=int, help="first run of the period")
    parser.add_argument("--run-max", type=int, help="last run of the period (default: --run-min)")
    parser.add_argument("--time", help="constants created at or before this time, CCDB format (2017-11-16_10-03-20); default: latest")
    parser.add_argument("--variations", default="default", help="comma separated variation names, or '*' for all (default: default)")
    parser.add_argument("--full", action="store_true", help="copy every row of every table instead")
    parser.add_argument("--per-run", action="store_true", help="select with one get_assignment call per table, variation and run (reference method)")
    parser.add_argument("--copy-passwords", action="store_true", help="copy users' passwords (blanked by default)")
    parser.add_argument("--overwrite", action="store_true", help="replace an existing SQLite target file")
    parser.add_argument("--time-limit", type=float, help="stop after this many seconds and report where (the copy is then incomplete)")
    parser.add_argument("--report-json", help="write the report to this file")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)
    if not args.full and args.run_min is None:
        parser.error("--run-min is required (or --full)")
    if args.run_max is None:
        args.run_max = args.run_min
    return args


def main(argv=None):
    args = parse_arguments(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(asctime)s %(message)s", stream=sys.stderr)
    try:
        if args.full:
            report = full_copy(args.source, args.target, args.overwrite, args.copy_passwords)
        else:
            variations = [name.strip() for name in args.variations.split(",") if name.strip()]
            max_time = parse_time(args.time) if args.time else None
            report = shallow_copy(args.source, args.target, args.run_min, args.run_max, variations, max_time,
                                  args.overwrite, args.per_run, args.copy_passwords, args.time_limit)
    except CopyError as error:
        log.error("%s", error)
        return 2

    text_report = json.dumps(report, indent=2, default=str)
    if args.report_json:
        with open(args.report_json, "w") as report_file:
            report_file.write(text_report + "\n")
    print(text_report)
    if not report.get("complete", True):
        log.error("Time limit reached at %s; the copy is incomplete", report["stopped_at"])
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
