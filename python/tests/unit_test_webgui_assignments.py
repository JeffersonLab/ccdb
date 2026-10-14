"""Tests the assignment views: request string and id give the same page, JSON and text; errors; redirects"""
import json
import os
import tempfile
import unittest
from urllib.parse import quote

from ccdb.sql.sqlite_schema import create_sqlite_database
from ccdb.webgui import cerate_ccdb_flask_app
from ccdb.webgui.db import get_database

TABLE = "/test/test_vars/test_table"
AMBIGUOUS = TABLE + ":0:default"  # assignments 1 and 4 match; 4 is the newest


class AssignmentViewsTest(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        db_path = os.path.join(self.tmp_dir.name, "assignments_test.sqlite")
        create_sqlite_database(db_path)
        self.app = cerate_ccdb_flask_app("sqlite:///" + db_path)
        self.client = self.app.test_client()

    def tearDown(self):
        get_database(self.app).dispose()
        self.tmp_dir.cleanup()

    def get(self, url):
        return self.client.get(url)

    def test_request_without_timestamp_picks_the_newest(self):
        data = json.loads(self.get("/assignments/data.json?request=" + quote(AMBIGUOUS)).get_data(as_text=True))
        self.assertEqual(data["id"], 4)
        self.assertEqual(data["request"], TABLE + ":0:default:2012-10-30_23-48-42")
        self.assertEqual(data["columns"], [{"name": "x", "type": "double"}, {"name": "y", "type": "double"}, {"name": "z", "type": "double"}])
        self.assertEqual(data["rows"], [["2.2", "2.3", "2.4"], ["2.5", "2.6", "2.7"]])
        self.assertEqual((data["run_min"], data["run_max"], data["author"], data["variation"]), (0, 2147483647, "test_user", "default"))

    def test_both_address_forms_give_identical_responses(self):
        exact = TABLE + ":0:default:2012-10-30_23-48-42"
        for by_request, by_id in (("/show_request?request=" + quote(exact), "/assignments/4"),
                                  ("/assignments/data.json?request=" + quote(exact), "/assignments/4/data.json"),
                                  ("/assignments/data.txt?request=" + quote(exact), "/assignments/4/data.txt")):
            first, second = self.get(by_request), self.get(by_id)
            self.assertEqual(first.status_code, 200, by_request)
            self.assertEqual(first.get_data(), second.get_data(), by_id)
            self.assertEqual(first.content_type, second.content_type)

    def test_page_shows_the_exact_request(self):
        html = self.get("/show_request?request=" + quote(AMBIGUOUS)).get_data(as_text=True)
        self.assertIn(TABLE + ":0:default:2012-10-30_23-48-42", html)

    def test_text_dump_format(self):
        text = self.get("/assignments/4/data.txt").get_data(as_text=True)
        lines = text.split("\n")
        self.assertEqual(lines[0], "#request: " + TABLE + ":0:default:2012-10-30_23-48-42")
        self.assertEqual(lines[1], "#Test assignment for software tests 4")
        # each cell: two spaces, the value left-aligned in 10 characters, one space; one trailing space ends the row
        self.assertEqual(lines[2], "  2.2          2.3          2.4         ")
        self.assertEqual(lines[3], "  2.5          2.6          2.7         ")
        self.assertEqual(lines[4:], [""])

    def test_cache_headers(self):
        self.assertEqual(self.get("/assignments/4/data.json").headers["Cache-Control"], "public, max-age=86400")
        self.assertEqual(self.get("/assignments/data.json?request=" + quote(AMBIGUOUS)).headers["Cache-Control"], "no-cache")
        exact = TABLE + ":0:default:2012-10-30_23-48-42"
        self.assertEqual(self.get("/assignments/data.json?request=" + quote(exact)).headers["Cache-Control"], "public, max-age=86400")
        for not_pinned in (TABLE + ":0:default:notadate", TABLE + ":0:default:2099-01-01"):  # both resolve to the newest
            self.assertEqual(self.get("/assignments/data.json?request=" + quote(not_pinned)).headers["Cache-Control"], "no-cache", not_pinned)

    def test_errors(self):
        self.assertEqual(self.get("/assignments/999999").status_code, 404)
        self.assertEqual(self.get("/assignments/999999/data.json").status_code, 404)
        self.assertEqual(self.get("/assignments/data.txt?request=" + quote("/no/such/table:1")).status_code, 404)
        self.assertEqual(self.get("/assignments/data.txt?request=" + quote(TABLE + ":1:nosuchvar")).status_code, 404)
        self.assertEqual(self.get("/assignments/data.json").status_code, 400)
        self.assertEqual(self.get("/show_request?request=" + quote(TABLE + ":abc")).status_code, 400)
        self.assertEqual(self.get("/show_request?request=garbage").status_code, 400)

    def test_request_form_parts_redirect_to_the_request_string(self):
        response = self.get("/show_request?path=" + quote(TABLE) + "&run=0&variation=default&time=")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/show_request?request=" + quote(TABLE + ":0:default", safe="/:")), response.headers["Location"])
        with_time = self.get("/show_request?path=" + quote(TABLE) + "&run=5&variation=mc&time=2020-01-04")
        self.assertTrue(with_time.headers["Location"].endswith(quote(TABLE + ":5:mc:2020-01-04", safe="/:")), with_time.headers["Location"])
        with_clock = self.get("/show_request?path=" + quote(TABLE) + "&run=0&variation=default&time=2012-10-30_23-48-42")
        self.assertEqual(with_clock.status_code, 302)
        followed = self.get(with_clock.headers["Location"])
        self.assertEqual(followed.status_code, 200)
        self.assertIn(TABLE + ":0:default:2012-10-30_23-48-42", followed.get_data(as_text=True))

    def test_old_download_routes_redirect(self):
        for old in ("/dowload_request", "/download_request"):
            response = self.get(old + "?request=" + quote(AMBIGUOUS))
            self.assertEqual(response.status_code, 302, old)
            self.assertTrue(response.headers["Location"].endswith("/assignments/data.txt?request=" + quote(AMBIGUOUS, safe="/:")), response.headers["Location"])


if __name__ == "__main__":
    unittest.main()
