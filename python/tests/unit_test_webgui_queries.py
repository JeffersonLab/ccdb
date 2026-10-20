"""Tests the web GUI query helpers: argument policy, paging, sorting, filters and the request string"""
import os
import tempfile
import unittest

import sqlalchemy
from sqlalchemy.orm import Session
from werkzeug.datastructures import MultiDict
from werkzeug.exceptions import BadRequest

import ccdb
from ccdb.sql.sqlite_schema import create_sqlite_database
from ccdb.webgui import queries


class ParsePageQueryTest(unittest.TestCase):
    SORTS = {"created": None, "id": None}

    def parse(self, **args):
        return queries.parse_page_query(MultiDict(args), self.SORTS, default_sort="created")

    def test_defaults(self):
        query = self.parse()
        self.assertEqual((query.page, query.per_page, query.sort, query.order, query.search), (1, 50, "created", "desc", ""))

    def test_values(self):
        query = self.parse(page="3", per_page="100", sort="id", order="asc", search=" bob ")
        self.assertEqual((query.page, query.per_page, query.sort, query.order, query.search), (3, 100, "id", "asc", "bob"))
        self.assertEqual(query.offset, 200)

    def test_per_page_snaps_to_the_nearest_allowed_size(self):
        self.assertEqual(self.parse(per_page="7").per_page, 25)
        self.assertEqual(self.parse(per_page="60").per_page, 50)
        self.assertEqual(self.parse(per_page="100000").per_page, 200)

    def test_bad_values_are_400(self):
        for args in (dict(page="0"), dict(page="x"), dict(per_page="0"), dict(sort="nope"), dict(order="sideways")):
            with self.assertRaises(BadRequest, msg=str(args)):
                self.parse(**args)

    def test_run_arg_is_bounded_by_the_run_sentinel(self):
        """A run wider than the runRanges columns is a 400; the driver would raise on it and answer 500."""
        self.assertEqual(queries.run_arg(MultiDict({"run": str(queries.INFINITE_RUN)}), "run"), queries.INFINITE_RUN)
        self.assertIsNone(queries.run_arg(MultiDict({}), "run"))
        for value in (str(queries.INFINITE_RUN + 1), "9" * 30, "-1"):
            with self.assertRaises(BadRequest, msg=value):
                queries.run_arg(MultiDict({"run": value}), "run")


