"""
Tags: create, list, show and remove; requests with '@NAME'; resolution by the tag variation and time;
the rm -a refusal while a tag may resolve to the assignment.

The tests pin the process time zone to UTC: they compare against literal times, and a tag stores a UTC
instant while SQLite assignments hold local time.
"""

import contextlib
import io
import os
import time
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

import ccdb
import ccdb.cmd.themes
from ccdb import testing as helper
from ccdb.cmd.cli_manager import CliManager, CCDB_EXCEPTIONS_THROW
from ccdb.errors import ObjectIsNotFoundInDbError
from ccdb.model import LogRecord, Tag
from ccdb.path_utils import parse_request

TABLE = "/test/test_vars/test_table"
RUN = 100


def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class TimeZonePinned(unittest.TestCase):
    def setUp(self):
        saved_tz = os.environ.get('TZ')

        def restore_tz():
            if saved_tz is None:
                os.environ.pop('TZ', None)
            else:
                os.environ['TZ'] = saved_tz
            time.tzset()

        self.addCleanup(restore_tz)
        os.environ['TZ'] = 'UTC'
        time.tzset()


class ParseRequestTagTest(unittest.TestCase):

    def test_tag_after_run(self):
        request = parse_request("/a/b/table:1000@mytag")
        self.assertEqual(request.path, "/a/b/table")
        self.assertTrue(request.run_is_parsed)
        self.assertEqual(request.run, 1000)
        self.assertTrue(request.tag_is_parsed)
        self.assertEqual(request.tag, "mytag")
        self.assertFalse(request.variation_is_parsed)
        self.assertFalse(request.time_is_parsed)

    def test_tag_after_path(self):
        request = parse_request("/a/b/table@mytag")
        self.assertEqual(request.path, "/a/b/table")
        self.assertFalse(request.run_is_parsed)
        self.assertEqual(request.tag, "mytag")

    def test_no_tag(self):
        request = parse_request("/a/b/table:1000:mc")
        self.assertFalse(request.tag_is_parsed)
        self.assertEqual(request.tag, "")

    def test_empty_variation_part_is_no_variation(self):
        request = parse_request("/a/b/table:1000:@mytag")
        self.assertEqual(request.tag, "mytag")
        self.assertFalse(request.variation_is_parsed)

    def test_tag_and_variation_is_an_error(self):
        with self.assertRaises(ValueError):
            parse_request("/a/b/table:1000:mc@mytag")

    def test_tag_and_time_is_an_error(self):
        with self.assertRaises(ValueError):
            parse_request("/a/b/table:1000::2012-08@mytag")
        with self.assertRaises(ValueError):
            parse_request("/a/b/table:::2012@mytag")

    def test_invalid_tag_name_is_an_error(self):
        with self.assertRaises(ValueError):
            parse_request("/a/b/table@")
        with self.assertRaises(ValueError):
            parse_request("/a/b/table@my-tag")
        with self.assertRaises(ValueError):
            parse_request("/a/b/table@t\u00e4g")


