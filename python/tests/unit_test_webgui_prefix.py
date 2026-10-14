"""Tests URL building under a reverse-proxy prefix (ProxyFix knob) and the author names in the info fragments"""
import os
import tempfile
import unittest

from ccdb.sql.sqlite_schema import create_sqlite_database
from ccdb.webgui import cerate_ccdb_flask_app
from ccdb.webgui.db import get_database

FORWARDED = {"X-Forwarded-Prefix": "/ccdb", "X-Forwarded-Host": "www.example.org", "X-Forwarded-Proto": "https"}


class PrefixAndAuthorsTest(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        db_path = os.path.join(self.tmp_dir.name, "prefix_test.sqlite")
        create_sqlite_database(db_path)
        self.connection_string = "sqlite:///" + db_path
        self.apps = []

    def tearDown(self):
        for app in self.apps:
            get_database(app).dispose()
        self.tmp_dir.cleanup()

    def make_app(self, **config):
        app = cerate_ccdb_flask_app(self.connection_string, test_config=config)
        self.apps.append(app)
        return app

    def test_links_follow_the_forwarded_prefix_when_enabled(self):
        html = self.make_app(PROXY_FIX=True).test_client().get("/", headers=FORWARDED).get_data(as_text=True)
        self.assertIn('href="/ccdb/versions/test/test_vars/test_table"', html)
        self.assertIn('data-url="/ccdb/get-table-info/1"', html)
        self.assertIn('data-url="/ccdb/get-dir-info/1"', html)
        self.assertNotIn('href="/versions/', html)

    def test_forwarded_headers_are_ignored_by_default(self):
        html = self.make_app().test_client().get("/", headers=FORWARDED).get_data(as_text=True)
        self.assertIn('href="/versions/test/test_vars/test_table"', html)
        self.assertNotIn('href="/ccdb/', html)  # the footer links github.com/JeffersonLab/ccdb/issues

    def test_redirect_keeps_the_prefix(self):
        response = self.make_app(PROXY_FIX=True).test_client().get("/download_request?request=/test/test_vars/test_table:0:default", headers=FORWARDED)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].startswith("/ccdb/assignments/data.txt?"), response.headers["Location"])

    def test_info_fragments_show_author_names(self):
        client = self.make_app().test_client()
        self.assertIn("<td>test_user</td>", client.get("/get-table-info/1").get_data(as_text=True))
        self.assertIn("<td>test_user</td>", client.get("/get-dir-info/1").get_data(as_text=True))

    def test_tree_has_no_absolute_fetch_urls(self):
        html = self.make_app().test_client().get("/").get_data(as_text=True)
        self.assertNotIn("fetch(`/get-", html)


if __name__ == "__main__":
    unittest.main()
