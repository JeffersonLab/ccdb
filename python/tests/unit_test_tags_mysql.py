"""
Tags on MySQL and MariaDB: the server branch of tag resolution (UNIX_TIMESTAMP(assignments.created) compared to the
epoch of the tag's UTC instant) and the rm -a refusal while a tag may resolve to the assignment.

Runs on the database of CCDB_TEST_MYSQL_CONNECTION, re-initialized by `db init` before each test; skipped when the
variable is unset. The assignment and tag times are days apart, so neither the server nor the process time zone
can move one across another.
"""

import contextlib
import io
import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

from sqlalchemy import text
from sqlalchemy.exc import NoResultFound

import ccdb
import ccdb.cmd.themes
from ccdb import testing as helper
from ccdb.cmd.cli_manager import CliManager, CCDB_EXCEPTIONS_THROW
from ccdb.errors import ObjectIsNotFoundInDbError

TABLE = "/test/test_vars/test_table"
RUN = 100


def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


@unittest.skipUnless(helper.ENV_TEST_MYSQL in os.environ, "{} is not set".format(helper.ENV_TEST_MYSQL))
class MySqlTagsTest(unittest.TestCase):

    @staticmethod
    def restore_database(connection_str):
        with contextlib.redirect_stdout(io.StringIO()):
            helper.recreate_mysql_db(connection_str)

    def setUp(self):
        connection_str = os.environ[helper.ENV_TEST_MYSQL]
        with contextlib.redirect_stdout(io.StringIO()):
            helper.recreate_mysql_db(connection_str)
        # Modules that run later in the same process (CI runs the list in one) read the db init content, so the
        # tags and assignments added here are removed. Registered first, so it runs after the provider disconnects.
        self.addCleanup(self.restore_database, connection_str)

        self.cli = CliManager()
        self.cli.exception_handling = CCDB_EXCEPTIONS_THROW
        self.cli.force_exceptions = True
        self.cli.theme = ccdb.cmd.themes.NoColorTheme()
        self.cli.connection_string = connection_str
        self.cli.context.user_name = "test_user"
        self.cli.register_utilities()
        self.addCleanup(self.cli.provider.disconnect)
        with contextlib.redirect_stdout(io.StringIO()):
            self.cli.process_command_line("ls /")       # the CLI connects on its first database command
        self.provider = self.cli.provider
        self.provider.logging_enabled = True
        self.assertIn(self.provider.engine.dialect.name, ("mysql", "mariadb"))

    def run_cli(self, command_line):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = self.cli.process_command_line(command_line)
        self.assertFalse(result is None or result is False, "'{}' failed".format(command_line))
        return output.getvalue()

    def add_assignment(self, value, days_ago):
        """A new default assignment of TABLE for runs 0-1000, its created moved days_ago days back"""
        assignment = self.provider.create_assignment([[value] * 3, [value] * 3], TABLE, 0, 1000, "default",
                                                     "mysql tags test")
        created = datetime.now().replace(microsecond=0) - timedelta(days=days_ago)
        self.provider.session.execute(text("UPDATE `assignments` SET `created` = :created WHERE `id` = :id"),
                                      {"created": created, "id": assignment.id})
        self.provider.session.commit()
        self.provider.session.expire_all()
        return self.provider.get_assignment_by_id(assignment.id)

    def two_assignments_and_a_tag_between(self):
        """A created 10 days ago, the tag 5 days ago, B 2 days ago"""
        first = self.add_assignment(111, 10)
        tag = self.provider.create_tag("between", "default", snapshot_time=utc_now() - timedelta(days=5),
                                       comment="between A and B")
        second = self.add_assignment(222, 2)
        self.assertGreater(second.id, first.id)
        return first, second, tag

    def test_tag_between_two_assignments_resolves_to_the_first(self):
        first, second, _ = self.two_assignments_and_a_tag_between()

        self.assertEqual(self.provider.get_assignment_by_request(TABLE + ":{}".format(RUN)).id, second.id)
        self.assertEqual(self.provider.get_assignment_by_request(TABLE + ":{}@between".format(RUN)).id, first.id)
        self.assertEqual(self.provider.get_assignment(TABLE, RUN, "", tag="between").id, first.id)

        output = self.run_cli("cat {}:{}@between".format(TABLE, RUN))
        self.assertIn("111", output)
        self.assertNotIn("222", output)

    def test_tag_before_all_assignments_resolves_to_none(self):
        self.two_assignments_and_a_tag_between()
        earliest = self.provider.session.execute(text("SELECT MIN(`created`) FROM `assignments`")).scalar()
        self.assertGreater(earliest, datetime(2001, 1, 1))
        self.provider.create_tag("too_early", "default", snapshot_time=datetime(2000, 1, 1), comment="before all")

        with self.assertRaises((ObjectIsNotFoundInDbError, NoResultFound)):
            self.provider.get_assignment_by_request(TABLE + ":{}@too_early".format(RUN))
        with self.assertRaises((ObjectIsNotFoundInDbError, NoResultFound)):
            self.provider.get_assignment(TABLE, RUN, "", tag="too_early")

    def test_rm_assignment_pinned_by_a_tag_is_refused_and_forced(self):
        first, second, _ = self.two_assignments_and_a_tag_between()
        self.provider.create_tag("too_early", "default", snapshot_time=datetime(2000, 1, 1), comment="before all")
        self.assertEqual([t.name for t in self.provider.get_pinning_tags(first)], ["between"])
        self.assertEqual(self.provider.get_pinning_tags(second), [])

        with self.assertRaises(ValueError):
            self.provider.delete_assignment(first)
        with mock.patch("builtins.input", return_value="yes"):
            with self.assertRaises(ValueError):
                self.run_cli("rm -a {}".format(first.id))
        self.assertEqual(self.provider.get_assignment_by_id(first.id).id, first.id)

        self.run_cli("rm -a {} -f".format(first.id))
        with self.assertRaises(ObjectIsNotFoundInDbError):
            self.provider.get_assignment_by_id(first.id)

    def test_rm_assignment_newer_than_every_tag(self):
        _, second, _ = self.two_assignments_and_a_tag_between()
        with mock.patch("builtins.input", return_value="yes"):
            self.run_cli("rm -a {}".format(second.id))
        with self.assertRaises(ObjectIsNotFoundInDbError):
            self.provider.get_assignment_by_id(second.id)


if __name__ == '__main__':
    unittest.main()
