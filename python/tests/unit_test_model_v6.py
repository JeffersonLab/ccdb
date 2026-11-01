"""Schema 6 model: hashed constant sets shared by assignments (T12, T13 of notes/schema6.md §14).

Pins §4.1 of the schema 6 design note: `ccdb.model.vault_digest`, the `vault` setter that hashes
(`ConstantSet.sha256`, `ConstantSet.size`), `data_list` and `data_table` going through that setter,
the many-to-one `Assignment.constant_set` without cascade, and the immutability of a stored set
(`ccdb.errors.ConstantSetIsImmutableError(set_id)` with the message §14.1 gives, Q40).

Each test builds the standard SQLite database with `create_sqlite_database` in a temporary
directory, which is schema 6 once PHASE0 item 2 lands. The new names are looked up inside the tests
(`model.vault_digest`, `errors.ConstantSetIsImmutableError`), so each test fails on its own feature
until item 3 exists, instead of the whole module failing at import.
"""
import hashlib
import os
import tempfile
import unittest
from unittest import mock

import sqlalchemy
from sqlalchemy import text
from sqlalchemy.orm import Session

from ccdb import errors, model
from ccdb import AlchemyProvider
from ccdb.model import Assignment, ConstantSet, RunRange, TypeTable, User, Variation
from ccdb.sql.sqlite_schema import create_sqlite_database

# Literals computed once with hashlib over the UTF-8 bytes; never recompute them in the test.
# Seed set 4 of /test/test_vars/test_table: §5.4 shows its prefix 55d35b501c1a in `vers -l`.
SEED_SET_4_ID = 4
SEED_SET_4_VAULT = "2.2|2.3|2.4|2.5|2.6|2.7"
SEED_SET_4_SHA256 = "55d35b501c1a5775b00fe77c00e7195ebe4d0b1b513ec0948d60df9cba239346"
SEED_SET_4_SIZE = 23

# "0.1|μs|Ω|Привет": 15 characters, 23 UTF-8 bytes
NON_ASCII_VAULT = "0.1|μs|Ω|Привет"
NON_ASCII_SHA256 = "9092a0055bc662bac60ba811a274058009e6515d6ac305650dbd82100b41f384"
NON_ASCII_SIZE = 23

EMPTY_SHA256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

# list_to_blob([1, 2.5, "a|b"]): the hash covers the blob text, delimiter replacement included
DELIMITER_LIST = [1, 2.5, "a|b"]
DELIMITER_VAULT = "1|2.5|a&delimiter;b"
DELIMITER_SHA256 = "2b215b7d6c3565865f1275e05dfa2cc609bbdabb6094199705e2bcd37758f204"
DELIMITER_SIZE = 19

# data_table [[0, 1, 2], [3, 4, 5]] for the 2 x 3 table /test/test_vars/test_table
TABLE_ROWS = [[0, 1, 2], [3, 4, 5]]
TABLE_VAULT = "0|1|2|3|4|5"
TABLE_SHA256 = "87b19a78e87fb010ece6c489f0ec08bb278fd7024a07c3f08cc9052c12ad0996"
TABLE_SIZE = 11

TEST_TABLE_PATH = "/test/test_vars/test_table"

# the message of ConstantSetIsImmutableError(set_id), as §14.1 (errors) gives it
IMMUTABLE_MESSAGE = "Constant set {0} is stored and cannot change"


