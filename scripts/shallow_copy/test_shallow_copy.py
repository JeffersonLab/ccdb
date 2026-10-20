"""
Tests of ccdb_shallow_copy.py on small SQLite databases built here.

Run from the repository root:
    python -m unittest discover -s scripts/shallow_copy -v

The central check: for every table, copied variation and run of the period, AlchemyProvider.get_assignment
on the copy returns the same assignment and constants as on the source. A seeded random database
exercises overlapping run ranges, ids out of creation order, variation fallback over several levels,
and assignments newer than --time.
"""

import datetime
import os
import random
import sqlite3
import sys
import tempfile
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ccdb_shallow_copy as shallow  # noqa: E402
import verify_shallow_copy  # noqa: E402

from ccdb.errors import ObjectIsNotFoundInDbError  # noqa: E402
from ccdb.model import INFINITE_RUN, TypeTable  # noqa: E402
from ccdb.provider import AlchemyProvider  # noqa: E402

BASE_TIME = datetime.datetime(2020, 1, 1, 12, 0, 0)

# id, name, parentId. 'orphan' is a root other than 'default': the provider finds nothing past it.
VARIATIONS = [(1, "default", 0), (2, "mc", 1), (3, "mc_sub", 2), (4, "calib", 1), (5, "orphan", 0), (6, "orphan_child", 5)]

# id, name, parentId
DIRECTORIES = [(1, "calib", 0), (2, "fcal", 1), (3, "empty_dir", 0)]

# id, name, directoryId; table 3 never gets an assignment
TABLES = [(1, "gains", 2), (2, "peds", 2), (3, "unused", 1), (4, "hostile", 3)]

HOSTILE_VAULT = "a|b&delimiter;c|<script>alert(1)</script>|O'Brien \"quoted\"|ünïcødé|line\nbreak"


def stamp(value):
    return value.isoformat(sep=" ")


class SourceBuilder:
    """Writes a CCDB SQLite source with the repository schema (no test content) and given rows"""

    def __init__(self, path):
        self.path = path
        shallow.prepare_target("sqlite:///" + path, overwrite=True).dispose()
        self.connection = sqlite3.connect(path)
        self.execute("INSERT INTO schemaVersions VALUES (1, 5)")
        self.execute("INSERT INTO users (id, created, lastActionTime, name, password, roles, info, isDeleted) "
                     "VALUES (1, '2014-01-01 00:00:00', '2014-01-01 00:00:00', 'anonymous', NULL, '', 'default user', 0)")
        self.execute("INSERT INTO users (id, created, lastActionTime, name, password, roles, info, isDeleted) "
                     "VALUES (2, '2014-01-01 00:00:00', '2014-01-01 00:00:00', 'expert', 'secret', 'all', 'has a password', 0)")
        for directory_id, name, parent_id in DIRECTORIES:
            self.execute("INSERT INTO directories (id, name, parentId, authorId, comment) VALUES (?, ?, ?, 1, 'dir <b>&</b>')",
                         directory_id, name, parent_id)
        for table_id, name, directory_id in TABLES:
            self.execute("INSERT INTO typeTables (id, directoryId, name, nRows, nColumns, nAssignments, authorId, comment) "
                         "VALUES (?, ?, ?, 1, 2, 999, 1, 'table')", table_id, directory_id, name)
            self.execute("INSERT INTO columns (id, name, typeId, columnType, \"order\") VALUES (?, 'x', ?, 'double', 0)", table_id * 2, table_id)
            self.execute("INSERT INTO columns (id, name, typeId, columnType, \"order\") VALUES (?, 'y', ?, 'double', 1)", table_id * 2 + 1, table_id)
        for variation_id, name, parent_id in VARIATIONS:
            self.execute("INSERT INTO variations (id, name, parentId, authorId) VALUES (?, ?, ?, 1)", variation_id, name, parent_id)
        self.execute("INSERT INTO logs (id, created, affectedIds, action, description, comment, authorId) "
                     "VALUES (1, '2014-01-01 00:00:00', 'x', 'create', 'source log', NULL, 1)")
        self.next_range_id = 1
        self.next_assignment_id = 1

    def execute(self, sql, *params):
        self.connection.execute(sql, params)

    def add_range(self, run_min, run_max, name=""):
        range_id = self.next_range_id
        self.next_range_id += 1
        self.execute("INSERT INTO runRanges (id, name, runMin, runMax, comment) VALUES (?, ?, ?, ?, 'range')", range_id, name, run_min, run_max)
        return range_id

    def add_assignment(self, table_id, variation_id, range_id, created, vault=None, assignment_id=None):
        assignment_id = assignment_id or self.next_assignment_id
        self.next_assignment_id = max(self.next_assignment_id, assignment_id) + 1
        vault = vault if vault is not None else "{0}|{1}".format(assignment_id, assignment_id * 1.5)
        self.execute("INSERT INTO constantSets (id, created, modified, vault, constantTypeId) VALUES (?, ?, ?, ?, ?)",
                     assignment_id, stamp(created), stamp(created), vault, table_id)
        self.execute("INSERT INTO assignments (id, created, modified, variationId, runRangeId, constantSetId, authorId, comment) "
                     "VALUES (?, ?, ?, ?, ?, ?, 1, 'assignment')", assignment_id, stamp(created), stamp(created), variation_id, range_id, assignment_id)
        return assignment_id

    def close(self):
        self.connection.commit()
        self.connection.close()


