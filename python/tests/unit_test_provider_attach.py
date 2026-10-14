"""Tests AlchemyProvider.attach(): sharing an engine and session created outside the provider"""
import os
import tempfile
import unittest

import sqlalchemy
from sqlalchemy.orm import Session, scoped_session, sessionmaker

import ccdb
from ccdb.errors import DatabaseStructureError
from ccdb.sql.sqlite_schema import create_sqlite_database


class ProviderAttachTest(unittest.TestCase):
    """Each test gets a fresh standard SQLite database, one engine and a session bound to it"""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp_dir.name, "attach_test.sqlite")
        create_sqlite_database(self.db_path)
        self.engine = sqlalchemy.create_engine("sqlite:///" + self.db_path)
        self.session = Session(bind=self.engine)
        self.provider = ccdb.AlchemyProvider()

    def tearDown(self):
        self.session.close()
        self.engine.dispose()
        self.tmp_dir.cleanup()

    def test_attach_uses_the_given_engine_and_session(self):
        self.provider.attach(self.engine, self.session)
        self.assertTrue(self.provider.is_connected)
        self.assertIs(self.provider.engine, self.engine)
        self.assertIs(self.provider.session, self.session)
        self.assertEqual(self.provider.connection_string, "sqlite:///" + self.db_path)
        self.assertEqual(self.provider.get_variation("default").name, "default")
        self.assertEqual(self.provider.get_type_table("/test/test_vars/test_table").name, "test_table")

    def test_attach_accepts_a_scoped_session(self):
        registry = scoped_session(sessionmaker(bind=self.engine))
        try:
            self.provider.attach(self.engine, registry)
            self.assertEqual(len(self.provider.get_variations()), 4)
        finally:
            registry.remove()

    def test_attach_rejects_a_non_engine(self):
        with self.assertRaises(TypeError) as raised:
            self.provider.attach("sqlite:///" + self.db_path, self.session)
        self.assertIn("'engine'", str(raised.exception))
        self.assertIn("str", str(raised.exception))
        self.assertFalse(self.provider.is_connected)

    def test_attach_rejects_a_non_session(self):
        with self.assertRaises(TypeError) as raised:
            self.provider.attach(self.engine, self.engine.connect())
        self.assertIn("'session'", str(raised.exception))
        self.assertFalse(self.provider.is_connected)

    def test_attach_rejects_a_session_bound_elsewhere(self):
        other_engine = sqlalchemy.create_engine("sqlite://")
        with self.assertRaises(ValueError) as raised:
            self.provider.attach(self.engine, Session(bind=other_engine))
        self.assertIn("bound to", str(raised.exception))
        self.assertFalse(self.provider.is_connected)

    def test_attach_rejects_an_unbound_session(self):
        with self.assertRaises(ValueError) as raised:
            self.provider.attach(self.engine, Session())
        self.assertIn("no bind", str(raised.exception))
        self.assertFalse(self.provider.is_connected)

    def test_attach_twice_needs_disconnect_in_between(self):
        self.provider.attach(self.engine, self.session)
        with self.assertRaises(RuntimeError) as raised:
            self.provider.attach(self.engine, self.session)
        self.assertIn("disconnect()", str(raised.exception))
        self.provider.disconnect()
        self.assertFalse(self.provider.is_connected)
        self.provider.attach(self.engine, self.session)
        self.assertTrue(self.provider.is_connected)

    def test_attach_checks_the_schema_version(self):
        empty_engine = sqlalchemy.create_engine("sqlite://")
        with self.assertRaises(DatabaseStructureError):
            self.provider.attach(empty_engine, Session(bind=empty_engine))
        self.assertFalse(self.provider.is_connected)  # a failed attach leaves the provider untouched
        self.provider.attach(empty_engine, Session(bind=empty_engine), check_version=False)
        self.assertTrue(self.provider.is_connected)

    def test_disconnect_keeps_a_scoped_session_usable(self):
        registry = scoped_session(sessionmaker(bind=self.engine))
        try:
            self.provider.attach(self.engine, registry)
            self.provider.disconnect()
            self.assertEqual(registry.query(ccdb.Variation).count(), 4)
        finally:
            registry.remove()


if __name__ == "__main__":
    unittest.main()
