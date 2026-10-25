"""Tests the `ccdb gui` command: it connects only through the web GUI engine, and fails before the server starts"""
import logging
import os
import tempfile
import unittest
from unittest import mock

import flask

from ccdb.cmd import CliManager
from ccdb.sql.sqlite_schema import create_sqlite_database
from ccdb.webgui.db import get_database


class CliGuiTest(unittest.TestCase):
    """Runs `ccdb gui` with Flask.run replaced by a mock, so no server starts"""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp_dir.name, "gui_test.sqlite")
        create_sqlite_database(self.db_path)
        self.cli = CliManager()
        self.cli.register_utilities()

    def tearDown(self):
        self.tmp_dir.cleanup()

    def run_gui(self, connection_string, *args):
        self.cli.context.connection_string = connection_string
        with mock.patch.object(flask.Flask, "run", autospec=True) as run:
            result = self.cli.process_command("gui", list(args))
        return result, run

    def test_server_starts_on_the_gui_engine_only(self):
        result, run = self.run_gui("sqlite:///" + self.db_path, "-p", "8765")
        run.assert_called_once()
        app = run.call_args.args[0]
        database = get_database(app)
        try:
            self.assertIsNotNone(database.engine)  # connected and schema-checked before the server started
            self.assertEqual(run.call_args.kwargs, {"port": "8765"})
            self.assertFalse(self.cli.provider.is_connected)  # no idle CLI connection beside the GUI
            self.assertNotIn("db", app.config)
            self.assertNotIn("cli_context", app.config)
        finally:
            database.dispose()

    def test_wrong_database_fails_before_the_server_starts(self):
        empty_path = os.path.join(self.tmp_dir.name, "empty.sqlite")
        with self.assertLogs("ccdb", level=logging.CRITICAL):
            result, run = self.run_gui("sqlite:///" + empty_path)
        self.assertIs(result, False)
        run.assert_not_called()

    def test_connect_error_hides_the_password(self):
        with self.assertLogs("ccdb", level=logging.CRITICAL) as logs:
            result, run = self.run_gui("mysql://bob:S3cret@127.0.0.1:1/ccdb")
        self.assertIs(result, False)
        run.assert_not_called()
        self.assertNotIn("S3cret", "\n".join(logs.output))
        self.assertIn("mysql://bob:***@127.0.0.1:1/ccdb", "\n".join(logs.output))


if __name__ == "__main__":
    unittest.main()