class ModelV6Test(unittest.TestCase):
    """Each test gets a fresh standard SQLite database, one engine and one ORM session on it"""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp_dir.name, "model_v6.sqlite")
        create_sqlite_database(self.db_path)
        self.connection_str = "sqlite:///" + self.db_path
        self.engine = sqlalchemy.create_engine(self.connection_str)
        self.session = Session(bind=self.engine)

    def tearDown(self):
        self.session.close()
        self.engine.dispose()
        self.tmp_dir.cleanup()

    # -- helpers ---------------------------------------------------------------------------------

    def _seed_objects(self, session=None):
        """The 2 x 3 test table, variation 'default', run range 'all' and user 'test_user'

        A bare session leaves Directory.path empty (the provider fills it), so the table is checked
        by its directory name and shape instead of TypeTable.path.
        """
        session = session or self.session
        table = session.query(TypeTable).filter(TypeTable.name == "test_table").one()
        self.assertEqual(table.parent_dir.name, "test_vars")
        self.assertEqual((table.rows_count, table.columns_count), (2, 3))
        variation = session.query(Variation).filter(Variation.name == "default").one()
        run_range = session.query(RunRange).filter(RunRange.name == "all").one()
        user = session.query(User).filter(User.name == "test_user").one()
        return table, variation, run_range, user

    def _scalar(self, sql, **params):
        """One value read on a separate connection: what is stored, not what the session holds"""
        with self.engine.connect() as connection:
            return connection.execute(text(sql), params).scalar()

    def _stored_set(self, set_id):
        """(vault, sha256, size) of a constantSets row, read with SQL"""
        with self.engine.connect() as connection:
            row = connection.execute(
                text('SELECT "vault", "sha256", "size" FROM "constantSets" WHERE "id" = :id'),
                {"id": set_id}).fetchone()
        return None if row is None else tuple(row)

    def _count_sets(self):
        return self._scalar('SELECT COUNT(*) FROM "constantSets"')

    # -- T12 -------------------------------------------------------------------------------------

    def test_setter_hashes(self):
        """T12, §4.1: vault_digest and the vault setter store the sha256 and byte size; loading never calls the setter."""
        # the one function of Q35
        self.assertEqual(model.vault_digest("1|2|3"), (hashlib.sha256(b"1|2|3").hexdigest(), 5))
        self.assertEqual(model.vault_digest(NON_ASCII_VAULT), (NON_ASCII_SHA256, NON_ASCII_SIZE))

        # the setter on a new set
        constant_set = ConstantSet()
        constant_set.vault = "1|2|3"
        self.assertEqual(constant_set.vault, "1|2|3")
        self.assertEqual(constant_set.sha256, hashlib.sha256(b"1|2|3").hexdigest())
        self.assertEqual(constant_set.size, 5)

        # a set without an id may still change, and the hash follows the text
        constant_set.vault = NON_ASCII_VAULT
        self.assertEqual(constant_set.vault, NON_ASCII_VAULT)
        self.assertEqual(constant_set.sha256, NON_ASCII_SHA256)
        self.assertEqual(constant_set.size, NON_ASCII_SIZE)          # bytes, not the 15 characters

        # the declarative constructor reaches the setter (create_assignment's ConstantSet(table, vault=text))
        built = ConstantSet(vault=DELIMITER_VAULT)
        self.assertEqual((built.sha256, built.size), (DELIMITER_SHA256, DELIMITER_SIZE))

        # data_list goes through the setter: the hash covers the blob, delimiter replacement included
        from_list = ConstantSet()
        from_list.data_list = DELIMITER_LIST
        self.assertEqual(from_list.vault, DELIMITER_VAULT)
        self.assertEqual((from_list.sha256, from_list.size), (DELIMITER_SHA256, DELIMITER_SIZE))

        # what the setter computed is what the row stores
        table, _, _, _ = self._seed_objects()
        constant_set.type_table = table
        self.session.add(constant_set)
        self.session.commit()
        set_id = constant_set.id
        self.assertEqual(self._stored_set(set_id), (NON_ASCII_VAULT, NON_ASCII_SHA256, NON_ASCII_SIZE))

        # loading reads the stored columns and never calls the setter: a wrong stored hash stays visible
        # (db rehash relies on this). Committed first: SQLite would lock the raw write otherwise.
        self.session.close()
        tampered = "f" * 64                                         # no other set of the table has it
        with self.engine.begin() as connection:
            connection.execute(text('UPDATE "constantSets" SET "sha256" = :h, "size" = 0 WHERE "id" = :id'),
                               {"h": tampered, "id": set_id})
        with Session(bind=self.engine) as session:
            loaded = session.get(ConstantSet, set_id)
            self.assertEqual(loaded.vault, NON_ASCII_VAULT)
            self.assertEqual(loaded.sha256, tampered)
            self.assertEqual(loaded.size, 0)

    def test_data_table_goes_through_setter(self):
        """T12, §4.1: the data_table setter reaches the vault setter, which hashes with vault_digest."""
        table, _, _, _ = self._seed_objects()

        with mock.patch.object(model, "vault_digest", wraps=model.vault_digest) as digest:
            constant_set = ConstantSet()
            constant_set.type_table = table
            constant_set.data_table = TABLE_ROWS
        digest.assert_called_once_with(TABLE_VAULT)                 # one function computes every hash (Q35)

        self.assertEqual(constant_set.vault, TABLE_VAULT)
        self.assertEqual(constant_set.sha256, TABLE_SHA256)
        self.assertEqual(constant_set.size, TABLE_SIZE)

        self.session.add(constant_set)
        self.session.commit()
        self.assertEqual(self._stored_set(constant_set.id), (TABLE_VAULT, TABLE_SHA256, TABLE_SIZE))

    def test_known_blob_hash(self):
        """T12, §4.1: known blobs hash to literals computed once; seed set 4 stores its literal (§5.4 prefix)."""
        self.assertEqual(model.vault_digest(SEED_SET_4_VAULT), (SEED_SET_4_SHA256, SEED_SET_4_SIZE))
        self.assertEqual(model.vault_digest(NON_ASCII_VAULT), (NON_ASCII_SHA256, NON_ASCII_SIZE))
        self.assertEqual(model.vault_digest(""), (EMPTY_SHA256, 0))

        constant_set = ConstantSet()
        constant_set.vault = SEED_SET_4_VAULT
        self.assertEqual((constant_set.sha256, constant_set.size), (SEED_SET_4_SHA256, SEED_SET_4_SIZE))

        # the fresh database's seed carries the same literal, read through the ORM and with SQL
        seed_set = self.session.get(ConstantSet, SEED_SET_4_ID)
        self.assertEqual(seed_set.vault, SEED_SET_4_VAULT)
        self.assertEqual((seed_set.sha256, seed_set.size), (SEED_SET_4_SHA256, SEED_SET_4_SIZE))
        self.assertEqual(self._stored_set(SEED_SET_4_ID), (SEED_SET_4_VAULT, SEED_SET_4_SHA256, SEED_SET_4_SIZE))
        self.assertEqual(seed_set.sha256[:12], "55d35b501c1a")

    # -- T13 -------------------------------------------------------------------------------------

    def test_set_survives_deleting_one_sharer(self):
        """T13, §4.1: the ORM never deletes a set (no cascade), not even with its last sharer.

        Deleting one of two sharers keeps the set and the other's link; deleting the last keeps the set too.
        provider.delete_assignment deletes a set with its last assignment by an explicit statement (§5.2).
        """
        table, variation, run_range, user = self._seed_objects()

        constant_set = ConstantSet()
        constant_set.type_table = table
        constant_set.data_table = [[7, 8, 9], [10, 11, 12]]
        first = Assignment(constant_set=constant_set, run_range=run_range, variation=variation,
                           author_id=user.id, comment="first sharer")
        second = Assignment(constant_set=constant_set, run_range=run_range, variation=variation,
                            author_id=user.id, comment="second sharer")
        self.session.add_all([first, second])
        self.session.commit()
        set_id, first_id, second_id = constant_set.id, first.id, second.id
        sets_before = self._count_sets()

        # delete one sharer through the ORM
        self.session.delete(first)
        self.session.commit()

        self.assertEqual(self._count_sets(), sets_before)
        self.assertIsNotNone(self._stored_set(set_id))
        self.assertIsNone(self._scalar('SELECT "id" FROM "assignments" WHERE "id" = :id', id=first_id))
        self.assertEqual(self._scalar('SELECT "constantSetId" FROM "assignments" WHERE "id" = :id', id=second_id),
                         set_id)

        with Session(bind=self.engine) as session:
            survivor = session.get(ConstantSet, set_id)
            self.assertEqual([a.id for a in survivor.assignments], [second_id])
            self.assertEqual(session.get(Assignment, second_id).constant_set.vault, "7|8|9|10|11|12")

        # deleting the last sharer through the ORM leaves an unused set; provider.delete_assignment would delete it
        # by an explicit statement (§5.2), and db dedup and rm -t remove unused sets (§5.2, §7)
        self.session.delete(self.session.get(Assignment, second_id))
        self.session.commit()
        self.assertEqual(self._count_sets(), sets_before)
        self.assertEqual(self._stored_set(set_id)[0], "7|8|9|10|11|12")

    def test_two_assignments_share_in_one_session(self):
        """T13, §4.1: one new set given to two new assignments in one session is stored once, with one commit."""
        table, variation, run_range, user = self._seed_objects()
        sets_before = self._count_sets()

        constant_set = ConstantSet()
        constant_set.vault = "1.5|2.5|3.5|4.5|5.5|6.5"
        constant_set.type_table = table
        first = Assignment(constant_set=constant_set, run_range=run_range, variation=variation,
                           author_id=user.id, comment="first sharer")
        second = Assignment(constant_set=constant_set, run_range=run_range, variation=variation,
                            author_id=user.id, comment="second sharer")
        self.session.add_all([first, second])
        self.session.commit()

        self.assertIs(first.constant_set, second.constant_set)
        self.assertEqual(first.constant_set_id, constant_set.id)
        self.assertEqual(second.constant_set_id, constant_set.id)
        self.assertEqual(self._count_sets(), sets_before + 1)
        self.assertEqual(
            self._scalar('SELECT COUNT(*) FROM "assignments" WHERE "constantSetId" = :id', id=constant_set.id), 2)
        self.assertEqual(self._stored_set(constant_set.id),
                         ("1.5|2.5|3.5|4.5|5.5|6.5",) + model.vault_digest("1.5|2.5|3.5|4.5|5.5|6.5"))

        with Session(bind=self.engine) as session:
            stored = session.get(ConstantSet, constant_set.id)
            self.assertEqual(sorted(a.id for a in stored.assignments), sorted([first.id, second.id]))

    def test_stored_set_is_immutable(self):
        """T13, §4.1 and §5.2 (Q40): a stored set refuses a new vault through every setter; the row stays."""
        stored = self.session.get(ConstantSet, SEED_SET_4_ID)
        self.assertEqual(stored.vault, SEED_SET_4_VAULT)

        with self.assertRaises(errors.ConstantSetIsImmutableError) as raised:
            stored.vault = "9|9|9|9|9|9"
        self.assertEqual(str(raised.exception), IMMUTABLE_MESSAGE.format(SEED_SET_4_ID))

        with self.assertRaises(errors.ConstantSetIsImmutableError):
            stored.data_list = ["9", "9", "9", "9", "9", "9"]
        with self.assertRaises(errors.ConstantSetIsImmutableError):
            stored.data_table = [[9, 9, 9], [9, 9, 9]]

        # the refused writes changed nothing in memory
        self.assertEqual(stored.vault, SEED_SET_4_VAULT)
        self.assertEqual((stored.sha256, stored.size), (SEED_SET_4_SHA256, SEED_SET_4_SIZE))

        # re-setting the same text is not a change and is allowed
        stored.vault = SEED_SET_4_VAULT
        self.assertEqual((stored.sha256, stored.size), (SEED_SET_4_SHA256, SEED_SET_4_SIZE))

        # nothing reaches the row
        self.session.commit()
        self.assertEqual(self._stored_set(SEED_SET_4_ID), (SEED_SET_4_VAULT, SEED_SET_4_SHA256, SEED_SET_4_SIZE))
        self.session.close()

        # through the provider (update_assignment, §5.2): data refused, assignment fields still update
        provider = AlchemyProvider()
        provider.logging_enabled = False
        provider.authentication.current_user_name = "test_user"
        provider.connect(self.connection_str)
        try:
            assignment = provider.get_assignment(TEST_TABLE_PATH, 100, "default")
            self.assertEqual(assignment.constant_set.id, SEED_SET_4_ID)
            assignment_id = assignment.id
            with self.assertRaises(errors.ConstantSetIsImmutableError):
                assignment.constant_set.data_table = [[9, 9, 9], [9, 9, 9]]
            assignment.comment = "comment changed in place"
            provider.update_assignment(assignment)
        finally:
            provider.disconnect()

        self.assertEqual(self._scalar('SELECT "comment" FROM "assignments" WHERE "id" = :id', id=assignment_id),
                         "comment changed in place")
        self.assertEqual(self._stored_set(SEED_SET_4_ID), (SEED_SET_4_VAULT, SEED_SET_4_SHA256, SEED_SET_4_SIZE))


if __name__ == "__main__":
    unittest.main()
