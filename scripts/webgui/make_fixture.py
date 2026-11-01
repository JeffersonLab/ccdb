"""Build the deterministic fixture database the web GUI checks run against.

Usage: python make_fixture.py --space DIR [--out PATH] [--verify]

The result is CCDB schema 6 with the standard test content (ccdb.sql.sqlite_schema) plus the
cases the web GUI checks need:

- /calib/fcal/gains: 3600 assignments over 6 variations and run ranges that end at 2147483647
- /calib/ccal/parms: one row, six columns, one assignment (the vertical data layout)
- /deep/l1/l2/l3/l4/l5/l6/bottom: a table seven directory levels down
- /bulk/dNN/tNNN: 1000 tables so the tree page can be sized up
- /hostile: names and comments with <script>, quotes, &, newlines and non-ASCII text
- a 4-level variation chain default -> test -> subtest -> subsubtest, plus calib and calib_v2
- two comparison pairs: /calib/ccal/parms in default and calib (two cells differ), /calib/ccal/channels 600 rows x 4 columns with two default assignments (seven cells differ)
- a log record with a 60-line comment of 135-character lines, then three records naming a table, a variation and a deleted table, for the log record page
- 2400 log records from three authors
- /schema6, the schema 6 cases, added last: /schema6/shared with two assignments that share one constant set
  (vers -l shows 2) and units on two of its three columns; /schema6/numeric with 1.0 and 1.00, two sets with two
  hashes; a deprecated directory /schema6/retired, a deprecated table /schema6/retired_table and a deprecated
  variation retired; the tags fixture_newest (at the creation time of the newest assignment) and fixture_past;
  an instance property and a property of /schema6/shared; a log record per new assignment

Every timestamp and every random value comes from a fixed seed, so the SQLite file hashes the same
on each build. The timestamps are naive values with no zone; tags.snapshotTime is defined as a UTC
instant, so the fixture's tags line up with its assignment times when those are read as UTC too.
Trap: the provider's create_* methods stamp datetime.now() and write log records,
so this script inserts ORM objects directly and never calls them. The same holds for the columns that
only the server clock fills (tags.created, properties.modified): set them here. pages.py refers to the
paths and ids above; change both files together.
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

from ccdb.model import Assignment, ConstantSet, Directory, LogRecord, Property, RunRange, Tag, TypeTable, TypeTableColumn, User, Variation
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

    def add_table(self, name, directory, columns, rows_count=1, comment="", author="test_user", units=None):
        """columns: list of (name, type). units: column name -> units text, for the columns that have units."""
        stamp = self.tick()
        units = units or {}
        unknown = set(units) - {column_name for column_name, _ in columns}
        if unknown:  # a misspelt key would silently give a table without units
            raise ValueError("units for unknown columns of {0}: {1}".format(name, sorted(unknown)))
        table = new(TypeTable, name=name, comment=comment, parent_dir_id=directory.id, rows_count=rows_count, _columns_count=len(columns), created=stamp, modified=stamp, author_id=self.user_id(author))
        self.session.add(table)
        self.session.flush()
        for order, (column_name, column_type) in enumerate(columns):
            self.session.add(new(TypeTableColumn, name=column_name, type=column_type, order=order, type_table_id=table.id, created=stamp, modified=stamp, units=units.get(column_name)))
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

    def add_sharing_assignment(self, constant_set, run_range, variation, comment, author="test_user"):
        """A second assignment of a stored set, as create_assignment makes it for data equal byte for byte to that set."""
        stamp = self.tick()
        assignment = new(Assignment, constant_set=constant_set, run_range_id=run_range.id, variation_id=variation.id, _comment=comment, author_id=self.user_id(author), created=stamp, modified=stamp)
        self.session.add(assignment)
        return assignment

    def deprecate(self, obj, author, comment):
        """Sets the four deprecation columns of a directory, table or variation."""
        obj.is_deprecated = True
        obj.deprecated_by_user_id = self.user_id(author)
        obj.deprecated_time = self.tick()
        obj.deprecation_comment = comment
        # The change moves modified to the deprecation time; for directories and tables this also stops onupdate
        # from stamping datetime.now(), which would break the fixed-seed build.
        obj.modified = obj.deprecated_time

    def add_tag(self, name, variation, snapshot_time, comment, author="test_user"):
        tag = new(Tag, name=name, variation_id=variation.id, snapshot_time=snapshot_time, comment=comment, author_id=self.user_id(author), created=self.tick())
        self.session.add(tag)
        return tag

    def add_property(self, owner_type, owner_id, name, value, author="test_user"):
        prop = new(Property, owner_type=owner_type, owner_id=owner_id, name=name, value=value, author_id=self.user_id(author), modified=self.tick())
        self.session.add(prop)
        return prop

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

    # A key-value style table, one row and six columns, as many CCDB parameter tables are: the data view
    # shows it vertically. Added after the logs so the timestamps of everything above stay as they were.
    ccal = b.add_directory("ccal", calib_dir, "Compton calorimeter")
    parms = b.add_table("parms", ccal, [("threshold", "double"), ("n_crystals", "int"), ("scale", "double"), ("offset", "double"), ("use_fit", "bool"), ("label", "string")],
                        rows_count=1, comment="Key-value parameters: one row, six columns")
    b.add_assignment(parms, run_ranges[0], variations["default"], [["0.195", "144", "2.17828", "1.08421", "1", "pass1"]], "initial parameters")

    # Two pairs for the comparison page, after everything else so no earlier timestamp moves.
    # parms gets its second assignment in `calib`: a request without a timestamp resolves to the newest
    # assignment, so a second `default` one would change what the parms pages show. Two of six values differ.
    b.add_assignment(parms, run_ranges[0], variations["calib"], [["0.200", "144", "2.17828", "1.08421", "1", "pass2"]], "calibration pass values", "alice")
    # channels: 600 rows, so the comparison pages have paging to show. Two default assignments; the second
    # differs in seven cells spread over three pages of 200 rows: gains in rows 3, 199, 399, 599, the sigma
    # in row 150, the status in rows 250 and 450.
    channels = b.add_table("channels", ccal, [("channel", "int"), ("gain", "double"), ("sigma", "double"), ("status", "string")],
                           rows_count=600, comment="Per-channel calibration: 600 rows, two passes")
    first_pass = [[str(row_i), f"{rng.uniform(0.8, 1.2):.5f}", f"{rng.uniform(0.0, 0.05):.5f}", "ok"] for row_i in range(600)]
    second_pass = [list(row) for row in first_pass]
    for row_i in (3, 199, 399, 599):
        second_pass[row_i][1] = f"{float(first_pass[row_i][1]) * 1.05:.5f}"
    second_pass[150][2] = "0.09999"
    second_pass[250][3] = "bad"
    second_pass[450][3] = "noisy"
    b.add_assignment(channels, run_ranges[0], variations["default"], first_pass, "first pass", "alice")
    b.add_assignment(channels, run_ranges[0], variations["default"], second_pass, "second pass: four gains, one sigma, two statuses", "bob")

    # A log record with a long multi-line comment, as the material-map uploads on the production database have
    # (comments of 65 535 characters, 500 lines of aligned program output), for the log record page.
    long_comment = "\n".join("line {0:3d} ".format(line_i) + ("x" * 10 + " ") * 11 + "end{0}".format(line_i) for line_i in range(60))
    b.add_log("alice", "create", "assignments3610", "Created assignment '/calib/ccal/parms:0:default'", long_comment)
    # Records naming a table, a variation and an object that no longer exists, for the links of the record page.
    b.add_log("bob", "create", "typeTables{0}".format(channels.id), "Created table '/calib/ccal/channels'", "")
    b.add_log("bob", "update", "variations{0}".format(variations["calib_v2"].id), "Updated variation 'calib_v2'", "")
    b.add_log("bob", "delete", "typeTables999999", "Deleted table '/gone/table'", "a table that no longer exists")
    session.flush()
    add_schema6_cases(b, variations, run_ranges)
    session.commit()


def add_schema6_cases(b, variations, run_ranges):
    """The schema 6 objects, in their own directory /schema6 and after everything else, so no earlier id or timestamp
    moves and only the pages that list every directory, table, variation or log record see them.

    Literal values that tests compare with, from a build of this script (sha256 of the vault's UTF-8 bytes):
      assignments 3614 and 3615: /schema6/shared, runs 0-999 and 1000-1999, both constant set 3614,
        vault "0|1.25|100.5|1|1.5|101.0|2|0.75|99.5", sha256 c4c90edd40236d79a696db3f2999ae5c8fe02a21de3b88d058dae1a370a5f907
      assignment 3616: /schema6/numeric, runs 0-999, set 3615, vault "1.0", sha256 d0ff5974b6aa52cf562bea5921840c032a860a91a3512f7fe8f768f6bbe005f6
      assignment 3617: /schema6/numeric, runs 1000-1999, set 3616, vault "1.00", sha256 cf9dcf6da8a82be1335c398a4005def7ee3a53d4698c59dbc6b2b14e72d1263c
      assignment 3618: /schema6/retired_table, set 3617
    """
    default = variations["default"]
    schema6 = b.add_directory("schema6", None, "Schema 6 cases: shared constant sets, deprecation, tags, units, properties")

    # One constant set given to two assignments: the data of runs 0-999 were found valid for runs 1000-1999 too, so the
    # second upload stored no new set. vers -l counts 2 sharers for both.
    shared = b.add_table("shared", schema6, [("channel", "int"), ("gain", "double"), ("pedestal", "double")], rows_count=3,
                         comment="Two assignments, one constant set; units on gain and pedestal", units={"gain": "MeV/count", "pedestal": "count"})
    first = b.add_assignment(shared, run_ranges[0], default, [["0", "1.25", "100.5"], ["1", "1.5", "101.0"], ["2", "0.75", "99.5"]], "first upload")
    b.session.flush()
    second = b.add_sharing_assignment(first.constant_set, run_ranges[1], default, "the same file for the next run range", "alice")

    # Numerically equal, textually different: the identity of a set is its bytes, so these are two sets with two hashes.
    numeric = b.add_table("numeric", schema6, [("value", "double")], comment="1.0 and 1.00: equal numbers, two constant sets")
    one = b.add_assignment(numeric, run_ranges[0], default, [["1.0"]], "written as 1.0")
    one_again = b.add_assignment(numeric, run_ranges[1], default, [["1.00"]], "written as 1.00", "bob")

    # One deprecated object of each kind, with all four deprecation columns set.
    retired_dir = b.add_directory("retired", schema6, "A deprecated directory")
    retired_table = b.add_table("retired_table", schema6, [("v", "double")], comment="A deprecated table")
    retired_assignment = b.add_assignment(retired_table, run_ranges[0], default, [["2.5"]], "data of a deprecated table")
    retired_variation = b.add_variation("retired", default, "A deprecated variation")
    b.session.flush()
    b.deprecate(retired_dir, "bob", "Moved to /schema6")
    b.deprecate(retired_table, "bob", "Replaced by /schema6/shared")
    b.deprecate(retired_variation, "alice", "Calibration pass abandoned")

    # Assignment log records as the provider writes them; the reused set is marked as shared data. The request is
    # assembled here because Assignment.request reads TypeTable.path, which only the provider fills in.
    for assignment, table, run_range, author, suffix in ((first, shared, run_ranges[0], "test_user", ""),
                                                         (second, shared, run_ranges[1], "alice", " (shared data)"),
                                                         (one, numeric, run_ranges[0], "test_user", ""),
                                                         (one_again, numeric, run_ranges[1], "bob", ""),
                                                         (retired_assignment, retired_table, run_ranges[0], "test_user", "")):
        request = "/schema6/{0}:{1}:default:{2}".format(table.name, run_range.min, assignment.created.strftime("%Y-%m-%d_%H-%M-%S"))
        b.add_log(author, "create", "assignments{0}|constantSets{1}".format(assignment.id, assignment.constant_set.id),
                  "Created assignment '{0}'{1}".format(request, suffix), assignment.comment)

    # Tags: one at the creation time of the newest assignment of the fixture, one in the past. snapshotTime is a UTC
    # instant while assignments.created has no zone: fixture_newest sits exactly at assignment 3618 only when the
    # reader takes created as UTC, so a test that resolves tags against this fixture pins its time zone to UTC.
    newest = max((first, second, one, one_again, retired_assignment), key=lambda each: each.created)
    b.add_tag("fixture_newest", default, newest.created, "At the creation time of the newest assignment")
    b.add_tag("fixture_past", default, at(24 * 60), "A moment inside the fixture's history: 2020-01-02 12:00", "alice")

    # One property of the instance (owner id 0) and one of a table.
    b.add_property("instance", 0, "experiment", "CCDB web GUI fixture")
    b.add_property("table", shared.id, "procedure", "Gains from the LED pulser runs", "alice")


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
