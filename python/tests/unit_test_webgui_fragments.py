"""Tests the live-search fragment responses of the table pages"""
import os
import tempfile
import unittest

from ccdb.sql.sqlite_schema import create_sqlite_database
from ccdb.webgui import cerate_ccdb_flask_app
from ccdb.webgui.db import get_database

VERSIONS = "/versions/test/test_vars/test_table"


class FragmentTest(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        db_path = os.path.join(self.tmp_dir.name, "fragments_test.sqlite")
        create_sqlite_database(db_path)
        self.app = cerate_ccdb_flask_app("sqlite:///" + db_path)
        self.client = self.app.test_client()

    def tearDown(self):
        get_database(self.app).dispose()
        self.tmp_dir.cleanup()

    def test_full_page_by_default(self):
        response = self.client.get(VERSIONS)
        html = response.get_data(as_text=True)
        self.assertIn("<html", html)
        self.assertIn('id="table-fragment"', html)
        self.assertIn('data-live-table="#table-fragment"', html)
        self.assertEqual(response.headers["Vary"], "X-Fragment, HX-Request")

    def test_fragment_on_request(self):
        for headers in ({"X-Fragment": "1"}, {"HX-Request": "true"}):
            response = self.client.get(VERSIONS + "?search=software", headers=headers)
            html = response.get_data(as_text=True)
            self.assertEqual(response.status_code, 200, headers)
            self.assertNotIn("<html", html)
            self.assertTrue(html.lstrip().startswith('<div id="table-fragment">'), headers)
            self.assertIn("data-total=", html)
            self.assertEqual(response.headers["Vary"], "X-Fragment, HX-Request")

    def test_open_ended_run_range_shows_infinity(self):
        html = self.client.get(VERSIONS, headers={"X-Fragment": "1"}).get_data(as_text=True)
        self.assertIn("∞", html)
        self.assertNotIn("2147483647", html)

    def test_long_variation_chain_collapses_in_place(self):
        import ccdb
        provider = ccdb.AlchemyProvider()
        provider.attach(*self._engine_and_session())
        provider.authentication.current_user_name = "test_user"
        provider.create_variation("deeper", "fourth level", "subtest")
        provider.disconnect()
        html = self.client.get("/vars", headers={"X-Fragment": "1"}).get_data(as_text=True)
        self.assertIn('chain">default › test › subtest', html)  # three levels stay inline, no <details>
        self.assertIn("default › <span class=\"chain-more\">…</span> › subtest › deeper", html)
        self.assertIn("default › test › subtest › deeper</span>", html)

    def _engine_and_session(self):
        from ccdb.webgui.db import get_database
        database = get_database(self.app)
        database.ensure_engine()
        return database.engine, database.sessions

    def test_sort_links_flip_the_order(self):
        html = self.client.get(VERSIONS + "?sort=created&order=desc").get_data(as_text=True)
        self.assertIn("sort=created&amp;order=asc", html)
        self.assertIn("sort=variation&amp;order=asc", html)


if __name__ == "__main__":
    unittest.main()
