"""Tests AlchemyProvider.connect() and disconnect(): one connection at a time, safe disconnect, disposes only the engine connect() created"""
import os
import tempfile
import unittest
from unittest import mock

import sqlalchemy
from sqlalchemy.orm import Session

import ccdb
from ccdb.errors import DatabaseStructureError
from ccdb.sql.sqlite_schema import create_sqlite_database


class ProviderDisconnectTest(unittest.TestCase):
    """Each test gets a fresh standard SQLite database and a provider that is not connected"""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp_dir.name, "disconnect_test.sqlite")
        create_sqlite_database(self.db_path)
        self.provider = ccdb.AlchemyProvider()

    def tearDown(self):
        self.provider.disconnect()
        self.tmp_dir.cleanup()

    def test_disconnect_without_a_connection_does_nothing(self):
        self.provider.disconnect()
        self.provider.disconnect()
        self.assertFalse(self.provider.is_connected)

    def test_failed_connect_keeps_its_error_and_disposes_its_engine(self):
        empty_path = os.path.join(self.tmp_dir.name, "empty.sqlite")
        engines = []
        real_create_engine = sqlalchemy.create_engine  # the patch below replaces it on the sqlalchemy module

        def create_engine(*args, **kwargs):
            engine = real_create_engine(*args, **kwargs)
            engine.dispose = mock.Mock(wraps=engine.dispose)
            engines.append(engine)
            return engine

        with mock.patch("ccdb.provider.sqlalchemy.create_engine", side_effect=create_engine):
            with self.assertRaises(DatabaseStructureError):
                self.provider.connect("sqlite:///" + empty_path)
        engines[0].dispose.assert_called_once()
        self.assertFalse(self.provider.is_connected)
        self.provider.disconnect()  # the usual cleanup after a failed connect must not raise

    def test_failing_cleanup_does_not_replace_the_connect_error(self):
        empty_path = os.path.join(self.tmp_dir.name, "empty.sqlite")
        real_create_engine = sqlalchemy.create_engine  # the patch below replaces it on the sqlalchemy module

        def create_engine(*args, **kwargs):
            engine = real_create_engine(*args, **kwargs)
            engine.dispose = mock.Mock(side_effect=RuntimeError("dispose failed"))
            return engine

        with mock.patch("ccdb.provider.sqlalchemy.create_engine", side_effect=create_engine), \
                mock.patch.object(Session, "close", side_effect=RuntimeError("close failed")), \
                self.assertLogs("ccdb.provider", level="WARNING") as logs:
            with self.assertRaises(DatabaseStructureError):
                self.provider.connect("sqlite:///" + empty_path)
        self.assertEqual(len(logs.records), 2)  # close failed, and dispose was still tried
        self.assertIn("close failed", logs.output[0])
        self.assertIn("dispose failed", logs.output[1])

    def test_disconnect_disposes_the_engine_connect_created(self):
        self.provider.connect("sqlite:///" + self.db_path)
        engine = self.provider.engine
        with mock.patch.object(engine, "dispose", wraps=engine.dispose) as dispose:
            self.provider.disconnect()
            self.provider.disconnect()  # a second call does not dispose again
        dispose.assert_called_once()
        self.assertFalse(self.provider.is_connected)

    def test_connect_on_a_connected_provider_raises(self):
        other_path = os.path.join(self.tmp_dir.name, "other.sqlite")
        create_sqlite_database(other_path)
        self.provider.connect("sqlite:///" + self.db_path)
        engine = self.provider.engine
        with mock.patch.object(engine, "dispose", wraps=engine.dispose) as dispose:
            with self.assertRaises(RuntimeError) as raised:
                self.provider.connect("sqlite:///" + other_path)
        self.assertIn("disconnect()", str(raised.exception))
        dispose.assert_not_called()  # the existing connection stays as it was
        self.assertTrue(self.provider.is_connected)
        self.assertIs(self.provider.engine, engine)
        self.assertEqual(self.provider.connection_string, "sqlite:///" + self.db_path)

    def test_connect_again_after_disconnect(self):
        other_path = os.path.join(self.tmp_dir.name, "other.sqlite")
        create_sqlite_database(other_path)
        self.provider.connect("sqlite:///" + self.db_path)
        self.provider.disconnect()
        self.provider.connect("sqlite:///" + other_path)
        self.assertTrue(self.provider.is_connected)
        self.assertEqual(self.provider.connection_string, "sqlite:///" + other_path)
        self.assertEqual(self.provider.get_variation("default").name, "default")

    def test_disconnect_leaves_an_attached_engine_open(self):
        engine = sqlalchemy.create_engine("sqlite:///" + self.db_path)
        session = Session(bind=engine)
        try:
            self.provider.attach(engine, session)
            with mock.patch.object(engine, "dispose", wraps=engine.dispose) as dispose:
                self.provider.disconnect()
            dispose.assert_not_called()
            with engine.connect() as connection:  # the caller can still use its engine
                self.assertEqual(connection.execute(sqlalchemy.text("SELECT count(*) FROM variations")).scalar(), 4)
        finally:
            session.close()
            engine.dispose()

    def test_attach_after_connect_does_not_dispose_the_attached_engine(self):
        self.provider.connect("sqlite:///" + self.db_path)
        self.provider.disconnect()
        engine = sqlalchemy.create_engine("sqlite:///" + self.db_path)
        try:
            self.provider.attach(engine, Session(bind=engine))
            with mock.patch.object(engine, "dispose", wraps=engine.dispose) as dispose:
                self.provider.disconnect()
            dispose.assert_not_called()
        finally:
            engine.dispose()


if __name__ == "__main__":
    unittest.main()
