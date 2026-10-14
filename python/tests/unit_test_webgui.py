"""Tests the web GUI app wiring: connection configuration, one engine per process, one session per request"""
import os
import tempfile
import unittest

from sqlalchemy import event
from sqlalchemy.engine import Engine

from ccdb.sql.sqlite_schema import create_sqlite_database
from ccdb.webgui import cerate_ccdb_flask_app, create_ccdb_flask_app, connection_string_from_env
from ccdb.webgui.db import NO_CONNECTION_MESSAGE, get_database, normalize_dialect


class WebGuiAppTest(unittest.TestCase):
    """Each test gets a fresh standard SQLite database and a clean environment"""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        db_path = os.path.join(self.tmp_dir.name, "webgui_test.sqlite")
        create_sqlite_database(db_path)
        self.connection_string = "sqlite:///" + db_path
        self.saved_env = {name: os.environ.pop(name, None) for name in ("CCDB_CONNECTION", "SQL_CONNECTION_STRING")}
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

    def test_environment_order(self):
        os.environ["SQL_CONNECTION_STRING"] = "sqlite:///compose.sqlite"
        self.assertEqual(connection_string_from_env(), "sqlite:///compose.sqlite")
        os.environ["CCDB_CONNECTION"] = "sqlite:///cli.sqlite"
        self.assertEqual(connection_string_from_env(), "sqlite:///cli.sqlite")
        self.assertEqual(self.make_app().config["SQL_CONNECTION_STRING"], "sqlite:///cli.sqlite")

    def test_no_connection_fails_at_first_request_with_the_message(self):
        app = self.make_app()  # nothing in the environment
        with self.assertLogs("ccdb.webgui", level="ERROR") as logs:  # app.logger is named after the import name
            response = app.test_client().get("/doc")
        self.assertEqual(response.status_code, 500)
        self.assertIn(NO_CONNECTION_MESSAGE, "\n".join(logs.output))

    def test_config_set_after_creation_as_the_cli_does(self):
        app = self.make_app()
        app.config["SQL_CONNECTION_STRING"] = self.connection_string  # the `ccdb gui` command does this
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

    def test_mysql_uses_pymysql(self):
        self.assertEqual(normalize_dialect("mysql://u@h/d"), "mysql+pymysql://u@h/d")
        self.assertEqual(normalize_dialect("mysql+pymysql://u@h/d"), "mysql+pymysql://u@h/d")
        self.assertEqual(normalize_dialect("sqlite:///x.sqlite"), "sqlite:///x.sqlite")

    def test_spelled_right_factory_name(self):
        self.assertIs(create_ccdb_flask_app, cerate_ccdb_flask_app)


if __name__ == "__main__":
    unittest.main()
