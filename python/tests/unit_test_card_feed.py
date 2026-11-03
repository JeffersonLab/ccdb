"""The data card (GUI /tables/<path>/card, API /api/v1/tables/<path>/card) and the change feed (/api/v1/logs.atom)
on the demo tables: every card value equals what SQL on the file gives, computed here without CCDB's code; the feed
is Atom 1.0 with the elements RFC 4287 requires, newest first. Skipped without the api extra."""
import importlib.util
import os
import sqlite3
import tempfile
import unittest
from xml.etree import ElementTree

import ccdb
from ccdb import testing
from ccdb.webgui import create_ccdb_flask_app

try:
    from fastapi.testclient import TestClient
    from ccdb.api import create_app
except ImportError:  # the api extra is not installed
    TestClient = None

ATOM = "{http://www.w3.org/2005/Atom}"
TABLES = ["/epic/TOFBarrel/lgad_calibration", "/epic/EcalBarrel/adc_calib", "/epic/EcalEndcapN/pi_rejection_model",
          "/test/test_vars/test_table"]


def _load_generator():
    path = os.path.join(ccdb.get_ccdb_home_path(), "scripts", "demo", "make_epic_tables.py")
    spec = importlib.util.spec_from_file_location("ccdb_scripts_demo_make_epic_tables", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def utc_text(stored):
    """A stored UTC time text (with or without its fraction) as the API writes it"""
    return stored.replace(" ", "T") + ("" if "." in stored else ".000000") + "Z"


def merged(ranges):
    result = []
    for low, high in sorted(ranges):
        if result and low <= result[-1][1] + 1:
            result[-1][1] = max(result[-1][1], high)
        else:
            result.append([low, high])
    return result


@unittest.skipIf(TestClient is None, "the api extra (fastapi, httpx) is not installed")
class CardAndFeedTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.restore = testing.pin_time_zone("UTC")
        cls.directory = tempfile.TemporaryDirectory()
        cls.path = os.path.join(cls.directory.name, "demo.sqlite")
        connection = "sqlite:///" + cls.path
        _load_generator().build(connection)
        cls.api = TestClient(create_app(connection))
        cls.gui = create_ccdb_flask_app(connection).test_client()
        cls.sql = sqlite3.connect(cls.path)

    @classmethod
    def tearDownClass(cls):
        cls.sql.close()
        cls.directory.cleanup()
        cls.restore()

    # ------------------------------------------------------------------ the card by SQL alone

    def table_id(self, path):
        directory_id = 0
        *directories, name = path.strip("/").split("/")
        for part in directories:
            directory_id = self.sql.execute("SELECT id FROM directories WHERE name = ? AND parentId = ?", (part, directory_id)).fetchone()[0]
        return self.sql.execute("SELECT id FROM typeTables WHERE name = ? AND directoryId = ?", (name, directory_id)).fetchone()[0]

    def expected_card(self, path):
        table_id = self.table_id(path)
        rows = self.sql.execute(
            "SELECT v.name, r.runMin, r.runMax, u.name, a.created, a.comment, a.variationId FROM assignments a "
            "JOIN constantSets s ON a.constantSetId = s.id JOIN variations v ON a.variationId = v.id "
            "JOIN runRanges r ON a.runRangeId = r.id LEFT JOIN users u ON a.authorId = u.id "
            "WHERE s.constantTypeId = ? ORDER BY a.created, a.id", (table_id,)).fetchall()
        variations = {}
        authors = {}
        for variation, run_min, run_max, author, _, _, _ in rows:
            variations.setdefault(variation, []).append((run_min, run_max))
            authors[author or ""] = authors.get(author or "", 0) + 1
        tags = []
        for name, variation_id, snapshot in self.sql.execute("SELECT name, variationId, snapshotTime FROM tags ORDER BY name"):
            chain, current = [], variation_id
            while current:
                chain.append(current)
                current = self.sql.execute("SELECT parentId FROM variations WHERE id = ?", (current,)).fetchone()[0]
            if any(row[6] in chain and row[4] <= snapshot for row in rows):
                tags.append(name)
        instance = dict(self.sql.execute("SELECT name, value FROM properties WHERE ownerType = 'instance'").fetchall())
        last = rows[-1] if rows else None
        return {"versions": len(rows),
                "variations": [{"name": name, "versions": len(found), "runs": merged(found)} for name, found in sorted(variations.items())],
                "authors": [{"name": name, "assignments": count} for name, count in sorted(authors.items(), key=lambda item: (-item[1], item[0]))],
                "last_change": None if last is None else {"created": utc_text(last[4]), "author": last[3] or "",
                                                           "variation": last[0], "comment": last[5] or ""},
                "tags": tags,
                "properties": dict(self.sql.execute("SELECT name, value FROM properties WHERE ownerType = 'table' AND ownerId = ?",
                                                    (table_id,)).fetchall()),
                "license": instance.get("license", ""), "citation": instance.get("citation", ""),
                "columns": [(name, kind, units or "") for name, kind, units in self.sql.execute(
                    'SELECT name, columnType, units FROM columns WHERE typeId = ? ORDER BY "order"', (table_id,))]}

    def test_card_values_equal_sql(self):
        for path in TABLES:
            with self.subTest(path=path):
                response = self.api.get("/api/v1/tables" + path + "/card")
                self.assertEqual(response.status_code, 200, response.text)
                self.assertIn("max-age=60", response.headers["cache-control"])
                card = response.json()
                expected = self.expected_card(path)
                for key in ("versions", "variations", "authors", "last_change", "tags", "properties", "license", "citation"):
                    self.assertEqual(card[key], expected[key], key)
                self.assertEqual([(column["name"], column["type"], column.get("units") or "") for column in card["columns"]],
                                 expected["columns"])
                self.assertEqual(card["path"], path)

    def test_card_examples(self):
        card = self.api.get("/api/v1/tables/epic/TOFBarrel/lgad_calibration/card").json()
        self.assertEqual(card["tags"], ["campaign_demo"])
        self.assertEqual([each["name"] for each in card["variations"]], ["default", "mc"])
        self.assertEqual(card["variations"][0]["runs"], [[1, 1999]])
        self.assertEqual(card["last_change"]["comment"], "late correction of tIntercept")
        self.assertTrue(card["license"].startswith("LGPL-3.0-or-later"))

    def test_card_unknown_table(self):
        self.assertEqual(self.api.get("/api/v1/tables/no/such/table/card").status_code, 404)
        self.assertEqual(self.gui.get("/tables/no/such/table/card").status_code, 404)

    def test_gui_card(self):
        page = self.gui.get("/tables/epic/TOFBarrel/lgad_calibration/card")
        self.assertEqual(page.status_code, 200)
        text = page.get_data(as_text=True)
        self.assertIn('data-card="versions">4<', text)
        self.assertIn("@campaign_demo", text)
        self.assertIn('<tr data-variation="default"><td>default</td><td class="text-end">3</td><td class="cell-mono">1–1999</td></tr>', text)
        self.assertIn("0–inf", text)
        self.assertIn("ns/TDC", text)
        versions = self.gui.get("/versions/epic/TOFBarrel/lgad_calibration").get_data(as_text=True)
        self.assertIn('href="/tables/epic/TOFBarrel/lgad_calibration/card"', versions)

    # ------------------------------------------------------------------ the feed

    def test_atom_feed(self):
        response = self.api.get("/api/v1/logs.atom?per_page=25")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.headers["content-type"].startswith("application/atom+xml"))
        feed = ElementTree.fromstring(response.content)
        self.assertEqual(feed.tag, ATOM + "feed")
        for required in ("id", "title", "updated"):
            self.assertIsNotNone(feed.find(ATOM + required), required)
        self.assertEqual(feed.find(ATOM + "link").get("rel"), "self")
        entries = feed.findall(ATOM + "entry")
        logs = self.sql.execute("SELECT id, created FROM logs ORDER BY id DESC LIMIT 25").fetchall()
        self.assertEqual(len(entries), len(logs))
        self.assertGreater(len(entries), 0)
        ids = []
        for entry, (log_id, created) in zip(entries, logs):
            for required in ("id", "title", "updated"):
                self.assertTrue(entry.find(ATOM + required).text, required)
            self.assertIsNotNone(entry.find(ATOM + "author/" + ATOM + "name"))
            self.assertTrue(entry.find(ATOM + "id").text.endswith("/api/v1/logs/{0}".format(log_id)))
            self.assertEqual(entry.find(ATOM + "updated").text, utc_text(created))
            ids.append(entry.find(ATOM + "id").text)
        self.assertEqual(len(set(ids)), len(ids))
        self.assertEqual(feed.find(ATOM + "updated").text, entries[0].find(ATOM + "updated").text)
        # an entry's link answers
        link = entries[0].find(ATOM + "link").get("href")
        self.assertEqual(self.api.get(link.replace("http://testserver", "")).status_code, 200)

    def test_atom_search(self):
        feed = ElementTree.fromstring(self.api.get("/api/v1/logs.atom?search=lgad_calibration").content)
        titles = [entry.find(ATOM + "title").text for entry in feed.findall(ATOM + "entry")]
        self.assertTrue(titles)
        self.assertTrue(all("lgad_calibration" in title for title in titles))


if __name__ == "__main__":
    unittest.main()
