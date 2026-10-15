"""Tests the variation comparison page: the chain segment, the affected tables, the run and time filters, the errors"""
import os
import re
import tempfile
import unittest

from ccdb.sql.sqlite_schema import create_sqlite_database
from ccdb.webgui import cerate_ccdb_flask_app
from ccdb.webgui.db import get_database

# The standard content: default(1) -> mc(2), default -> test(3) -> subtest(4).
# /test/test_vars/test_table has assignments in default (2), test (runs 500-3000, created 2012-08-30) and subtest;
# /test/test_vars/test_table2 has one in test (runs 0-inf, created 2012-09-30).
TABLE = "/test/test_vars/test_table"
TABLE2 = "/test/test_vars/test_table2"


def shown_tables(html):
    """table path -> {variation: count}, as the page's tree and badges show them"""
    result = {}
    for path, body in re.findall(r'<li data-path="([^"]+)" data-kind="table" data-id="\d+">(.*?)</li>', html, re.S):
        result[path] = {m.group(1): int(m.group(2)) for m in re.finditer(r'data-variation="([^"]+)" data-count="(\d+)"', body)}
    return result


class CompareVariationsTest(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        db_path = os.path.join(self.tmp_dir.name, "compare_test.sqlite")
        create_sqlite_database(db_path)
        self.app = cerate_ccdb_flask_app("sqlite:///" + db_path)
        self.client = self.app.test_client()

    def tearDown(self):
        get_database(self.app).dispose()
        self.tmp_dir.cleanup()

    def page(self, query):
        response = self.client.get("/vars/compare" + query)
        self.assertEqual(response.status_code, 200, query)
        return response.get_data(as_text=True)

    def test_direct_parent_by_default(self):
        html = self.page("?variation=subtest")
        self.assertEqual(shown_tables(html), {TABLE: {"subtest": 1}})
        self.assertIn('<option value="test" selected>test (parent)</option>', html)
        self.assertIn("<strong>subtest</strong>", html)
        self.assertIn('data-remember="no"', html)  # the comparison tree does not share the tables page's open state
        self.assertIn('href="/versions/test/test_vars/test_table?variation=subtest"', html)

    def test_segment_up_to_an_older_ancestor(self):
        html = self.page("?variation=subtest&parent=default")
        self.assertEqual(shown_tables(html), {TABLE: {"test": 1, "subtest": 1}, TABLE2: {"test": 1}})
        self.assertIn("<strong>test</strong> › <strong>subtest</strong>", html)
        self.assertIn("2 affected tables", html)

    def test_run_filter(self):
        html = self.page("?variation=test&run=100")  # the test assignment of test_table covers runs 500-3000 only
        self.assertEqual(shown_tables(html), {TABLE2: {"test": 1}})
        self.assertIn('href="/versions/test/test_vars/test_table2?variation=test&amp;run=100"', html)

    def test_time_filter(self):
        html = self.page("?variation=test&parent=default&time=2012-09-01")  # test_table2's assignment came on 2012-09-30
        self.assertEqual(shown_tables(html), {TABLE: {"test": 1}})
        self.assertIn("up to 2012-09-01", html)

    def test_empty_segment_and_root(self):
        html = self.page("?variation=mc")
        self.assertEqual(shown_tables(html), {})
        self.assertIn("No table has an assignment in mc", html)
        html = self.page("?variation=default")
        self.assertNotIn('data-kind="table"', html)
        self.assertIn("is the root variation", html)
        self.assertNotIn('id="tree"', html)

    def test_form_alone(self):
        html = self.page("")
        self.assertIn('<select class="form-select" style="max-width: 16rem" name="variation"', html)
        self.assertNotIn('id="tree"', html)

    def test_errors(self):
        for query, status in (("?variation=nosuch", 404), ("?variation=subtest&parent=mc", 400), ("?variation=subtest&parent=subtest", 400),
                              ("?variation=subtest&run=abc", 400), ("?variation=subtest&time=yesterday", 400)):
            self.assertEqual(self.client.get("/vars/compare" + query).status_code, status, query)

    def test_eye_links_in_the_variation_list(self):
        html = self.client.get("/vars").get_data(as_text=True)
        self.assertIn('href="/vars/compare?variation=subtest"', html)
        self.assertNotIn('href="/vars/compare?variation=default"', html)  # the root has no parent to compare with
        self.assertIn('href="/vars/compare"', html)
