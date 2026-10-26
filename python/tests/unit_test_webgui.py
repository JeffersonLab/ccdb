"""Tests the web GUI app wiring: connection configuration, one engine per process, one session per request"""
import os
import re
import tempfile
import unittest

from sqlalchemy import event
from sqlalchemy.engine import Engine

from ccdb.sql.sqlite_schema import create_sqlite_database
from ccdb.webgui import cerate_ccdb_flask_app, create_ccdb_flask_app, connection_string_from_env
from ccdb.webgui.db import NO_CONNECTION_MESSAGE, get_database, normalize_dialect
from ccdb.webgui.views import natural_key


class WebGuiAppTest(unittest.TestCase):
    """Each test gets a fresh standard SQLite database and a clean environment"""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        db_path = os.path.join(self.tmp_dir.name, "webgui_test.sqlite")
        create_sqlite_database(db_path)
        self.connection_string = "sqlite:///" + db_path
        self.saved_env = {name: os.environ.pop(name, None) for name in ("CCDB_CONNECTION",)}
        self.apps = []

    def tearDown(self):
        for app in self.apps:
            get_database(app).dispose()
        for name, value in self.saved_env.items():
            if value is not None:
                os.environ[name] = value
        self.tmp_dir.cleanup()

    def make_app(self, *args, **kwargs):
        app = cerate_ccdb_flask_app(*args, **kwargs)
        self.apps.append(app)
        return app

    def test_connection_string_argument(self):
        app = self.make_app(self.connection_string)
        self.assertEqual(app.test_client().get("/doc").status_code, 200)
        self.assertEqual(app.test_client().get("/vars").status_code, 200)

    def test_environment_variable(self):
        self.assertEqual(connection_string_from_env(), "")
        os.environ["CCDB_CONNECTION"] = "sqlite:///cli.sqlite"
        self.assertEqual(connection_string_from_env(), "sqlite:///cli.sqlite")
        self.assertEqual(self.make_app().config["CCDB_CONNECTION"], "sqlite:///cli.sqlite")

    def test_no_connection_fails_at_first_request_with_the_message(self):
        app = self.make_app()  # nothing in the environment
        with self.assertLogs("ccdb.webgui", level="ERROR") as logs:  # app.logger is named after the import name
            response = app.test_client().get("/doc")
        self.assertEqual(response.status_code, 500)
        self.assertIn(NO_CONNECTION_MESSAGE, "\n".join(logs.output))

    def test_info_boxes_show_the_assignment_activity(self):
        """The table box counts its assignments and names the newest; the directory box does the same for the tables under it"""
        client = self.make_app(self.connection_string).test_client()
        table_box = client.get("/get-table-info/1").get_data(as_text=True)  # /test/test_vars/test_table: 4 assignments in the standard content
        self.assertIn("<th scope=\"row\">Assignments</th>", table_box)
        self.assertIn("<td>4</td>", table_box)
        self.assertRegex(table_box, r"Last assignment</th>\s*<td>2012-10-30 23:48:43 by test_user</td>")
        self.assertNotIn("Modified", table_box)
        directory_box = client.get("/get-dir-info/1").get_data(as_text=True)  # /test holds test_vars with 2 tables
        self.assertRegex(directory_box, r"Tables</th>\s*<td>2</td>")
        self.assertRegex(directory_box, r"Last assignment</th>\s*<td>\d{4}-\d\d-\d\d \d\d:\d\d:\d\d by \w+</td>")
        self.assertNotIn("Modified", directory_box)
        empty_box = client.get("/get-dir-info/2").get_data(as_text=True)  # /test/subtest has no tables
        self.assertRegex(empty_box, r"Tables</th>\s*<td>0</td>")
        self.assertRegex(empty_box, r"Last assignment</th>\s*<td>none</td>")

    def test_tree_nodes_carry_ids_in_name_order(self):
        """Every node has data-id for Sort by ID; the page arrives sorted: directories first, then tables, each by name"""
        html = self.make_app(self.connection_string).test_client().get("/tree").get_data(as_text=True)
        nodes = re.findall(r'<li data-path="([^"]+)" data-kind="(dir|table)" data-id="(\d+)">', html)
        self.assertGreaterEqual(len(nodes), 4)
        self.assertEqual(len(nodes), html.count("<li data-path="))  # no node without an id
        siblings = {}
        for path, kind, _ in nodes:
            parent, _, name = path.rpartition("/")
            siblings.setdefault(parent, []).append((kind != "dir", natural_key(name)))
        for parent, keys in siblings.items():
            self.assertEqual(keys, sorted(keys), parent)
        for label in ("Expand<", "Collapse<", "Sort A…Z<", "Sort by ID<"):
            self.assertIn(label, html)
        self.assertNotIn("Expand all", html)

    def test_log_record_page(self):
        """every row of the logs list links to its record; the record page shows the full comment and the affected objects"""
        client = self.make_app(self.connection_string).test_client()
        html = client.get("/logs").get_data(as_text=True)
        self.assertRegex(html, r'<tr data-href="/logs/\d+">\s*<td class="text-nowrap"><a class="link-body-emphasis" href="/logs/\d+"')
        record = client.get("/logs/1")
        self.assertEqual(record.status_code, 200)
        page = record.get_data(as_text=True)
        self.assertIn('id="log-meta"', page)
        self.assertRegex(page, r"<th scope=\"row\">Affected</th><td class=\"text-break\">\s*user 1\s*</td>")  # the oldest records write `users_1`; users have no page
        directory = client.get("/logs/2").get_data(as_text=True)  # names directory 5, which the standard content does not have: text, no link
        self.assertRegex(directory, r'Affected</th><td class="text-break">\s*directory 5\s*</td>')
        self.assertEqual(client.get("/logs/999999").status_code, 404)

    def test_versions_page_rolls_down_the_info_block(self):
        """The versions page carries the table's info rows in a collapsed block; the live-search fragment does not"""
        client = self.make_app(self.connection_string).test_client()
        html = client.get("/versions/test/test_vars/test_table").get_data(as_text=True)
        self.assertIn('data-bs-target="#table-info"', html)
        self.assertIn("Show info", html)
        self.assertRegex(html, r'id="table-info">[\s\S]*?Assignments</th><td>4</td>')
        self.assertIn('id="versions-table"', html)
        fragment = client.get("/versions/test/test_vars/test_table", headers={"X-Fragment": "1"}).get_data(as_text=True)
        self.assertNotIn("table-info", fragment)
        self.assertIn('id="versions-table"', fragment)

    def test_natural_key(self):
        names = ["Layer10", "layer2", "layer1", "a", "B", "x1y", "x1", "1start", "z"]
        self.assertEqual(sorted(names, key=natural_key), ["1start", "a", "B", "layer1", "layer2", "Layer10", "x1", "x1y", "z"])

    def test_config_set_after_creation_as_the_cli_does(self):
        app = self.make_app()
        app.config["CCDB_CONNECTION"] = self.connection_string  # the `ccdb gui` command does this
        self.assertEqual(app.test_client().get("/vars").status_code, 200)

    def test_one_engine_for_all_requests(self):
        app = self.make_app(self.connection_string)
        client = app.test_client()
        client.get("/doc")
        engine = get_database(app).engine
        self.assertIsNotNone(engine)
        client.get("/vars")
        client.get("/logs")
        self.assertIs(get_database(app).engine, engine)

    def test_schema_check_runs_once(self):
        app = self.make_app(self.connection_string)
        counted = []

        def count(*args):
            counted.append(1)

        event.listen(Engine, "before_cursor_execute", count)
        try:
            client = app.test_client()
            client.get("/doc")
            first = len(counted)
            client.get("/doc")
            self.assertEqual(first, 1, "the first request runs the schema check and nothing else")
            self.assertEqual(len(counted), 1, "a view that needs no data runs no query")
        finally:
            event.remove(Engine, "before_cursor_execute", count)

    def test_session_is_released_after_the_request(self):
        app = self.make_app(self.connection_string)
        app.test_client().get("/vars")
        self.assertFalse(get_database(app).sessions.registry.has())

    def test_wrong_database_is_retried_not_cached(self):
        empty = os.path.join(self.tmp_dir.name, "empty.sqlite")
        app = self.make_app("sqlite:///" + empty)
        self.assertEqual(app.test_client().get("/vars").status_code, 500)
        self.assertIsNone(get_database(app).engine)
        create_sqlite_database(empty)
        self.assertEqual(app.test_client().get("/vars").status_code, 200)

    def test_health(self):
        import json
        app = self.make_app(self.connection_string)
        response = app.test_client().get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        body = json.loads(response.get_data(as_text=True))
        self.assertEqual((body["status"], body["database"]), ("ok", "ok"))
        self.assertIn("version", body)

    def test_health_reports_a_dead_database_as_503_and_recovers(self):
        import json
        missing = os.path.join(self.tmp_dir.name, "not_yet.sqlite")
        app = self.make_app("sqlite:///" + missing)
        response = app.test_client().get("/health")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(json.loads(response.get_data(as_text=True))["status"], "error")
        create_sqlite_database(missing)
        self.assertEqual(app.test_client().get("/health").status_code, 200)

    def test_url_control_arguments_are_not_taken_from_the_query_string(self):
        """url_for() reads `_external`, `_scheme`, `_anchor` and `_method` as control arguments. A page must
        ignore them in its own query string: `?_method=POST` used to fail the link build and answer 500."""
        client = self.make_app(self.connection_string).test_client()
        for query in ("?_method=POST", "?_external=1", "?_scheme=javascript&_external=1", "?_anchor=x"):
            response = client.get("/vars" + query)
            self.assertEqual(response.status_code, 200, query)
            body = response.get_data(as_text=True)
            self.assertNotIn("javascript:", body.lower(), query)
            self.assertIn('href="/vars?sort=', body, "links stay relative to this app: " + query)

    def test_out_of_range_numbers_are_400_not_500(self):
        """Every number a URL carries is bounded before it reaches the driver."""
        client = self.make_app(self.connection_string).test_client()
        cases = ["/logs?page=" + "9" * 30,
                 "/versions/test/test_vars/test_table?run=" + "9" * 30,
                 "/versions/test/test_vars/test_table?run_min=-1",
                 "/show_request?request=/test/test_vars/test_table:" + "9" * 30 + ":default"]
        for url in cases:
            self.assertLess(client.get(url).status_code, 500, url)

    def test_a_page_past_the_end_renders_rows(self):
        """A stale or hand-edited `page` lands on the last page and shows its rows, instead of an empty table.

        The standard test content holds 13 log records, so the last page is the only one and the page
        navigation is not rendered; unit_test_webgui_queries covers the clamp on a multi-page table.
        """
        client = self.make_app(self.connection_string).test_client()
        body = client.get("/logs?page=9999&per_page=25").get_data(as_text=True)
        self.assertIn('data-pages="1"', body)
        self.assertIn("Created user", body, "the clamped page carries real rows")

    def test_health_error_does_not_name_the_database(self):
        """The route is unauthenticated: a failure answers a fixed string, not the driver's message, which
        carries the host and the user it connected as."""
        app = self.make_app("sqlite:////nonexistent/directory/ccdb.sqlite")
        response = app.test_client().get("/health")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.get_json()["database"], "unavailable")
        self.assertNotIn("nonexistent", response.get_data(as_text=True))

    def test_show_request_rejects_a_post(self):
        """No view reads a request body; the form submits with GET."""
        client = self.make_app(self.connection_string).test_client()
        self.assertEqual(client.post("/show_request").status_code, 405)

    def test_mysql_uses_pymysql(self):
        self.assertEqual(normalize_dialect("mysql://u@h/d"), "mysql+pymysql://u@h/d")
        self.assertEqual(normalize_dialect("mysql+pymysql://u@h/d"), "mysql+pymysql://u@h/d")
        self.assertEqual(normalize_dialect("sqlite:///x.sqlite"), "sqlite:///x.sqlite")

    def test_spelled_right_factory_name(self):
        self.assertIs(create_ccdb_flask_app, cerate_ccdb_flask_app)


if __name__ == "__main__":
    unittest.main()