def provider_for(path):
    engine = create_engine("sqlite:///" + path)
    provider = AlchemyProvider()
    provider.attach(engine, sessionmaker(bind=engine)())
    return provider


def resolve(provider, table_id, run, variation, max_time):
    """(assignment id, vault) or None, as a CCDB reader sees it"""
    table = provider.session.get(TypeTable, table_id)
    assignment = shallow.lookup(provider, table, run, variation, max_time)
    return None if assignment is None else (assignment.id, assignment.constant_set.vault)


def rows(path, sql):
    connection = sqlite3.connect(path)
    try:
        return connection.execute(sql).fetchall()
    finally:
        connection.close()


class ShallowCopyTestBase(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.source_path = os.path.join(self.tmp.name, "source.sqlite")
        self.target_path = os.path.join(self.tmp.name, "target.sqlite")

    def tearDown(self):
        self.tmp.cleanup()

    def copy(self, run_min, run_max, variations=("default",), max_time=None, target_path=None, **options):
        return shallow.shallow_copy("sqlite:///" + self.source_path, "sqlite:///" + (target_path or self.target_path),
                                    run_min, run_max, list(variations), max_time, **options)

    def assert_copy_matches_source(self, run_min, run_max, variations, max_time, target_path=None):
        """Every table x copied variation x run of the period: the copy answers as the source does,
        with the copy time and with no time. Returns the number of lookups that found an assignment."""
        source = provider_for(self.source_path)
        copy = provider_for(target_path or self.target_path)
        if list(variations) == ["*"]:
            variations = [variation[1] for variation in VARIATIONS]
        found = 0
        for table_id, _name, _directory in TABLES:
            for variation in variations:
                for run in range(run_min, run_max + 1):
                    expected = resolve(source, table_id, run, variation, max_time)
                    self.assertEqual(expected, resolve(copy, table_id, run, variation, max_time),
                                     "table {0} variation {1} run {2}".format(table_id, variation, run))
                    self.assertEqual(expected, resolve(copy, table_id, run, variation, None))
                    found += expected is not None
        return found


class TestRandomDatabase(ShallowCopyTestBase):
    """Seeded random content: the bulk selection must equal the per-run reference and the source"""

    RUN_MIN, RUN_MAX = 20, 60

    def build(self, seed):
        generator = random.Random(seed)
        builder = SourceBuilder(self.source_path)
        boundaries = [0, 1, 19, 20, 21, 35, 59, 60, 61, 100, INFINITE_RUN]
        ranges = [builder.add_range(0, INFINITE_RUN, "all")]
        for _ in range(25):
            first, last = sorted(generator.sample(boundaries + [generator.randint(0, 120) for _ in range(5)], 2))
            ranges.append(builder.add_range(first, last))
        ranges.append(builder.add_range(self.RUN_MAX + 1, INFINITE_RUN))   # after the period only
        ranges.append(builder.add_range(0, self.RUN_MIN - 1))               # before the period only
        ranges.append(builder.add_range(40, 40, "single"))
        variation_ids = [variation[0] for variation in VARIATIONS]
        for _ in range(300):
            table_id = generator.choice([1, 2, 4])
            created = BASE_TIME + datetime.timedelta(minutes=generator.randint(0, 10000))
            # ids are not in creation order: the winner is the highest id, not the newest timestamp
            builder.add_assignment(table_id, generator.choice(variation_ids), generator.choice(ranges), created,
                                   vault=HOSTILE_VAULT if table_id == 4 else None)
        builder.close()

    def check(self, seed, variations, max_time):
        self.build(seed)
        bulk = self.copy(self.RUN_MIN, self.RUN_MAX, variations, max_time)
        self.assertTrue(bulk["complete"])
        found = self.assert_copy_matches_source(self.RUN_MIN, self.RUN_MAX, variations, max_time)
        self.assertGreater(found, 0)

        reference_path = os.path.join(self.tmp.name, "reference.sqlite")
        reference = self.copy(self.RUN_MIN, self.RUN_MAX, variations, max_time, target_path=reference_path, per_run=True)
        self.assertEqual(bulk["assignments"], reference["assignments"])
        self.assertEqual(rows(self.target_path, "SELECT id, runRangeId, constantSetId FROM assignments ORDER BY id"),
                         rows(reference_path, "SELECT id, runRangeId, constantSetId FROM assignments ORDER BY id"))
        self.assertEqual(rows(self.target_path, "SELECT * FROM runRanges ORDER BY id"), rows(reference_path, "SELECT * FROM runRanges ORDER BY id"))
        return bulk

    def test_default_latest(self):
        report = self.check(1, ["default"], None)
        self.assertEqual(report["copied_variations"], ["default"])

    def test_mc_and_default_at_time(self):
        self.check(2, ["default", "mc"], BASE_TIME + datetime.timedelta(minutes=5000))

    def test_deep_chain_and_orphan_root(self):
        report = self.check(3, ["mc_sub", "orphan_child"], BASE_TIME + datetime.timedelta(minutes=7000))
        self.assertEqual(report["copied_variations"], ["default", "mc", "mc_sub", "orphan", "orphan_child"])

    def test_all_variations(self):
        report = self.check(4, ["*"], None)
        self.assertEqual(len(report["copied_variations"]), len(VARIATIONS))

    def test_many_seeds(self):
        for seed in range(10, 16):
            with self.subTest(seed=seed):
                self.tearDown()
                self.setUp()
                self.check(seed, ["mc", "calib"], BASE_TIME + datetime.timedelta(minutes=seed * 600))


class TestHandPickedCases(ShallowCopyTestBase):
    """Small content where every expected row is known"""

    def setUp(self):
        super().setUp()
        builder = SourceBuilder(self.source_path)
        self.wide = builder.add_range(0, INFINITE_RUN, "all runs")
        self.inside = builder.add_range(110, 120, "inside")
        self.before = builder.add_range(0, 99, "before")
        self.after = builder.add_range(201, 300, "after")
        self.edge = builder.add_range(200, 250, "edge")
        # table 1, default: old wide assignment, newer narrow one, one created after the copy time
        self.old_wide = builder.add_assignment(1, 1, self.wide, BASE_TIME)
        self.narrow = builder.add_assignment(1, 1, self.inside, BASE_TIME + datetime.timedelta(days=1))
        self.too_new = builder.add_assignment(1, 1, self.wide, BASE_TIME + datetime.timedelta(days=10))
        self.before_period = builder.add_assignment(1, 1, self.before, BASE_TIME + datetime.timedelta(days=2))
        self.after_period = builder.add_assignment(1, 1, self.after, BASE_TIME + datetime.timedelta(days=2))
        self.at_edge = builder.add_assignment(1, 1, self.edge, BASE_TIME + datetime.timedelta(days=2))
        # table 1, mc: covers part of the period; the rest falls back to default
        self.mc_part = builder.add_assignment(1, 2, self.inside, BASE_TIME + datetime.timedelta(days=3))
        # table 2, calib only (not copied when only default and mc are asked for)
        self.calib_only = builder.add_assignment(2, 4, self.wide, BASE_TIME)
        # table 4: hostile text, created exactly at the copy time (included: created <= time)
        self.copy_time = BASE_TIME + datetime.timedelta(days=5)
        self.hostile = builder.add_assignment(4, 1, self.wide, self.copy_time, vault=HOSTILE_VAULT)
        builder.close()

    def test_selection_and_clipping(self):
        report = self.copy(100, 200, ["default", "mc"], self.copy_time)
        self.assertEqual(report["copied_variations"], ["default", "mc"])
        copied = {row[0] for row in rows(self.target_path, "SELECT id FROM assignments")}
        self.assertEqual(copied, {self.old_wide, self.narrow, self.at_edge, self.mc_part, self.hostile})

        ranges = {row[0]: row[1:] for row in rows(self.target_path, "SELECT id, name, runMin, runMax FROM runRanges")}
        self.assertEqual(ranges[self.inside], ("inside", 110, 120))          # inside the period: original row
        self.assertNotIn(self.wide, ranges)
        self.assertNotIn(self.edge, ranges)
        self.assertEqual(sorted(value[1:] for value in ranges.values()), [(100, 200), (110, 120), (200, 200)])
        self.assert_copy_matches_source(100, 200, ["default", "mc"], self.copy_time)

        copy = provider_for(self.target_path)
        for outside_run in (0, 99, 201, INFINITE_RUN):
            self.assertIsNone(resolve(copy, 1, outside_run, "default", None), outside_run)
        with self.assertRaises(ObjectIsNotFoundInDbError):
            resolve(copy, 2, 150, "calib", None)       # a variation that was not copied fails loudly
        self.assertEqual(rows(self.target_path, "SELECT name FROM variations ORDER BY id"), [("default",), ("mc",)])

    def test_single_run(self):
        report = self.copy(115, 115, ["mc"])
        # table 1: mc has its own assignment; table 2: only calib has one; table 4: falls back to default
        self.assertEqual(report["assignments"], 2)
        copied = {row[0] for row in rows(self.target_path, "SELECT id FROM assignments")}
        self.assertEqual(copied, {self.mc_part, self.hostile})
        self.assert_copy_matches_source(115, 115, ["mc"], None)

    def test_time_before_everything(self):
        report = self.copy(0, INFINITE_RUN, ["default"], BASE_TIME - datetime.timedelta(seconds=1))
        self.assertEqual(report["assignments"], 0)
        self.assertEqual(rows(self.target_path, "SELECT COUNT(*) FROM typeTables"), [(len(TABLES),)])
        self.assertEqual(rows(self.target_path, "SELECT COUNT(*) FROM directories"), [(len(DIRECTORIES),)])
        self.assertEqual(rows(self.target_path, "SELECT SUM(nAssignments) FROM typeTables"), [(0,)])

    def test_whole_run_space(self):
        self.copy(0, INFINITE_RUN, ["default", "mc"])
        copied = {row[0] for row in rows(self.target_path, "SELECT id FROM assignments")}
        # table 1 default, by descending id: at_edge 200-250, after 251-300, before 0-99, too_new the rest
        self.assertEqual(copied, {self.at_edge, self.after_period, self.before_period, self.too_new, self.mc_part, self.hostile})
        self.assertEqual(rows(self.target_path, "SELECT nAssignments FROM typeTables ORDER BY id"), [(5,), (0,), (0,), (1,)])
        self.assert_copy_matches_source(0, 400, ["default", "mc"], None)

    def test_metadata_text_and_provenance(self):
        report = self.copy(100, 200, ["mc"], self.copy_time)
        self.assertEqual(rows(self.target_path, "SELECT vault FROM constantSets WHERE id = {0}".format(self.hostile)), [(HOSTILE_VAULT,)])
        self.assertEqual(rows(self.target_path, "SELECT name, password FROM users ORDER BY id"), [("anonymous", None), ("expert", None)])
        self.assertEqual(rows(self.target_path, "SELECT schemaVersion FROM schemaVersions"), [(5,)])
        self.assertEqual(rows(self.target_path, "SELECT comment FROM directories WHERE id = 1"), [("dir <b>&</b>",)])
        self.assertEqual(rows(self.target_path, "SELECT created FROM assignments WHERE id = {0}".format(self.old_wide)), [(stamp(BASE_TIME),)])
        log_rows = rows(self.target_path, "SELECT description, comment FROM logs")
        self.assertEqual(len(log_rows), 1)
        self.assertIn("runs 100-200, variations mc", log_rows[0][0])
        self.assertIn("source.sqlite", log_rows[0][1])
        self.assertEqual(report["target_bytes"], os.path.getsize(self.target_path))
        indexes = {row[0] for row in rows(self.target_path, "SELECT name FROM sqlite_master WHERE type = 'index'")}
        self.assertIn("constantSets_fk_constantSets_constantTypes1_idx", indexes)

    def test_copy_passwords_flag(self):
        self.copy(100, 200, copy_passwords=True)
        self.assertEqual(rows(self.target_path, "SELECT password FROM users WHERE id = 2"), [("secret",)])

    def test_source_columns_missing_in_target_schema_are_kept(self):
        connection = sqlite3.connect(self.source_path)
        connection.execute("ALTER TABLE variations ADD COLUMN extraFlag INTEGER NOT NULL DEFAULT 0")
        connection.execute("UPDATE variations SET extraFlag = 7 WHERE name = 'mc'")
        connection.commit()
        connection.close()
        report = self.copy(100, 200, ["mc"])
        self.assertIn("variations.extraFlag", report["added_columns"])
        self.assertEqual(rows(self.target_path, "SELECT name, extraFlag FROM variations ORDER BY id"), [("default", 0), ("mc", 7)])

    def test_existing_target(self):
        self.copy(100, 200)
        with self.assertRaises(shallow.CopyError):
            self.copy(100, 200)
        report = self.copy(150, 150, overwrite=True)
        self.assertEqual(report["run_min"], 150)
        self.assertEqual(len(rows(self.target_path, "SELECT * FROM logs")), 1)

    def test_bad_arguments(self):
        with self.assertRaises(shallow.CopyError):
            self.copy(200, 100)
        with self.assertRaises(shallow.CopyError):
            self.copy(100, 200, ["no_such_variation"])
        self.assertFalse(os.path.exists(self.target_path))

    def test_duplicate_variation_names(self):
        connection = sqlite3.connect(self.source_path)
        connection.execute("INSERT INTO variations (id, name, parentId, authorId) VALUES (99, 'mc', 1, 1)")
        connection.commit()
        connection.close()
        with self.assertRaises(shallow.CopyError):
            self.copy(100, 200, ["mc"])
        self.copy(100, 200, ["calib"])     # a chain without the duplicated name still works

    def test_wrong_schema_version(self):
        connection = sqlite3.connect(self.source_path)
        connection.execute("UPDATE schemaVersions SET schemaVersion = 4")
        connection.commit()
        connection.close()
        with self.assertRaises(shallow.CopyError):
            self.copy(100, 200)

    def test_time_limit_reports_where_it_stopped(self):
        report = self.copy(0, 100000, ["default"], per_run=True, time_limit=0.2)
        self.assertFalse(report["complete"])
        self.assertIn("table 1/4 /calib/fcal/gains, variation default, run", report["stopped_at"])
        self.assertIn("INCOMPLETE", rows(self.target_path, "SELECT description FROM logs")[0][0])

    def test_full_copy(self):
        report = shallow.full_copy("sqlite:///" + self.source_path, "sqlite:///" + self.target_path)
        for table in ("assignments", "constantSets", "runRanges", "variations", "logs", "directories", "typeTables", "columns"):
            self.assertEqual(rows(self.source_path, "SELECT * FROM {0} ORDER BY 1".format(table)),
                             rows(self.target_path, "SELECT * FROM {0} ORDER BY 1".format(table)), table)
        self.assertEqual(rows(self.target_path, "SELECT password FROM users WHERE id = 2"), [(None,)])
        self.assertEqual(report["rows"]["assignments"], 9)

    def test_command_line(self):
        report_path = os.path.join(self.tmp.name, "report.json")
        source, target = "sqlite:///" + self.source_path, "sqlite:///" + self.target_path
        self.assertEqual(shallow.main([source, target, "--run-min", "100", "--run-max", "200", "--variations", "default, mc",
                                       "--time", "2020-01-06_12-00-00", "--report-json", report_path]), 0)
        self.assertTrue(os.path.exists(report_path))
        self.assertEqual(shallow.main([source, target, "--run-min", "100"]), 2)          # target exists
        self.assertEqual(shallow.main([source, target, "--run-min", "1", "--overwrite", "--per-run", "--run-max", "100000",
                                       "--time-limit", "0.1"]), 3)


class TestVerify(ShallowCopyTestBase):
    """verify_shallow_copy.py passes a correct copy and catches a damaged one"""

    RUN_MIN, RUN_MAX = TestRandomDatabase.RUN_MIN, TestRandomDatabase.RUN_MAX

    def setUp(self):
        super().setUp()
        TestRandomDatabase.build(self, seed=7)
        self.copy(20, 60, ["default", "mc"])

    def verify(self, **options):
        return verify_shallow_copy.verify("sqlite:///" + self.source_path, "sqlite:///" + self.target_path, 20, 60,
                                          ["default", "mc"], None, workers=2, **options)

    def damage(self, sql):
        connection = sqlite3.connect(self.target_path)
        connection.execute(sql)
        connection.commit()
        connection.close()

    def test_correct_copy_passes(self):
        report = self.verify()
        self.assertTrue(report["passed"], report["mismatches"])
        self.assertEqual(report["lookups"], len(TABLES) * 2 * 41)

    def test_changed_constants(self):
        self.damage("UPDATE constantSets SET vault = vault || '|1' WHERE id = (SELECT MIN(id) FROM constantSets)")
        report = self.verify()
        self.assertFalse(report["passed"])
        self.assertEqual(report["mismatches"][0]["problem"], "constants differ")

    def test_missing_assignment(self):
        self.damage("DELETE FROM assignments WHERE id = (SELECT MAX(id) FROM assignments)")
        self.assertFalse(self.verify()["passed"])

    def test_assignment_outside_period(self):
        self.damage("UPDATE runRanges SET runMax = 61 WHERE runMax = 60")
        report = self.verify()
        self.assertFalse(report["passed"])
        self.assertIn("outside the period", report["mismatches"][0]["problem"])

    def test_time_limit(self):
        report = self.verify(time_limit=0.000001)
        self.assertFalse(report["complete"])


class TestHelpers(unittest.TestCase):

    def test_claim_runs(self):
        self.assertEqual(shallow.claim_runs([(10, 20)], 0, 5), ([(10, 20)], False))
        self.assertEqual(shallow.claim_runs([(10, 20)], 0, 10), ([(11, 20)], True))
        self.assertEqual(shallow.claim_runs([(10, 20)], 12, 15), ([(10, 11), (16, 20)], True))
        self.assertEqual(shallow.claim_runs([(10, 20), (30, 40)], 15, 35), ([(10, 14), (36, 40)], True))
        self.assertEqual(shallow.claim_runs([(10, 20)], 0, INFINITE_RUN), ([], True))

    def test_as_datetime(self):
        self.assertEqual(shallow.as_datetime("2020-01-01 12:00:00"), BASE_TIME)
        self.assertEqual(shallow.as_datetime("2020-01-01 12:00:00.5"), BASE_TIME.replace(microsecond=500000))
        self.assertEqual(shallow.as_datetime("2020-01-01 12:00:00.123456"), BASE_TIME.replace(microsecond=123456))
        self.assertEqual(shallow.as_datetime(BASE_TIME), BASE_TIME)
        self.assertEqual(shallow.as_datetime("0000-00-00 00:00:00"), datetime.datetime.min)

    def test_hide_password(self):
        self.assertNotIn("secret", shallow.hide_password("mysql://user:secret@host/ccdb"))


if __name__ == "__main__":
    unittest.main()
