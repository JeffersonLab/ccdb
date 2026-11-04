"""The HTTP API (ccdb.api, docs/apis/http.md) on the test database of `ccdb db init`.

Checks the endpoints, the cache rules of each address form, the three data forms (data.json and data.txt byte-identical
to the web GUI's, the stored hash equal to SHA-256 over the served bytes), the comparison, the table schema, errors as
JSON, and the OpenAPI document. Skipped when the api extra (fastapi, httpx) is not installed.
"""
import hashlib
import json
import os
import time
import tempfile
import unittest
from urllib.parse import quote

from ccdb import testing
from ccdb.sql.sqlite_schema import create_sqlite_database

try:
    from fastapi.testclient import TestClient
    from ccdb.api import create_app
except ImportError:  # the api extra is not installed
    TestClient = None

TABLE = "/test/test_vars/test_table"
NEWEST = TABLE + ":0:default"                            # assignments 1 and 4 match; 4 is the newest
EXACT = TABLE + ":0:default:2012-10-30_23-48-42"         # names assignment 4 for good
IMMUTABLE = "public, max-age=31536000, immutable"


def setUpModule():
    # the data holds literal UTC times that the tests compare with shown (local) times
    global _restore_time_zone
    _restore_time_zone = testing.pin_time_zone("UTC")


def tearDownModule():
    _restore_time_zone()


