"""Tests the comparison of two assignments: the diff module (changed set, numeric difference, shape check) and the
compare page and its JSON view on the standard test database (the form, the canonical redirect, the views, the inline alerts)."""
import json
import os
import re
import tempfile
import unittest

from ccdb.sql.sqlite_schema import create_sqlite_database
from ccdb.webgui import cerate_ccdb_flask_app
from ccdb.webgui.db import get_database
from ccdb.webgui.diff import diff_tables, kept_rows, delta_text, numeric_delta

# The standard content: /test/test_vars/test_table (2 rows × 3 columns) has four assignments, two of them in default.
TABLE = "/test/test_vars/test_table"
TABLE2 = "/test/test_vars/test_table2"

COLUMNS = [{"name": "channel", "type": "int"}, {"name": "gain", "type": "double"}, {"name": "label", "type": "string"}]


class DiffTablesTest(unittest.TestCase):

    def test_equal_sides_have_no_change(self):
        rows = [["0", "1.5", "a"], ["1", "2.5", "b"]]
        diff = diff_tables(rows, [list(row) for row in rows], COLUMNS)
        self.assertEqual(diff.changed_cells, 0)
        self.assertEqual(diff.changed_rows, [])
        self.assertEqual(diff.changed_columns, [])
        self.assertEqual(diff.cells, 6)
        self.assertFalse(any(cell.changed for row in diff.rows for cell in row))

    def test_changed_cells_rows_and_columns(self):
        a = [["0", "1.5", "a"], ["1", "2.5", "b"], ["2", "3.5", "c"]]
        b = [["0", "1.5", "a"], ["1", "2.75", "b"], ["2", "3.5", "d"]]
        diff = diff_tables(a, b, COLUMNS)
        self.assertEqual(diff.changed_cells, 2)
        self.assertEqual(diff.changed_rows, [1, 2])
        self.assertEqual(diff.changed_columns, [1, 2])
        gain = diff.rows[1][1]
        self.assertTrue(gain.changed)
        self.assertEqual((gain.a, gain.b), ("2.5", "2.75"))
        self.assertAlmostEqual(gain.delta, 0.25)
        self.assertAlmostEqual(gain.relative, 0.1)
        label = diff.rows[2][2]
        self.assertTrue(label.changed)
        self.assertIsNone(label.delta)

    def test_strings_compare_exactly(self):
        # The stored strings are the contract: `1.0` and `1` are two values to the APIs and to the page.
        diff = diff_tables([["1", "1.0", "x"]], [["1", "1", "x"]], COLUMNS)
        self.assertEqual(diff.changed_cells, 1)
        self.assertEqual(diff.rows[0][1].delta, 0.0)

    def test_numeric_delta(self):
        self.assertEqual(numeric_delta("2", "2.5"), (0.5, 0.25))
        self.assertEqual(numeric_delta("0", "3"), (3.0, None))      # no relative change from zero
        self.assertEqual(numeric_delta("abc", "3"), (None, None))
        self.assertEqual(numeric_delta("nan", "3"), (None, None))
        self.assertEqual(numeric_delta("1", "inf"), (None, None))

    def test_delta_text(self):
        diff = diff_tables([["0", "2", "a"]], [["0", "2.5", "b"]], COLUMNS)
        self.assertEqual(delta_text(diff.rows[0][1]), "2 → 2.5  Δ +0.5 (+25 %)")
        self.assertEqual(delta_text(diff.rows[0][2]), "a → b")
        zero = diff_tables([["0", "0", "a"]], [["0", "1", "a"]], COLUMNS)
        self.assertEqual(delta_text(zero.rows[0][1]), "0 → 1  Δ +1")

    def test_kept_rows(self):
        a = [["0", "1", "a"], ["1", "2", "b"], ["2", "3", "c"]]
        b = [["0", "1", "a"], ["1", "9", "b"], ["2", "3", "c"]]
        diff = diff_tables(a, b, COLUMNS)
        self.assertEqual([row_i for row_i, _ in kept_rows(diff, changed_only=False)], [0, 1, 2])
        self.assertEqual([row_i for row_i, _ in kept_rows(diff, changed_only=True)], [1])

    def test_unequal_shapes_raise(self):
        with self.assertRaises(ValueError):
            diff_tables([["0", "1", "a"]], [["0", "1", "a"], ["1", "2", "b"]], COLUMNS)
        with self.assertRaises(ValueError):
            diff_tables([["0", "1"]], [["0", "1", "a"]], COLUMNS)


