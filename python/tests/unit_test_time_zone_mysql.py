"""
MySQL and MariaDB session time zone: the provider sets it to UTC, and the model's UTC columns send and receive UTC
(docs/concepts/time.md), so the creation time it writes is the true instant, with microseconds, even when the client
and the server are in different zones; Python reads it back as the client's local wall time.

The process time zone is pinned to America/New_York, or to Asia/Tokyo when the server's own offset is New York's,
so the two always differ. Runs on the database of CCDB_TEST_MYSQL_CONNECTION, re-initialized before each test;
skipped when the variable is unset.
"""

import contextlib
import io
import os
import time
import unittest
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from ccdb import testing as helper
from ccdb.provider import AlchemyProvider

TABLE = "/test/test_vars/test_table"
RUN = 100


def set_process_time_zone(name):
    if name is None:
        os.environ.pop("TZ", None)
    else:
        os.environ["TZ"] = name
    time.tzset()


@unittest.skipUnless(helper.ENV_TEST_MYSQL in os.environ, "{} is not set".format(helper.ENV_TEST_MYSQL))
@unittest.skipUnless(hasattr(time, "tzset"), "time.tzset is not available")
class MySqlSessionTimeZoneTest(unittest.TestCase):

    def setUp(self):
        connection_str = os.environ[helper.ENV_TEST_MYSQL]
        with contextlib.redirect_stdout(io.StringIO()):
            helper.recreate_mysql_db(connection_str)
        self.addCleanup(self.restore_database, connection_str)

        self.addCleanup(set_process_time_zone, os.environ.get("TZ"))
        set_process_time_zone("America/New_York")

        self.provider = AlchemyProvider()
        self.provider.connect(connection_str)
        self.addCleanup(self.provider.disconnect)
        self.provider.authentication.current_user_name = "test_user"

        # the server's own offset: NOW() runs in the session zone, which is the client's
        server_offset = self.scalar("SELECT TIMESTAMPDIFF(MINUTE, UTC_TIMESTAMP(), "
                                    "CONVERT_TZ(NOW(), @@session.time_zone, @@global.time_zone))")
        if server_offset in (-time.timezone // 60, -time.altzone // 60):
            set_process_time_zone("Asia/Tokyo")
            self.provider.session.rollback()        # the next checkout takes the new offset

    @staticmethod
    def restore_database(connection_str):
        with contextlib.redirect_stdout(io.StringIO()):
            helper.recreate_mysql_db(connection_str)

    def scalar(self, sql, **params):
        return self.provider.session.execute(text(sql), params).scalar()

    def new_assignment(self, value):
        return self.provider.create_assignment([[value] * 3, [value] * 3], TABLE, 0, 1000, "default", "tz test")

    def test_session_time_zone_is_utc(self):
        self.assertEqual(self.scalar("SELECT @@session.time_zone"), "+00:00")

    def test_created_is_the_true_instant(self):
        before = time.time()
        assignment = self.new_assignment(111)
        after = time.time()
        epoch = self.scalar("SELECT UNIX_TIMESTAMP(`created`) FROM `assignments` WHERE `id` = :id", id=assignment.id)
        self.assertGreaterEqual(float(epoch), int(before) - 1)
        self.assertLessEqual(float(epoch), after + 1)

        # read back, it is the client's local time again, with the microseconds the server kept
        self.provider.session.expire_all()
        created = self.provider.get_assignment_by_id(assignment.id).created
        self.assertLess(abs((created - datetime.now()).total_seconds()), 60)
        stored = self.scalar("SELECT `created` FROM `assignments` WHERE `id` = :id", id=assignment.id)
        self.assertEqual(stored.microsecond, created.microsecond)
        self.assertEqual(self.scalar("SELECT DATETIME_PRECISION FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = "
                                     "DATABASE() AND TABLE_NAME = 'assignments' AND COLUMN_NAME = 'created'"), 6)

    def test_tag_and_request_time_before_a_new_assignment_do_not_see_it(self):
        old = self.new_assignment(111)
        hour_ago_utc = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1)
        self.provider.session.execute(text("UPDATE `assignments` SET `created` = :created WHERE `id` = :id"),
                                      {"created": datetime.now() - timedelta(days=2), "id": old.id})
        self.provider.session.commit()
        new = self.new_assignment(222)
        self.provider.create_tag("hour_ago", "default", snapshot_time=hour_ago_utc, comment="before the new one")

        self.assertEqual(self.provider.get_assignment(TABLE, RUN, "default").id, new.id)
        self.assertEqual(self.provider.get_assignment(TABLE, RUN, "", tag="hour_ago").id, old.id)
        hour_ago_local = datetime.now() - timedelta(hours=1)
        self.assertEqual(self.provider.get_assignment(TABLE, RUN, "default", date_and_time=hour_ago_local).id, old.id)

    def test_schema_commands_keep_the_server_time_zone(self):
        schema_provider = AlchemyProvider()
        schema_provider.connect(os.environ[helper.ENV_TEST_MYSQL], client_time_zone=False)
        self.addCleanup(schema_provider.disconnect)
        zones = schema_provider.session.execute(text("SELECT @@session.time_zone, @@global.time_zone")).one()
        self.assertEqual(zones[0], zones[1])


if __name__ == '__main__':
    unittest.main()