@unittest.skipIf(TestClient is None, "the api extra (fastapi, httpx) is not installed")
class ApiTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        cls.path = os.path.join(cls.directory.name, "api.sqlite")
        create_sqlite_database(cls.path)
        cls.connection = "sqlite:///" + cls.path
        cls.app = create_app(cls.connection)
        cls.client = TestClient(cls.app)
        os.environ["CCDB_API_CACHE_DIR"] = os.path.join(cls.directory.name, "cache")

    @classmethod
    def tearDownClass(cls):
        cls.app.state.database.dispose()
        os.environ.pop("CCDB_API_CACHE_DIR", None)
        cls.directory.cleanup()

    def get(self, url, **kwargs):
        return self.client.get("/api/v1" + url, follow_redirects=False, **kwargs)

    def json(self, url):
        response = self.get(url)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    # ------------------------------------------------------------------ service

    def test_without_a_connection_the_app_says_how_to_give_one(self):
        saved = {name: os.environ.pop(name, None) for name in ("CCDB_CONNECTION", "CCDB_API_CONNECTION")}
        try:
            with self.assertRaises(RuntimeError) as raised:
                create_app()
            self.assertIn("CCDB_CONNECTION", str(raised.exception))
        finally:
            for name, value in saved.items():
                if value is not None:
                    os.environ[name] = value

    def test_health(self):
        response = self.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
        self.assertEqual(response.headers["Cache-Control"], "no-store")

    def test_health_of_a_database_that_does_not_open(self):
        client = TestClient(create_app("sqlite:///" + os.path.join(self.directory.name, "missing", "no.sqlite")))
        response = client.get("/api/v1/health")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"status": "error", "database": "unavailable", "version": response.json()["version"]})

    def test_instance(self):
        data = self.json("/instance")
        self.assertEqual(data["schema_version"], 6)
        self.assertIsInstance(data["properties"], dict)

    def test_readiness_profile(self):
        """/readiness is `ccdb db readiness --json`, cached for an hour; a negative window is refused"""
        from ccdb import AlchemyProvider
        from ccdb.readiness import profile
        response = self.get("/readiness?stale_years=3")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.headers["Cache-Control"], "public, max-age=3600")
        served = response.json()
        provider = AlchemyProvider()
        provider.connect(self.connection)
        try:
            expected = profile(provider, stale_years=3)
        finally:
            provider.disconnect()
        served["config"].pop("generated"), expected["config"].pop("generated")
        self.assertEqual(served, expected)
        self.assertEqual(self.get("/readiness?stale_years=-1").status_code // 100, 4)

    def test_tag_properties(self):
        """/tags and /tags/{name} carry the tag's properties; a fresh database, so the shared one stays without tags"""
        from fastapi.testclient import TestClient
        from ccdb import AlchemyProvider
        path = os.path.join(self.directory.name, "tags.sqlite")
        create_sqlite_database(path)
        provider = AlchemyProvider()
        provider.connect("sqlite:///" + path)
        provider.authentication.current_user_name = "test_user"
        tag = provider.create_tag("pass1", "default", comment="for properties")
        provider.set_property("tag", tag.id, "software", "eicrecon-1.42.0")
        provider.disconnect()
        app = create_app("sqlite:///" + path)
        try:
            client = TestClient(app)
            self.assertEqual(client.get("/api/v1/tags/pass1").json()["properties"], {"software": "eicrecon-1.42.0"})
            self.assertEqual(client.get("/api/v1/tags").json()[0]["properties"], {"software": "eicrecon-1.42.0"})
        finally:
            app.state.database.dispose()

    def test_property_vocabulary(self):
        from ccdb.vocabulary import STANDARD_NAMES
        data = self.json("/properties/vocabulary")
        self.assertEqual(data["owner_types"], {owner: list(names) for owner, names in STANDARD_NAMES.items()})
        self.assertIn("doi", data["meanings"])
        self.assertEqual(data["instance_additions"], [])

    def test_card_as_jsonld(self):
        response = self.get("/tables/test/test_vars/test_table/card?format=jsonld")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.headers["content-type"].startswith("application/ld+json"))
        record = response.json()
        self.assertEqual((record["@context"], record["@type"]), ("https://schema.org", "Dataset"))
        self.assertEqual(record["identifier"], "/test/test_vars/test_table")
        self.assertEqual([variable["name"] for variable in record["variableMeasured"]], ["x", "y", "z"])
        self.assertTrue(record["url"].endswith("/api/v1/tables/test/test_vars/test_table/card"))
        self.assertIn("dateModified", record)
        self.assertEqual(self.get("/tables/test/test_vars/test_table/card?format=xml").status_code, 400)

    def test_openapi_document(self):
        document = self.json("/openapi.json")
        self.assertTrue(document["openapi"].startswith("3."))
        for path in ("/api/v1/health", "/api/v1/tables/{path}", "/api/v1/assignments/{assignment_id}", "/api/v1/bundle"):
            self.assertIn(path, document["paths"])
        self.assertIn("TableInfo", document["components"]["schemas"])

    # ------------------------------------------------------------------ browse

    def test_directories_and_tables(self):
        paths = [each["path"] for each in self.json("/directories")]
        self.assertIn("/test/test_vars", paths)
        directory = self.json("/directories/test/test_vars")
        self.assertIn("test_table", [each["name"] for each in directory["tables"]])
        self.assertIn("/test/test_vars/test_table", [each["path"] for each in self.json("/tables?search=test_tab*")])
        table = self.json("/tables" + TABLE)
        self.assertEqual([column["name"] for column in table["columns"]], ["x", "y", "z"])
        self.assertEqual(table["rows"], 2)
        self.assertGreaterEqual(table["assignments"], 2)
        self.assertEqual(self.get("/tables/test/no_such_table").status_code, 404)

    def test_versions_page(self):
        page = self.json("/tables" + TABLE + "/versions?per_page=25&sort=id&order=asc")
        self.assertEqual(page["sort"], "id")
        self.assertEqual([item["id"] for item in page["items"]], sorted(item["id"] for item in page["items"]))
        self.assertTrue(all(item["created"].endswith("Z") for item in page["items"]))
        self.assertEqual(self.get("/tables" + TABLE + "/versions?sort=nonsense").status_code, 400)

    def test_variations_run_ranges_tags_logs(self):
        variations = {each["name"]: each for each in self.json("/variations")}
        self.assertEqual(variations["subtest"]["chain"], ["default", "test", "subtest"])
        self.assertEqual(self.json("/variations/test")["parent"], "default")
        self.assertIn("all", [each["name"] for each in self.json("/run-ranges")])
        self.assertEqual(self.json("/tags"), [])
        self.assertEqual(self.get("/tags/no_such_tag").status_code, 404)
        logs = self.json("/logs?per_page=25")
        self.assertIn("items", logs)

    # ------------------------------------------------------------------ assignments

    def test_a_resolving_request_redirects_to_the_id_form(self):
        response = self.get("/assignments?request=" + quote(NEWEST))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Cache-Control"], "public, max-age=60")
        self.assertTrue(response.headers["Location"].endswith("/api/v1/assignments/4"), response.headers["Location"])
        data_response = self.get("/assignments/data.txt?request=" + quote(NEWEST))
        self.assertTrue(data_response.headers["Location"].endswith("/api/v1/assignments/4/data.txt"))

    def test_an_exact_address_is_immutable(self):
        for url in ("/assignments/4", "/assignments?request=" + quote(EXACT), "/assignments/4/data.json"):
            response = self.get(url)
            self.assertEqual(response.status_code, 200, url)
            self.assertEqual(response.headers["Cache-Control"], IMMUTABLE, url)
        self.assertEqual(self.json("/assignments?request=" + quote(EXACT))["id"], 4)

    def test_etag_gives_304(self):
        first = self.get("/assignments/4/data")
        again = self.get("/assignments/4/data", headers={"If-None-Match": first.headers["ETag"]})
        self.assertEqual(again.status_code, 304)
        self.assertEqual(again.content, b"")

    def test_data_forms_and_the_stored_hash(self):
        info = self.json("/assignments/4")
        raw = self.get("/assignments/4/data")
        self.assertEqual(raw.headers["X-CCDB-SHA256"], hashlib.sha256(raw.content).hexdigest())
        self.assertEqual(raw.headers["X-CCDB-SHA256"], info["sha256"])
        self.assertEqual(raw.headers["ETag"], '"{0}"'.format(info["sha256"]))
        self.assertEqual(int(raw.headers["X-CCDB-Size"]), len(raw.content))
        self.assertEqual((raw.headers["X-CCDB-Rows"], raw.headers["X-CCDB-Columns"]), ("2", "3"))
        self.assertEqual([column["name"] for column in json.loads(raw.headers["X-CCDB-Schema"])], ["x", "y", "z"])
        self.assertEqual(raw.text, "2.2|2.3|2.4|2.5|2.6|2.7")

    def test_data_json_and_text_equal_the_web_gui(self):
        from ccdb.webgui import cerate_ccdb_flask_app
        from ccdb.webgui.db import get_database
        gui = cerate_ccdb_flask_app(self.connection)
        try:
            gui_client = gui.test_client()
            for form in ("data.json", "data.txt"):
                with self.subTest(form=form):
                    self.assertEqual(self.get("/assignments/4/" + form).content, gui_client.get("/assignments/4/" + form).get_data())
            api_compare = self.get("/compare?a=1&b=4").content
            self.assertEqual(api_compare, gui_client.get("/compare/data.json?a=1&b=4&changed=0").get_data())
            self.assertEqual(self.get("/compare.diff?a=1&b=4").content, gui_client.get("/compare/data.diff?a=1&b=4").get_data())
        finally:
            get_database(gui).dispose()

    def test_errors_are_json(self):
        for url, status in (("/assignments/999999", 404), ("/assignments?request=" + quote(TABLE + ":abc"), 400),
                            ("/assignments/data.yaml?request=" + quote(NEWEST), 404), ("/assignments", 400),
                            ("/compare?a=1&b=3", 400)):
            with self.subTest(url=url):
                response = self.get(url)
                self.assertEqual(response.status_code, status, response.text)
                self.assertEqual(response.json()["status"], status)
                self.assertEqual(response.headers["Cache-Control"], "no-store")

    def test_table_schema_describes_data_json(self):
        import jsonschema
        schema = self.json("/tables" + TABLE + "/schema")
        rows = self.json("/assignments/4/data.json")["rows"]
        jsonschema.validate(rows, schema)
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(rows[:1], schema)

    # ------------------------------------------------------------------ bundle

    def test_bundle_builds_are_bounded(self):
        """A burst of requests for many runs builds at most BUNDLE_BUILDS bundles at a time (F30)"""
        import threading
        from concurrent.futures import ThreadPoolExecutor
        from unittest import mock
        from ccdb.api import snapshots
        lock, state = threading.Lock(), {"running": 0, "peak": 0}

        def slow_build(source, cache_dir, run, variation="default", max_time_utc=None, tag=None):
            with lock:
                state["running"] += 1
                state["peak"] = max(state["peak"], state["running"])
            time.sleep(0.05)
            path = os.path.join(self.directory.name, "fake_bundle_{0}.sqlite".format(run))
            with open(path, "wb") as file:
                file.write(b"bundle of run %d" % run)
            with lock:
                state["running"] -= 1
            return path

        with mock.patch.object(snapshots.snapshot, "run_bundle", slow_build):
            with ThreadPoolExecutor(max_workers=16) as pool:
                statuses = list(pool.map(lambda run: self.client.get("/api/v1/bundle?run={0}&time=2020-01-01".format(run)).status_code,
                                         range(1000, 1024)))
        self.assertEqual(statuses, [200] * 24)
        self.assertLessEqual(state["peak"], snapshots.BUNDLE_BUILDS)
        self.assertGreaterEqual(state["peak"], 1)

    def test_bundle_by_time_and_by_tag(self):
        from ccdb import AlchemyProvider
        response = self.get("/bundle?run=100")
        self.assertEqual(response.status_code, 302)
        location = response.headers["Location"]
        self.assertIn("time=", location)
        bundle = self.client.get(location)
        self.assertEqual(bundle.status_code, 200)
        self.assertEqual(bundle.headers["Cache-Control"], IMMUTABLE)
        self.assertEqual(bundle.headers["X-CCDB-SHA256"], hashlib.sha256(bundle.content).hexdigest())
        path = os.path.join(self.directory.name, "bundle.sqlite")
        with open(path, "wb") as file:
            file.write(bundle.content)
        provider = AlchemyProvider()
        provider.connect("sqlite:///" + path)
        source = AlchemyProvider()
        source.connect(self.connection)
        try:
            self.assertEqual(provider.get_assignment(TABLE, 100, "default").constant_set.vault,
                             source.get_assignment(TABLE, 100, "default").constant_set.vault)
        finally:
            provider.disconnect()
            source.disconnect()
        self.assertEqual(self.get("/bundle?run=100&variation=default&tag=x").status_code, 400)
        self.assertEqual(self.get("/bundle?run=100&tag=no_such_tag").status_code, 404)


if __name__ == '__main__':
    unittest.main()