class ComparePageTest(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        db_path = os.path.join(self.tmp_dir.name, "diff_test.sqlite")
        create_sqlite_database(db_path)
        self.app = cerate_ccdb_flask_app("sqlite:///" + db_path)
        self.client = self.app.test_client()
        with self.app.app_context():
            db = get_database(self.app).provider()
            both = db.get_assignments(TABLE, 0, "default")   # newest first
            other = db.get_assignments(TABLE2)
            self.newest, self.older, self.other = both[0].id, both[1].id, other[0].id
            self.newest_request, self.older_request = both[0].request, both[1].request

    def tearDown(self):
        get_database(self.app).dispose()
        self.tmp_dir.cleanup()

    def get(self, url, status=200):
        response = self.client.get(url)
        self.assertEqual(response.status_code, status, url)
        return response.get_data(as_text=True)

    @staticmethod
    def summary(html):
        match = re.search(r'id="diff-summary" data-cells="(\d+)" data-changed-cells="(\d+)" data-changed-rows="(\d+)"', html)
        return tuple(int(n) for n in match.groups()) if match else None

    def test_form_alone_and_with_a_table(self):
        html = self.get("/compare")
        self.assertIn('id="compare-form"', html)
        self.assertIsNone(self.summary(html))
        html = self.get("/compare?table=" + TABLE)
        self.assertIn('value="{0}"'.format(TABLE), html)
        self.assertIn('<option value="default">', html)

    def test_form_parts_redirect_to_the_canonical_url(self):
        response = self.client.get("/compare?table={0}&a_variation=default&b_variation=test&b_run=600&view=columns".format(TABLE))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/compare?a={0}:0:default&b={0}:600:test&view=columns".format(TABLE))

    def test_pair_by_id_and_by_request_string(self):
        by_id = self.get("/compare?a={0}&b={1}".format(self.older, self.newest))
        self.assertIn('data-view="cells" data-lines="rows"', by_id)
        cells, changed_cells, changed_rows = self.summary(by_id)
        self.assertEqual(cells, 6)
        self.assertEqual(by_id.count('class="diff-changed" data-changed title='), changed_cells)  # one marked data cell per changed cell
        by_request = self.get("/compare?a={0}&b={1}".format(self.older_request, self.newest_request))
        self.assertEqual(self.summary(by_request), (cells, changed_cells, changed_rows))

    def test_same_assignment_has_no_change(self):
        html = self.get("/compare?a={0}&b={0}".format(self.newest))
        self.assertEqual(self.summary(html), (6, 0, 0))
        self.assertIn("No cell differs.", html)

    def test_views_layouts_and_changed_rows(self):
        pair = "/compare?a={0}&b={1}".format(self.older, self.newest)
        self.assertIn('data-view="columns" data-lines="rows"', self.get(pair + "&view=columns"))
        tables = self.get(pair + "&view=tables")
        self.assertIn('data-view="tables" data-lines="rows" data-side="b"', tables)
        self.assertIn('data-view="tables" data-lines="rows" data-side="a"', tables)
        self.assertIn('data-view="cells" data-lines="columns"', self.get(pair + "&layout=horizontal"))  # Horizontal: one line per column
        self.assertIn('data-view="cells" data-lines="rows"', self.get(pair + "&layout=vertical"))
        changed_rows = self.summary(self.get(pair))[2]
        kept = self.get(pair + "&changed=1")
        self.assertEqual(kept.count('<th scope="row" class="row-index">'), changed_rows)
        self.get(pair + "&view=sideways", 400)
        self.get(pair + "&layout=diagonal", 400)
        self.get(pair + "&changed=maybe", 400)
        self.get(pair + "&page=0", 400)

    def test_failing_sides_keep_the_form_with_an_alert(self):
        html = self.get("/compare?a=/no/such/table:0&b={0}".format(self.newest), 404)
        self.assertIn('data-side="a"', html)
        self.assertIn('id="compare-form"', html)
        html = self.get("/compare?a=garbage&b=/no/such/table:0", 400)  # malformed outranks missing
        self.assertIn('data-side="a"', html)
        self.assertIn('data-side="b"', html)
        self.get("/compare?a=99999999999999999999&b={0}".format(self.newest), 400)
        html = self.get("/compare?a={0}&b={1}".format(self.newest, self.other), 400)
        self.assertIn('data-side="table"', html)
        self.assertIn(TABLE2, html)
        self.get("/compare?table=/no/such/table", 404)

    def test_json_view(self):
        response = self.client.get("/compare/data.json?a={0}&b={1}".format(self.older, self.newest))
        self.assertEqual(response.status_code, 200)
        body = json.loads(response.get_data(as_text=True))
        self.assertEqual(body["table"], TABLE)
        self.assertEqual([c["name"] for c in body["columns"]], ["x", "y", "z"])
        self.assertEqual(len(body["rows"]), 2)
        self.assertEqual(body["a"]["request"], self.older_request)
        self.assertEqual(body["b"]["id"], self.newest)
        self.assertEqual(sum(cell["changed"] for row in body["rows"] for cell in row["cells"]), body["changed_cells"])
        by_request = self.client.get("/compare/data.json?a={0}&b={1}".format(self.older_request, self.newest_request))
        self.assertEqual(by_request.get_data(), response.get_data())  # both address forms: byte-identical
        self.assertEqual(self.client.get("/compare/data.json?a={0}".format(self.newest)).status_code, 400)
        self.assertEqual(self.client.get("/compare/data.json?a=/no/such:0&b={0}".format(self.newest)).status_code, 404)
        self.assertEqual(self.client.get("/compare/data.json?a={0}&b={1}".format(self.newest, self.other)).status_code, 400)

    def test_assignment_page_links(self):
        newest = self.get("/assignments/{0}".format(self.newest))
        self.assertIn("Compare with previous", newest)
        self.assertIn("/compare?a={0}&amp;b={1}".format(self.older_request, self.newest_request), newest)
        self.assertIn("/compare?a={0}&amp;table={1}".format(self.newest_request, TABLE), newest)
        older = self.get("/assignments/{0}".format(self.older))
        self.assertNotIn("Compare with previous", older)
        self.assertIn("/compare?table={0}".format(TABLE), self.get("/versions" + TABLE))


if __name__ == "__main__":
    unittest.main()
