"""MySQL, MariaDB and SQLite resolve times alike, to the microsecond, deterministically (docs/concepts/time.md).

scripts/time/make_time_db.py writes the data of testdata/time/resolution.tsv into a database; every query of the file
must give its expected value, in the zone the file names, on SQLite and, with CCDB_TEST_MYSQL_CONNECTION, on that
server (mysql-tests.yml runs MySQL 8.3 and MariaDB 10.5). The stored times read back equal the file's UTC values on
every engine, and two builds store the same rows. The C++ library runs the same file in test_TimeResolution.cc.
"""
import contextlib
import importlib.util
import io
import os
import tempfile
import time
import unittest

from sqlalchemy import text
from sqlalchemy.exc import NoResultFound

import ccdb
from ccdb import AlchemyProvider, testing
from ccdb.errors import ObjectIsNotFoundInDbError


def _load_builder():
    path = os.path.join(ccdb.get_ccdb_home_path(), "scripts", "time", "make_time_db.py")
    spec = importlib.util.spec_from_file_location("ccdb_scripts_time_make_time_db", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


builder = _load_builder()
CASES = builder.read_cases()


def stored_times(provider):
    """(assignment created, tag snapshotTime) as 'YYYY-MM-DD HH:MM:SS.ffffff' text, in insertion order"""
    def as_text(value):
        return value if isinstance(value, str) else value.strftime("%Y-%m-%d %H:%M:%S.%f")
    created = [as_text(row[0]) for row in provider.session.execute(text(
        "SELECT a.created FROM assignments a JOIN constantSets c ON c.id = a.constantSetId "
        "JOIN typeTables t ON t.id = c.constantTypeId WHERE t.name = 'values' ORDER BY a.id"))]
    snapshots = [as_text(row[0]) for row in provider.session.execute(text("SELECT snapshotTime FROM tags ORDER BY id"))]
    return created, snapshots


@unittest.skipUnless(hasattr(time, "tzset"), "time.tzset is not available")
class TimeResolutionMixin(object):
    """The checks, run on the database at self.connection"""

    def resolve(self, provider, request):
        try:
            assignment = provider.get_assignment_by_request(request)
        except (NoResultFound, ObjectIsNotFoundInDbError):
            return None
        return int(assignment.constant_set.data_table[0][0])

    def test_queries(self):
        provider = AlchemyProvider()
        provider.connect(self.connection)
        self.addCleanup(provider.disconnect)
        self.addCleanup(testing.pin_time_zone("UTC"))
        for zone, request, expected in CASES["query"]:
            with self.subTest(zone=zone, request=request):
                testing.pin_time_zone(zone)
                self.assertEqual(self.resolve(provider, request), expected)

    def test_stored_times_are_the_utc_values(self):
        provider = AlchemyProvider()
        provider.connect(self.connection)
        self.addCleanup(provider.disconnect)
        created, snapshots = stored_times(provider)
        self.assertEqual(created, [row[2] for row in CASES["assignment"]])
        self.assertEqual(snapshots, [row[2] for row in CASES["tag"]])


class SqliteTimeResolutionTest(TimeResolutionMixin, unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        cls.connection = "sqlite:///" + os.path.join(cls.directory.name, "time.sqlite")
        restore = testing.pin_time_zone("America/New_York")     # the zone the data is written in does not matter
        try:
            builder.build(cls.connection)
        finally:
            restore()

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def test_two_builds_store_the_same_rows(self):
        other = "sqlite:///" + os.path.join(self.directory.name, "again.sqlite")
        restore = testing.pin_time_zone("Asia/Kolkata")
        try:
            builder.build(other)
        finally:
            restore()
        rows = []
        for connection in (self.connection, other):
            provider = AlchemyProvider()
            provider.connect(connection)
            rows.append(provider.session.execute(text(
                "SELECT a.id, a.created, a.variationId, c.vault FROM assignments a "
                "JOIN constantSets c ON c.id = a.constantSetId ORDER BY a.id")).fetchall())
            rows.append(provider.session.execute(text("SELECT name, snapshotTime, variationId FROM tags ORDER BY id")).fetchall())
            provider.disconnect()
        self.assertEqual(rows[0], rows[2])
        self.assertEqual(rows[1], rows[3])


class MysqlTimeResolutionTest(TimeResolutionMixin, unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.connection = os.environ.get(testing.ENV_TEST_MYSQL)
        if not cls.connection:
            raise unittest.SkipTest("{} is not set".format(testing.ENV_TEST_MYSQL))
        builder.build(cls.connection)

    @classmethod
    def tearDownClass(cls):
        with contextlib.redirect_stdout(io.StringIO()):
            testing.recreate_mysql_db(cls.connection)



if __name__ == '__main__':
    unittest.main()
