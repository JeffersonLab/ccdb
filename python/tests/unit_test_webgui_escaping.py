"""Tests that database text reaches the pages escaped: names, comments and the autocomplete list"""
import os
import tempfile
import unittest
from urllib.parse import quote

import ccdb
from ccdb.sql.sqlite_schema import create_sqlite_database
from ccdb.webgui import cerate_ccdb_flask_app
from ccdb.webgui.db import get_database

HOSTILE = 'x"y\'z&<script>alert(1)<b>'
COMMENT = 'line one <script>alert("x")</script>\nline two & more'


class EscapingTest(unittest.TestCase):
    """A standard database plus one table with a hostile name and a hostile comment"""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        db_path = os.path.join(self.tmp_dir.name, "escaping_test.sqlite")
        create_sqlite_database(db_path)
        provider = ccdb.AlchemyProvider()
        provider.connect("sqlite:///" + db_path)
        provider.authentication.current_user_name = "test_user"
        provider.create_type_table(HOSTILE, "/test", 1, [("a", "string")], COMMENT)
        provider.create_assignment([["<b>cell</b>"]], "/test/" + HOSTILE, 0, 2147483647, "default", COMMENT)
        provider.disconnect()
        provider.engine.dispose()
        self.app = cerate_ccdb_flask_app("sqlite:///" + db_path)
        self.client = self.app.test_client()

    def tearDown(self):
        get_database(self.app).dispose()
        self.tmp_dir.cleanup()

    def test_tree_escapes_names_and_keeps_every_table(self):
        html = self.client.get("/").get_data(as_text=True)
        self.assertNotIn("<script>alert(1)", html)
        self.assertIn("&lt;script&gt;alert(1)&lt;b&gt;", html)
        self.assertIn('data="/test/x&#34;y&#39;z&amp;&lt;script&gt;alert(1)&lt;b&gt;"', html)
        self.assertIn("test_table2", html, "the tables after the hostile one are still there")

    def test_autocomplete_list_is_json_safe(self):
        html = self.client.get("/test_request").get_data(as_text=True)
        self.assertNotIn("<script>alert(1)", html)
        self.assertIn("\\u003cscript\\u003ealert(1)", html)

    def test_comment_and_cells_are_escaped_on_the_assignment_page(self):
        html = self.client.get("/show_request?request=" + quote("/test/" + HOSTILE + ":0:default")).get_data(as_text=True)
        self.assertNotIn('<script>alert("x")</script>', html)
        self.assertIn("&lt;script&gt;alert(&#34;x&#34;)&lt;/script&gt;<br>line two &amp; more", html)
        self.assertIn("&lt;b&gt;cell&lt;/b&gt;", html)

    def test_text_dump_is_plain_text(self):
        response = self.client.get("/assignments/data.txt?request=" + quote("/test/" + HOSTILE + ":0:default"))
        self.assertEqual(response.content_type, "text/plain; charset=utf-8")
        self.assertIn('#line one <script>alert("x")</script>\n#line two & more\n', response.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
