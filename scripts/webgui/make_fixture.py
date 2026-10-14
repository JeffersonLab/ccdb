"""Build the deterministic fixture database the web GUI checks run against.

Usage: python make_fixture.py --space DIR [--out PATH] [--verify]

The result is CCDB schema v5 with the standard test content (ccdb.sql.sqlite_schema) plus the
cases the web GUI checks need:

- /calib/fcal/gains: 3600 assignments over 6 variations and run ranges that end at 2147483647
- /deep/l1/l2/l3/l4/l5/l6/bottom: a table seven directory levels down
- /bulk/dNN/tNNN: 1000 tables so the tree page can be sized up
- /hostile: names and comments with <script>, quotes, &, newlines and non-ASCII text
- a 4-level variation chain default -> test -> subtest -> subsubtest, plus calib and calib_v2
- 2400 log records from three authors

Every timestamp and every random value comes from a fixed seed, so the SQLite file hashes the same
on each build. Trap: the provider's create_* methods stamp datetime.now() and write log records,
so this script inserts ORM objects directly and never calls them. pages.py refers to the paths
above; change both files together.
"""
import argparse
import datetime
import hashlib
import os
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import workspace  # noqa: E402

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from ccdb.model import Assignment, ConstantSet, Directory, LogRecord, RunRange, TypeTable, TypeTableColumn, User, Variation
from ccdb.sql.sqlite_schema import init_sqlite_database

INFINITE_RUN = 2147483647
BASE_TIME = datetime.datetime(2020, 1, 1, 12, 0, 0)

HOSTILE_COMMENT = 'Tag <script>alert("x")</script> & "double" \'single\'\nsecond line — Привет ✓ ünïcödé'
HOSTILE_TABLE_NAME = "x\"y'z&<script>alert(1)<b>"
UNICODE_TABLE_NAME = "unicode_Привет_✓"


def new(model, **attrs):
    """Construct a model object and set attributes. Directory has a no-argument __init__, so keywords are not accepted."""
    obj = model()
    for name, value in attrs.items():
        setattr(obj, name, value)
    return obj


def at(minutes):
    """A fixed timestamp: BASE_TIME plus the given minutes."""
    return BASE_TIME + datetime.timedelta(minutes=minutes)


class Builder:
    def __init__(self, session, rng):
        self.session = session
        self.rng = rng
        self.clock = 0  # minutes since BASE_TIME; every new object gets the next tick
        self.users = {u.name: u for u in session.query(User).all()}

    def tick(self):
        self.clock += 1
        return at(self.clock)

    def user_id(self, name):
        return self.users[name].id

    def add_user(self, name, info):
        user = new(User, name=name, password="", _roles_str="", info=info, is_deleted=False, created=self.tick(), last_action_time=self.tick())
        self.session.add(user)
        self.session.flush()
        self.users[name] = user
        return user

    def add_directory(self, name, parent, comment="", author="test_user"):
        stamp = self.tick()
        directory = new(Directory, name=name, comment=comment, parent_id=parent.id if parent else 0, created=stamp, modified=stamp, author_id=self.user_id(author))
        self.session.add(directory)
        self.session.flush()
        return directory

    def add_table(self, name, directory, columns, rows_count=1, comment="", author="test_user"):
        """columns: list of (name, type)."""
        stamp = self.tick()
        table = new(TypeTable, name=name, comment=comment, parent_dir_id=directory.id, rows_count=rows_count, _columns_count=len(columns), created=stamp, modified=stamp, author_id=self.user_id(author))
        self.session.add(table)
        self.session.flush()
        for order, (column_name, column_type) in enumerate(columns):
            self.session.add(new(TypeTableColumn, name=column_name, type=column_type, order=order, type_table_id=table.id, created=stamp, modified=stamp))
        self.session.flush()
        return table

    def add_variation(self, name, parent, comment, author="test_user"):
        stamp = self.tick()
        variation = new(Variation, name=name, comment=comment, parent_id=parent.id, created=stamp, modified=stamp, author_id=self.user_id(author), is_locked=False, lock_time=stamp, _description=comment[:255])
        self.session.add(variation)
        self.session.flush()
        return variation

    def add_run_range(self, run_min, run_max, name=""):
        stamp = self.tick()
        run_range = new(RunRange, min=run_min, max=run_max, name=name, comment="", created=stamp, modified=stamp)
        self.session.add(run_range)
        self.session.flush()
        return run_range

    def add_assignment(self, table, run_range, variation, rows, comment, author="test_user"):
        stamp = self.tick()
        constant_set = new(ConstantSet, type_table_id=table.id, created=stamp, modified=stamp)
        constant_set.data_table = rows
        assignment = new(Assignment, constant_set=constant_set, run_range_id=run_range.id, variation_id=variation.id, _comment=comment, author_id=self.user_id(author), created=stamp, modified=stamp)
        self.session.add(constant_set)
        self.session.add(assignment)
        return assignment

    def add_log(self, author, action, affected, description, comment):
        self.session.add(new(LogRecord, created=self.tick(), affected_ids="|" + affected + "|", action=action, description=description, comment=comment, author_id=self.user_id(author)))