class TagsTest(TimeZonePinned):

    def setUp(self):
        super().setUp()
        helper.recreate_test_sqlite_db()
        self.addCleanup(helper.clean_test_sqlite_db)

        self.cli = CliManager()
        self.cli.exception_handling = CCDB_EXCEPTIONS_THROW
        self.cli.force_exceptions = True
        self.cli.theme = ccdb.cmd.themes.NoColorTheme()
        self.cli.connection_string = helper.sqlite_test_connection_str
        self.cli.context.user_name = "test_user"
        self.cli.register_utilities()
        self.addCleanup(self.cli.provider.disconnect)
        with contextlib.redirect_stdout(io.StringIO()):
            self.cli.process_command_line("ls /")       # the CLI connects on its first database command
        self.provider = self.cli.provider
        self.provider.logging_enabled = True

    def run_cli(self, command_line):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = self.cli.process_command_line(command_line)
        self.assertFalse(result is None or result is False, "'{}' failed".format(command_line))
        return output.getvalue()

    def add_assignment(self, variation="default", value=777):
        return self.provider.create_assignment([[value, value, value], [value, value, value]], TABLE, 0, 1000,
                                               variation, "tags test")

    def log_records_of(self, tag_id):
        return self.provider.session.query(LogRecord) \
            .filter(LogRecord.affected_ids == "|tags{}|".format(tag_id)).order_by(LogRecord.id).all()

    # resolution
    def test_tag_made_before_a_new_assignment_resolves_to_the_old_one(self):
        old = self.provider.get_assignment(TABLE, RUN, "default")
        self.provider.create_tag("before_new", "default", comment="before the new data")
        new = self.add_assignment()
        self.assertNotEqual(old.id, new.id)

        self.assertEqual(self.provider.get_assignment_by_request(TABLE + ":{}".format(RUN)).id, new.id)
        self.assertEqual(self.provider.get_assignment_by_request(TABLE + ":{}@before_new".format(RUN)).id, old.id)
        self.assertEqual(self.provider.get_assignment(TABLE, RUN, "", tag="before_new").id, old.id)

        self.assertIn("777", self.run_cli("cat {}:{}".format(TABLE, RUN)))
        self.assertNotIn("777", self.run_cli("cat {}:{}@before_new".format(TABLE, RUN)))
        self.assertNotIn("777", self.run_cli("dump {}:{}@before_new".format(TABLE, RUN)))
        output = self.run_cli("vers {}@before_new".format(TABLE))
        self.assertIn(str(old.id), output)
        self.assertNotIn(" {} ".format(new.id), output.replace("(", " ").replace(")", " "))
        output = self.run_cli("info {}@before_new".format(TABLE))
        self.assertIn("before_new", output)
        self.assertIn("test_table", output)

    def test_past_time_tag(self):
        moment = datetime(2012, 9, 1)
        expected = self.provider.get_assignment(TABLE, RUN, "default", moment)
        latest = self.provider.get_assignment(TABLE, RUN, "default")
        self.assertNotEqual(expected.id, latest.id)

        self.run_cli('tag past -t 2012-09-01-00-00-00 -c "September 2012"')
        tag = self.provider.get_tag("past")
        self.assertEqual(tag.snapshot_time, moment)        # TZ is UTC, so local time is the UTC instant

        self.assertEqual(self.provider.get_assignment_by_request(TABLE + ":{}@past".format(RUN)).id, expected.id)

    def test_tag_follows_its_variation_tree(self):
        expected = self.provider.get_assignment(TABLE, RUN, "subtest")
        self.provider.create_tag("sub", "subtest", comment="subtest")
        self.add_assignment("default")
        self.assertEqual(self.provider.get_assignment_by_request(TABLE + ":{}@sub".format(RUN)).id, expected.id)

    def test_vers_with_tag_lists_the_parent_variations_as_cat_resolves(self):
        # 'leaf' has no data of its own: a request with the tag resolves in its parent, default
        self.provider.create_variation("leaf", "no data of its own", "default")
        self.provider.create_tag("on_leaf", "leaf", comment="tag of a variation without data")
        resolved = self.provider.get_assignment_by_request(TABLE + ":{}@on_leaf".format(RUN))
        self.assertEqual(resolved.variation.name, "default")
        default_ids = [a.id for a in self.provider.get_assignments(TABLE, variation="default")]

        listed = self.provider.get_assignments(TABLE, tag="on_leaf")
        self.assertEqual(sorted(a.id for a in listed), sorted(default_ids))
        output = self.run_cli("vers {}@on_leaf".format(TABLE))
        self.assertIn(" {} ".format(resolved.id), output)
        self.assertIn("leaf -> default", output)
        # the tag time still applies
        newer = self.add_assignment("default")
        self.assertNotIn(newer.id, [a.id for a in self.provider.get_assignments(TABLE, tag="on_leaf")])

    def test_vers_with_tag_on_a_second_level_variation_lists_the_whole_tree(self):
        self.provider.create_tag("sub", "subtest", comment="subtest")
        names = {a.variation.name for a in self.provider.get_assignments(TABLE, tag="sub")}
        expected = {a.variation.name for a in self.provider.get_assignments(TABLE)} & {"subtest", "test", "default"}
        self.assertEqual(names, expected)
        self.assertIn("subtest -> test -> default", self.run_cli("vers {}@sub".format(TABLE)))

    def test_request_with_tag_and_variation_or_time_is_an_error(self):
        self.provider.create_tag("t", "default", comment="t")
        with self.assertRaises(ValueError):
            self.provider.get_assignment_by_request(TABLE + ":100:mc@t")
        with self.assertRaises(ValueError):
            self.run_cli("cat {}@t -v mc".format(TABLE))
        with self.assertRaises(ValueError):
            self.run_cli("cat {}@t -t 2012".format(TABLE))
        with self.assertRaises(ValueError):
            self.run_cli("vers {}@t -v mc".format(TABLE))

    def test_unknown_tag(self):
        with self.assertRaises(ObjectIsNotFoundInDbError):
            self.provider.get_assignment_by_request(TABLE + "@nosuch")

    def test_working_variation_does_not_apply_to_a_tag(self):
        old = self.provider.get_assignment(TABLE, RUN, "default")
        self.provider.create_tag("t", "default", comment="t")
        self.add_assignment()
        self.cli.context.current_variation = "mc"
        self.run_cli("cat {}:{}@t".format(TABLE, RUN))
        self.assertEqual(self.provider.get_assignment_by_request(TABLE + ":{}@t".format(RUN)).id, old.id)

    # create, list, show, remove
    def test_tag_create_list_show_rm_with_log_records(self):
        self.run_cli('tag v1 -c "First tag"')
        tag = self.provider.get_tag("v1")
        self.assertEqual(self.provider.get_tag_variation(tag).name, "default")
        self.assertLessEqual(abs((utc_now() - tag.snapshot_time).total_seconds()), 60)
        records = self.log_records_of(tag.id)
        self.assertEqual([r.action for r in records], ["create"])
        self.assertIn("v1", records[0].description)

        self.run_cli('tag v2 -v mc -c "Second tag"')
        self.assertEqual(self.provider.get_tag_variation(self.provider.get_tag("v2")).name, "mc")

        output = self.run_cli("tag")
        self.assertIn("v1", output)
        self.assertIn("v2", output)
        self.assertIn("Second tag", output)

        output = self.run_cli("tag v2")
        self.assertIn("v2", output)
        self.assertIn("mc", output)
        self.assertIn("Second tag", output)

        tag_id = self.provider.get_tag("v1").id
        self.run_cli("tag rm v1")
        with self.assertRaises(ObjectIsNotFoundInDbError):
            self.provider.get_tag("v1")
        self.assertEqual([r.action for r in self.log_records_of(tag_id)], ["create", "delete"])

    def test_tag_needs_a_comment(self):
        with self.assertRaises(ValueError):
            self.run_cli("tag v1 -v mc")
        self.assertEqual(self.provider.session.query(Tag).count(), 0)

    def test_duplicate_and_invalid_names_are_refused(self):
        self.provider.create_tag("v1", comment="x")
        with self.assertRaises(ValueError):
            self.provider.create_tag("v1", comment="y")
        with self.assertRaises(ValueError):
            self.provider.create_tag("bad-name", comment="y")
        with self.assertRaises(ValueError):
            self.provider.create_tag("a" * 101, comment="y")

    def test_future_time_is_refused(self):
        with self.assertRaises(ValueError):
            self.provider.create_tag("future", snapshot_time=utc_now() + timedelta(days=1), comment="x")
        with self.assertRaises(ValueError):
            self.run_cli('tag future -t 2137 -c "far away"')
        self.assertEqual(self.provider.session.query(Tag).count(), 0)

    def test_partial_date_of_today_is_refused_as_its_last_second(self):
        today = datetime.now().strftime("%Y-%m-%d")        # TZ is UTC
        with self.assertRaises(ValueError) as context:
            self.run_cli('tag today -t {} -c "today"'.format(today))
        self.assertIn("-t {0} means {0} 23:59:59".format(today), str(context.exception))
        self.assertEqual(self.provider.session.query(Tag).count(), 0)

    def test_aware_time_is_stored_as_utc(self):
        moment = datetime(2012, 9, 1, 12, 0, 0, tzinfo=timezone(timedelta(hours=-4)))
        tag = self.provider.create_tag("aware", snapshot_time=moment, comment="x")
        self.assertEqual(tag.snapshot_time, datetime(2012, 9, 1, 16, 0, 0))

    # rm -a
    def test_rm_assignment_pinned_by_a_tag_is_refused_and_forced(self):
        assignment = self.add_assignment()
        self.provider.create_tag("pin", "default", comment="pins it")

        with self.assertRaises(ValueError):
            self.provider.delete_assignment(assignment)
        with mock.patch("builtins.input", return_value="yes"):
            with self.assertRaises(ValueError):
                self.run_cli("rm -a {}".format(assignment.id))
        self.assertEqual(self.provider.get_assignment_by_id(assignment.id).id, assignment.id)

        self.run_cli("rm -a {} -f".format(assignment.id))
        with self.assertRaises(ObjectIsNotFoundInDbError):
            self.provider.get_assignment_by_id(assignment.id)

    def test_rm_assignment_pinned_by_a_tag_of_a_child_variation(self):
        assignment = self.add_assignment("default")
        self.provider.create_tag("pin_mc", "mc", comment="mc inherits from default")
        self.assertEqual([t.name for t in self.provider.get_pinning_tags(assignment)], ["pin_mc"])
        with self.assertRaises(ValueError):
            self.provider.delete_assignment(assignment)

    def test_rm_assignment_not_pinned(self):
        # a tag older than the assignment, and a tag of a variation that does not inherit from it
        self.provider.create_tag("old", "default", snapshot_time=datetime(2012, 1, 1), comment="old")
        assignment = self.add_assignment("test")
        self.provider.create_tag("other", "mc", comment="mc does not inherit from test")
        self.assertEqual(self.provider.get_pinning_tags(assignment), [])
        with mock.patch("builtins.input", return_value="yes"):
            self.run_cli("rm -a {}".format(assignment.id))
        with self.assertRaises(ObjectIsNotFoundInDbError):
            self.provider.get_assignment_by_id(assignment.id)


    def test_non_ascii_tag_name_is_refused(self):
        with self.assertRaises(ValueError):
            self.provider.create_tag("t\u00e4g", comment="y")

    def test_failed_log_record_rolls_back_the_tag(self):
        with mock.patch.object(self.provider, "create_log_record", side_effect=RuntimeError("log failed")):
            with self.assertRaises(RuntimeError):
                self.provider.create_tag("v1", comment="x")
        self.assertEqual(self.provider.session.query(Tag).count(), 0)

    def test_delete_variation_with_tags_is_refused(self):
        variation = self.provider.create_variation("tagged", "for the tag", "default")
        self.provider.create_tag("v1", variation, comment="x")
        with self.assertRaises(ValueError) as context:
            self.provider.delete_variation(variation)
        self.assertIn("v1", str(context.exception))

    def test_tag_list_with_a_missing_variation(self):
        self.provider.create_tag("v1", comment="x")
        with mock.patch.object(self.provider, "get_tag_variation",
                               side_effect=ObjectIsNotFoundInDbError(ccdb.model.Variation, "gone")):
            output = self.run_cli("tag")
        self.assertIn("<deleted>", output)


if __name__ == '__main__':
    unittest.main()