class ListQueriesTest(unittest.TestCase):
    """Runs against the standard test database: table 1 has 4 assignments, 4 variations, 13 log records"""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        db_path = os.path.join(self.tmp_dir.name, "queries_test.sqlite")
        create_sqlite_database(db_path)
        self.engine = sqlalchemy.create_engine("sqlite:///" + db_path)
        self.session = Session(bind=self.engine)
        self.provider = ccdb.AlchemyProvider()
        self.provider.attach(self.engine, self.session)
        self.table = self.provider.get_type_table("/test/test_vars/test_table")

    def tearDown(self):
        self.session.close()
        self.engine.dispose()
        self.tmp_dir.cleanup()

    def query(self, sorts, **args):
        return queries.parse_page_query(MultiDict(args), sorts, default_sort="created")

    def test_assignments_page_matches_the_provider(self):
        page = queries.list_assignments(self.session, self.table, self.query(queries.ASSIGNMENT_SORTS))
        expected = self.provider.get_assignments(self.table.path)
        self.assertEqual(page.total, len(expected))
        self.assertEqual([row.request for row in page.items], [a.request for a in expected])
        self.assertEqual([row.id for row in page.items], [a.id for a in expected], "newest first, as the provider orders")
        self.assertEqual(page.items[0].author, expected[0].author.name)

    def test_paging_and_navigation(self):
        first = queries.list_assignments(self.session, self.table, self.query(queries.ASSIGNMENT_SORTS, per_page="25"))
        self.assertEqual((first.page, first.pages, first.first_row, first.last_row), (1, 1, 1, first.total))
        self.assertFalse(first.has_prev)
        self.assertFalse(first.has_next)
        beyond = queries.list_assignments(self.session, self.table, self.query(queries.ASSIGNMENT_SORTS, page="9"))
        self.assertEqual(beyond.page, beyond.pages, "a page past the end is clamped to the last page")
        self.assertTrue(beyond.items, "the clamped page shows rows instead of an empty table")
        self.assertFalse(beyond.has_next)
        huge = queries.list_assignments(self.session, self.table, self.query(queries.ASSIGNMENT_SORTS, page="9" * 30))
        self.assertEqual((huge.page, huge.items), (huge.pages, beyond.items), "a page number wider than the database integers is clamped too")

    def test_search_wildcards_match_literally(self):
        """A search term is a literal substring: `%` and `_` are escaped instead of reaching LIKE as wildcards.

        Unescaped, `%` matched every row, which on the production logs table means two full scans per request.
        The test data holds no percent sign, so a literal search for one matches nothing; it does hold the
        author `test_user`, so a literal underscore legitimately matches the rows that carry that name.
        """
        everything = queries.list_assignments(self.session, self.table, self.query(queries.ASSIGNMENT_SORTS))
        self.assertTrue(everything.items)
        for wildcard in ("%", "%%", "a%b"):
            found = queries.list_assignments(self.session, self.table, self.query(queries.ASSIGNMENT_SORTS, search=wildcard))
            self.assertEqual(found.total, 0, "search={0!r} matches no row: the data has no percent sign".format(wildcard))
        underscore = queries.list_assignments(self.session, self.table, self.query(queries.ASSIGNMENT_SORTS, search="_"))
        for row in underscore.items:
            self.assertIn("_", row.comment + row.author, "every matched row carries a literal underscore")
        self.assertEqual(queries.like_pattern("50%"), "%50\\%%")
        self.assertEqual(queries.like_pattern("a_b"), "%a\\_b%")
        self.assertEqual(queries.like_pattern("c\\d"), "%c\\\\d%")

    def test_sorting(self):
        ascending = queries.list_assignments(self.session, self.table, self.query(queries.ASSIGNMENT_SORTS, sort="id", order="asc"))
        ids = [row.id for row in ascending.items]
        self.assertEqual(ids, sorted(ids))

    def test_filters(self):
        default_only = queries.list_assignments(self.session, self.table, self.query(queries.ASSIGNMENT_SORTS), variation="default")
        self.assertTrue(default_only.items)
        self.assertTrue(all(row.variation == "default" for row in default_only.items))
        run = queries.list_assignments(self.session, self.table, self.query(queries.ASSIGNMENT_SORTS), run=100000)
        self.assertTrue(all(row.run_min <= 100000 <= row.run_max for row in run.items))
        none = queries.list_assignments(self.session, self.table, self.query(queries.ASSIGNMENT_SORTS), run_min=5000, run_max=5001)
        self.assertTrue(all(row.run_max >= 5000 and row.run_min <= 5001 for row in none.items))
        searched = queries.list_assignments(self.session, self.table, self.query(queries.ASSIGNMENT_SORTS, search="software tests 4"))
        self.assertEqual([row.comment for row in searched.items], ["Test assignment for software tests 4"])

    def test_logs(self):
        page = queries.list_logs(self.session, self.query(queries.LOG_SORTS))
        expected = self.provider.get_log_records(1000)
        self.assertEqual(page.total, len(expected))
        self.assertEqual([row.id for row in page.items], [r.id for r in expected])
        self.assertEqual(page.items[0].author, expected[0].author.name)
        by_author = queries.list_logs(self.session, self.query(queries.LOG_SORTS, search="test_user"))
        self.assertTrue(by_author.items)
        self.assertTrue(all(row.author == "test_user" for row in by_author.items))

    def test_variations_with_parent(self):
        page = queries.list_variations(self.session, self.query(queries.VARIATION_SORTS, sort="id", order="asc"))
        by_name = {row.name: row for row in page.items}
        self.assertEqual(by_name["default"].parent, "")
        self.assertEqual(by_name["test"].parent, "default")
        self.assertEqual(by_name["subtest"].parent, "test")
        self.assertEqual(page.total, len(self.provider.get_variations()))


if __name__ == "__main__":
    unittest.main()