def build(session):
    rng = random.Random(20261013)
    b = Builder(session, rng)
    b.add_user("alice", "Calibration shift worker")
    b.add_user("bob", "Detector expert")
    authors = ["test_user", "alice", "bob"]

    # Variations: the standard content has default(1) -> test(3) -> subtest(4) and mc(2).
    variations = {v.name: v for v in session.query(Variation).all()}
    variations["subsubtest"] = b.add_variation("subsubtest", variations["subtest"], "Fourth level of the test chain")
    variations["calib"] = b.add_variation("calib", variations["default"], "Calibration pass 1 " + HOSTILE_COMMENT)
    variations["calib_v2"] = b.add_variation("calib_v2", variations["calib"], "Calibration pass 2, inherits calib")

    # Big table: 3600 assignments over 6 variations and 24 run ranges, 8 of them open-ended.
    calib_dir = b.add_directory("calib", None, "Calibration constants")
    fcal_dir = b.add_directory("fcal", calib_dir, "Forward calorimeter")
    gains = b.add_table("gains", fcal_dir, [("channel", "int"), ("gain", "double"), ("sigma", "double")], rows_count=4, comment="Per-block gains. " + HOSTILE_COMMENT)
    run_ranges = [b.add_run_range(start, start + 999) for start in range(0, 16000, 1000)] + [b.add_run_range(start, INFINITE_RUN) for start in range(10000, 50000, 5000)]
    big_variations = [variations[n] for n in ("default", "mc", "test", "subtest", "calib", "calib_v2")]
    for i in range(3600):
        rows = [[str(row_i), f"{rng.uniform(0.5, 1.5):.6f}", f"{rng.uniform(0.0, 0.1):.6f}"] for row_i in range(4)]
        comment = HOSTILE_COMMENT if i % 500 == 0 else f"gains iteration {i} by shift"
        b.add_assignment(gains, rng.choice(run_ranges), big_variations[i % 6], rows, comment, rng.choice(authors))
    session.flush()

    # Small sibling with one open-ended assignment, for the infinity rendering check.
    pedestals = b.add_table("pedestals", fcal_dir, [("channel", "int"), ("pedestal", "double")], rows_count=2)
    b.add_assignment(pedestals, run_ranges[-1], variations["default"], [["0", "100.5"], ["1", "101.5"]], "open-ended run range")

    # Seven directory levels, one table at the bottom.
    parent = b.add_directory("deep", None, "Depth test")
    for level in range(1, 7):
        parent = b.add_directory(f"l{level}", parent)
    bottom = b.add_table("bottom", parent, [("v", "double")])
    b.add_assignment(bottom, run_ranges[0], variations["default"], [["42.0"]], "bottom of the tree")

    # 1000 bulk tables: 25 directories with 40 tables each, 1 to 3 columns.
    bulk = b.add_directory("bulk", None, "Volume test: 1000 tables")
    types = ["int", "double", "string", "bool"]
    for dir_i in range(1, 26):
        sub = b.add_directory(f"d{dir_i:02d}", bulk)
        for table_i in range(1, 41):
            columns = [(f"c{c}", rng.choice(types)) for c in range(rng.randint(1, 3))]
            b.add_table(f"t{table_i:03d}", sub, columns, rows_count=rng.randint(1, 5), comment=f"bulk table {dir_i}/{table_i}")

    # Hostile names and comments, kept in their own subtree so a crash stays local to it.
    hostile = b.add_directory("hostile", None, HOSTILE_COMMENT)
    hostile_table = b.add_table(HOSTILE_TABLE_NAME, hostile, [("a", "string"), ("b", "int")], rows_count=2, comment=HOSTILE_COMMENT)
    b.add_assignment(hostile_table, run_ranges[0], variations["default"], [["<b>bold</b>", "1"], ["it's & \"quoted\"", "2"]], HOSTILE_COMMENT)
    unicode_table = b.add_table(UNICODE_TABLE_NAME, hostile, [("значение", "double")], comment="Non-ASCII name and column")
    b.add_assignment(unicode_table, run_ranges[0], variations["default"], [["3.14"]], "Привет, мир ✓")

    # 2400 log records from three authors, in time order.
    actions = ["create", "update", "delete"]
    for i in range(2400):
        author = authors[i % 3]
        b.add_log(author, actions[i % 3], f"assignments{i + 10}", f"Created assignment '/calib/fcal/gains:{i}:default'", HOSTILE_COMMENT if i % 400 == 0 else f"log comment {i}")
    session.commit()


def sha256_of(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def make(out_path):
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        out_path.unlink()
    engine = create_engine("sqlite:///" + str(out_path))
    init_sqlite_database(engine)
    with Session(engine) as session:
        build(session)
    with engine.connect() as connection:
        connection.execute(text("VACUUM"))
    engine.dispose()
    return sha256_of(out_path)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    workspace.add_space_argument(parser)
    parser.add_argument("--out", help="output file (default: <space>/fixture/ccdb_fixture.sqlite)")
    parser.add_argument("--verify", action="store_true", help="build a second copy and check that both hashes match")
    args = parser.parse_args()
    out = Path(args.out) if args.out else workspace.fixture_path(workspace.resolve(args))
    digest = make(out)
    print(f"{out}  sha256={digest}  bytes={os.path.getsize(out)}")
    if args.verify:
        second = out.with_suffix(".verify.sqlite")
        other = make(second)
        second.unlink()
        print("deterministic:", "yes" if other == digest else f"NO ({other})")
        sys.exit(0 if other == digest else 1)


if __name__ == "__main__":
    main()
