"""`ccdb db rehash` on an upgraded schema 5 database: design note schema6.md §8 and §4.1 (Q35), matrix row T24.

The database is the frozen schema 5 base (schema_v5_base.py) plus one non-ASCII set, upgraded by `ccdb db upgrade`;
a second non-ASCII set is written after the upgrade through create_assignment, so the backfill, the setter and
rehash all meet. SQLite runs always; MySQL and MariaDB run on the database of CCDB_TEST_MYSQL_CONNECTION when it is
set, where --server is compared too (see unit_test_upgrade_v6 for the variables). §14.1: `db rehash` exits 1 on a
mismatch and `rehash --apply` exits 0 when it repaired every mismatch.
"""
import tempfile
import unittest

import ccdb

# Have to import it this way as tests may be considered a package or not depending on context
try:
    from . import unit_test_upgrade_v6 as v6
except ImportError:
    import unit_test_upgrade_v6 as v6


LATIN_SET = 301
LATIN_VAULT = "µs|°C|ü"                       # every character also exists in latin1: it goes through the backfill
UNICODE_ROW = ["μs", "Ω", "Привет"]           # Greek and Cyrillic: written after the upgrade, through the setter
CHANGED_VAULT = "µs|°C|changed by SQL"


class RehashCases(object):
    """T24 for one backend: the class provides self.db"""

    def server_agrees(self, set_ids):
        """MySQL: SHA2 and LENGTH of the utf8mb4 text equal the stored sha256 and size; nothing to compare on SQLite"""

    def write_unicode_set(self):
        provider = ccdb.AlchemyProvider()
        provider.connect(self.db.url)
        provider.authentication.current_user_name = "test_user"
        try:
            provider.create_type_table("t24_unicode", "/test/test_vars", 1,
                                       [("unit", "string"), ("symbol", "string"), ("word", "string")], "T24 non-ASCII")
            assignment = provider.create_assignment([UNICODE_ROW], "/test/test_vars/t24_unicode", 0, ccdb.INFINITE_RUN,
                                                    "default", "T24 non-ASCII through the setter")
            return assignment.constant_set.id
        finally:
            provider.disconnect()

    def check_server_flag(self, expect_ok):
        pass

    def test_rehash(self):
        """T24 (§8): rehash agrees with the stored hashes and with --server for ASCII and non-ASCII; reports an SQL change"""
        from ccdb.model import vault_digest
        db = self.db
        db.build_v5()
        db.insert_sets([(LATIN_SET, 2, LATIN_VAULT)])
        run = v6.run_ccdb(db.url, v6.UPGRADE + db.no_tx_check)
        self.assertTrue(run.ok, run.text())
        unicode_set = self.write_unicode_set()

        stored = dict((row[0], row[1:]) for row in db.query("SELECT `id`, `vault`, `sha256`, `size` FROM `constantSets`"))
        self.assertEqual(stored[LATIN_SET][0], LATIN_VAULT)
        self.assertIn("Привет", stored[unicode_set][0])
        for set_id in (1, LATIN_SET, unicode_set):
            vault, sha256, size = stored[set_id]
            self.assertEqual((sha256, size), v6.digest(vault), "set %d" % set_id)
            self.assertEqual(vault_digest(vault), v6.digest(vault))
        self.server_agrees([1, LATIN_SET, unicode_set])

        for flags in ("", " --sample 2"):
            run = v6.run_ccdb(db.url, "db rehash" + flags)
            self.assertTrue(run.ok, run.text())
        self.check_server_flag(expect_ok=True)

        db.execute("UPDATE `constantSets` SET `vault` = :v WHERE `id` = :id", {"v": CHANGED_VAULT, "id": LATIN_SET})
        run = v6.run_ccdb(db.url, "db rehash")
        self.assertFalse(run.ok, "a mismatch exits 1\n" + run.text())
        self.assertRegex(run.said(), r"\b%d\b" % LATIN_SET, "the mismatch names the set")
        self.check_server_flag(expect_ok=False)

        last_log = db.max_log_id()
        run = v6.run_ccdb(db.url, "db rehash --apply")
        self.assertTrue(run.ok, "§14.1: rehash --apply exits 0 when it repaired every mismatch\n" + run.text())
        sha256, size = db.query("SELECT `sha256`, `size` FROM `constantSets` WHERE `id` = :id", {"id": LATIN_SET})[0]
        self.assertEqual((sha256, size), v6.digest(CHANGED_VAULT))
        records = db.logs_after(last_log)
        self.assertEqual(len(records), 1, "--apply writes one log record")
        self.assertRegex(records[0][1] + " " + records[0][3], r"\b%d\b|constantSets%d\b" % (LATIN_SET, LATIN_SET),
                         "the record lists the set ids")
        run = v6.run_ccdb(db.url, "db rehash")
        self.assertTrue(run.ok, run.text())


class SQLiteRehashTest(RehashCases, unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db = v6.SqliteDb(self.tmp_dir.name)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def check_server_flag(self, expect_ok):
        # MySQLRehashTest proves --server is a known option; on SQLite an argparse-style refusal is a refusal too
        run = v6.run_ccdb(self.db.url, "db rehash --server", allow_parse_error=True)
        self.assertFalse(run.ok, "--server is refused on SQLite\n" + run.text())


class MySQLRehashTest(RehashCases, unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.db = v6.MysqlDb(v6.mysql_url_or_skip())

    @classmethod
    def tearDownClass(cls):
        v6.restore_mysql_test_db(cls.db.url)

    def server_agrees(self, set_ids):
        for set_id in set_ids:
            rows = self.db.query("SELECT `sha256`, `size`, SHA2(CONVERT(`vault` USING utf8mb4), 256), "
                                 "LENGTH(CONVERT(`vault` USING utf8mb4)) FROM `constantSets` WHERE `id` = :id",
                                 {"id": set_id})
            sha256, size, server_sha256, server_size = rows[0]
            self.assertEqual((server_sha256, server_size), (sha256, size), "set %d" % set_id)

    def check_server_flag(self, expect_ok):
        run = v6.run_ccdb(self.db.url, "db rehash --server")
        self.assertEqual(run.ok, expect_ok, run.text())
        if not expect_ok:
            self.assertRegex(run.said(), r"\b%d\b" % LATIN_SET, "the mismatch names the set")


if __name__ == "__main__":
    unittest.main()
