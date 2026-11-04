"""`ccdb export tag @NAME -o DIR` (ccdb.tag_export): the file answers every request of the tag as the source does, the
hash file matches, and the DataCite record validates against the DataCite 4.5 schema (scripts/docs/datacite).

Runs on the SQLite test database that ccdb.testing recreates (CCDB_TEST_SQLITE_CONNECTION).
"""
import datetime
import hashlib
import json
import logging
import os
import sys
import tempfile
import unittest
from io import StringIO

import ccdb.cmd.themes
from ccdb import testing as helper
from ccdb.cmd.cli_manager import CliManager, CCDB_EXCEPTIONS_THROW
from ccdb.provider import AlchemyProvider
from ccdb.tag_export import datacite_record, export_tag

SCHEMA = os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "docs", "datacite", "datacite-v4.5.json")
TABLE = "/test/test_vars/test_table"
TABLE2 = "/test/test_vars/test_table2"
REQUESTS = [TABLE + ":100", TABLE + ":600", TABLE + ":2500", TABLE2 + ":100", TABLE2 + ":1500"]


def validate(record):
    import jsonschema
    with open(SCHEMA, encoding="utf-8") as file:
        schema = json.load(file)
    jsonschema.Draft201909Validator(schema, format_checker=jsonschema.FormatChecker()).validate(record)


class ExportTagTest(unittest.TestCase):

    def setUp(self):
        helper.recreate_test_sqlite_db()
        self.source = helper.sqlite_test_connection_str
        self.provider = AlchemyProvider()
        self.provider.connect(self.source)
        self.provider.authentication.current_user_name = "test_user"
        db = self.provider
        db.set_property("instance", 0, "experiment", "GlueX")
        db.set_property("instance", 0, "license", "CC-BY-4.0")
        db.set_property("instance", 0, "url", "https://halldweb.jlab.org/ccdb")
        db.set_property("instance", 0, "contact", "Hall D software <halld-software@example.org>")
        db.set_property("table", db.get_type_table(TABLE).id, "contact", "calib@example.org")
        tag = db.create_tag("pass1", "test", comment="Pass 1")
        for name, value in (("description", "Pass 1 of the test run"), ("software", "halld_recon 6.1.0"),
                            ("container", "docker://example/recon:1"), ("rucio_did", "gluex:pass1")):
            db.set_property("tag", tag.id, name, value)
        # added after the tag: the export must not hold it
        db.create_assignment([["9", "9", "9"], ["9", "9", "9"]], TABLE, 0, 5000, "test", "after the tag")
        self.directory = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.provider.disconnect()
        self.directory.cleanup()
        helper.clean_test_sqlite_db()

    def test_the_file_answers_as_the_source(self):
        report = export_tag(self.source, "pass1", self.directory.name)
        exported = AlchemyProvider()
        exported.connect("sqlite:///" + report["paths"]["sqlite"])
        try:
            for request in REQUESTS:
                with self.subTest(request=request):
                    expected = self.provider.get_assignment_by_request(request + "@pass1")
                    got = exported.get_assignment_by_request(request + "@pass1")
                    self.assertEqual(got.id, expected.id)
                    self.assertEqual(got.constant_set.vault, expected.constant_set.vault)
                    self.assertEqual(got.constant_set.sha256, expected.constant_set.sha256)
            tag = exported.get_tag("pass1")
            self.assertEqual(exported.get_property("tag", tag.id, "software").value, "halld_recon 6.1.0")
            self.assertEqual(exported.get_property("instance", 0, "license").value, "CC-BY-4.0")
            table = exported.get_type_table(TABLE)
            self.assertEqual(exported.get_property("table", table.id, "contact").value, "calib@example.org")
            self.assertNotIn("after the tag", [each.comment for each in exported.get_assignments(table)])
        finally:
            exported.disconnect()

    def test_hash_file_and_datacite_record(self):
        report = export_tag(self.source, "pass1", self.directory.name, now_utc=datetime.datetime(2026, 11, 3, 18, 0))
        with open(report["paths"]["sqlite"], "rb") as file:
            sha256 = hashlib.sha256(file.read()).hexdigest()
        with open(report["paths"]["sha256"], encoding="utf-8") as file:
            self.assertEqual(file.read(), "{0}  pass1.sqlite\n".format(sha256))
        with open(report["paths"]["datacite"], encoding="utf-8") as file:
            record = json.load(file)
        validate(record)
        self.assertEqual(record["titles"][0]["title"], "GlueX calibration constants, tag pass1")
        self.assertEqual(record["creators"][0]["name"], "GlueX Collaboration")
        self.assertEqual(record["rightsList"], [{"rights": "CC-BY-4.0"}])
        self.assertEqual(record["contributors"], [{"name": "Hall D software <halld-software@example.org>",
                                                   "contributorType": "ContactPerson"}])
        self.assertEqual(record["alternateIdentifiers"][0], {"alternateIdentifier": sha256, "alternateIdentifierType": "SHA-256"})
        self.assertEqual(record["publicationYear"], "2026")
        self.assertIn("Software: halld_recon 6.1.0", record["descriptions"][1]["description"])
        self.assertEqual(record["relatedIdentifiers"], [])

    def test_a_previous_doi_is_named(self):
        record = datacite_record("pass1", "", datetime.datetime(2026, 1, 1), {}, {"doi": "https://doi.org/10.5281/zenodo.1234567"},
                                 "0" * 64, 100, datetime.datetime(2026, 11, 3))
        validate(record)
        self.assertEqual(record["relatedIdentifiers"], [{"relatedIdentifier": "10.5281/zenodo.1234567",
                                                         "relatedIdentifierType": "DOI", "relationType": "IsNewVersionOf"}])
        self.assertEqual(record["creators"][0]["name"], "CCDB")

    def test_an_export_is_not_overwritten(self):
        export_tag(self.source, "pass1", self.directory.name)
        with self.assertRaises(FileExistsError):
            export_tag(self.source, "pass1", self.directory.name)

    def test_cli(self):
        cli = CliManager()
        cli.exception_handling = CCDB_EXCEPTIONS_THROW
        cli.force_exceptions = True
        cli.theme = ccdb.cmd.themes.NoColorTheme()
        cli.connection_string = self.source
        cli.register_utilities()
        output, saved = StringIO(), sys.stdout
        sys.stdout = output
        try:
            cli.process_command_line("export tag @pass1 -o " + self.directory.name)
        finally:
            sys.stdout = saved
            cli.context.provider.disconnect()
        self.assertIn("tag pass1:", output.getvalue())
        self.assertTrue(os.path.exists(os.path.join(self.directory.name, "pass1.datacite.json")))
        with self.assertRaises(ValueError):
            cli.process_command_line("export tag @pass1 -r 100 -o " + self.directory.name)


if __name__ == "__main__":
    logging.getLogger("ccdb").setLevel(logging.WARNING)
    unittest.main()
