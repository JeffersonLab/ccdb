"""Run bundles (ccdb.snapshot.run_bundle): a bundle answers like its source for its run, variation and time or tag.

The source is the test database of `ccdb db init`. A bundle opened by the Python SQLite provider must return the
same constants as the source for every table, its shared constant sets once, and the bundle of a tag must answer
requests with @tag. The shallow copy behind it is tested in scripts/shallow_copy.
"""
import datetime
import os
import sqlite3
import tempfile
import unittest

from ccdb import AlchemyProvider, snapshot, testing
from ccdb.sql.sqlite_schema import create_sqlite_database

RUN = 1000


def setUpModule():
    # the data holds literal UTC times
    global _restore_time_zone
    _restore_time_zone = testing.pin_time_zone("UTC")


def tearDownModule():
    _restore_time_zone()


class RunBundleTest(unittest.TestCase):

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        path = os.path.join(self.directory.name, "source.sqlite")
        create_sqlite_database(path)
        self.source_url = "sqlite:///" + path
        self.cache = os.path.join(self.directory.name, "cache")
        self.source = AlchemyProvider()
        self.source.connect(self.source_url)
        self.addCleanup(self.source.disconnect)
        self.source.authentication.current_user_name = "test_user"

    def open(self, path):
        provider = AlchemyProvider()
        provider.connect("sqlite:///" + path)
        self.addCleanup(provider.disconnect)
        return provider

    def vault_or_none(self, provider, request):
        try:
            return provider.get_assignment_by_request(request).constant_set.vault
        except Exception:
            return None

    def test_bundle_answers_like_the_source(self):
        now_utc = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        for variation in ("default", "subtest"):
            with self.subTest(variation=variation):
                path = snapshot.run_bundle(self.source_url, self.cache, RUN, variation, now_utc)
                bundle = self.open(path)
                self.source.get_root_directory()
                compared = 0
                for table in self.source.search_type_tables("*"):
                    request = "{0}:{1}:{2}".format(table.path, RUN, variation)
                    expected = self.vault_or_none(self.source, request)
                    self.assertEqual(self.vault_or_none(bundle, request), expected, request)
                    compared += expected is not None
                self.assertGreater(compared, 0)
                # another run is not in the bundle
                self.assertIsNone(self.vault_or_none(bundle, "/test/test_vars/test_table:{0}:{1}".format(RUN + 5000, variation)))

    def test_bundle_holds_each_set_once(self):
        now_utc = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        path = snapshot.run_bundle(self.source_url, self.cache, RUN, "default", now_utc)
        with sqlite3.connect(path) as connection:
            sets = connection.execute("SELECT COUNT(*) FROM constantSets").fetchone()[0]
            used = connection.execute("SELECT COUNT(DISTINCT constantSetId) FROM assignments").fetchone()[0]
        self.assertEqual(sets, used)

    def test_a_time_limits_the_bundle(self):
        before_everything = datetime.datetime(2010, 1, 1)
        path = snapshot.run_bundle(self.source_url, self.cache, RUN, "default", before_everything)
        with sqlite3.connect(path) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM assignments").fetchone()[0], 0)

    def test_bundle_of_a_tag_answers_with_the_tag(self):
        self.source.create_tag("bundle_test", "default", datetime.datetime(2012, 9, 1), "bundle test")
        path = snapshot.run_bundle(self.source_url, self.cache, RUN, tag="bundle_test")
        bundle = self.open(path)
        request = "/test/test_vars/test_table:{0}@bundle_test".format(RUN)
        self.assertEqual(self.vault_or_none(bundle, request), self.vault_or_none(self.source, request))
        self.assertIsNotNone(self.vault_or_none(bundle, request))

    def test_the_file_is_made_once(self):
        moment = datetime.datetime(2013, 1, 1)
        first = snapshot.run_bundle(self.source_url, self.cache, RUN, "default", moment)
        written = os.path.getmtime(first)
        self.assertEqual(snapshot.run_bundle(self.source_url, self.cache, RUN, "default", moment), first)
        self.assertEqual(os.path.getmtime(first), written)
        self.assertEqual([name for name in os.listdir(self.cache) if ".part" in name], [])

    def test_a_bundle_needs_a_time_or_a_tag(self):
        with self.assertRaises(ValueError):
            snapshot.run_bundle(self.source_url, self.cache, RUN, "default")


if __name__ == '__main__':
    unittest.main()
