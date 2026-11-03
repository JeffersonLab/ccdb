"""The time parser of the schema 6 time model (docs/concepts/time.md) against testdata/time/parse_cases.tsv,
the case table the C++ test test_TimeParse.cc runs too: both languages must give the same UTC instant for every
input and zone, or both must refuse it. Also the local and UTC conversions of ccdb.path_utils."""
import os
import time
import unittest
from datetime import datetime, timezone

from ccdb import path_utils

CASES = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                     "testdata", "time", "parse_cases.tsv")


def read_cases():
    with open(CASES, encoding="utf-8") as file:
        return [line.rstrip("\n").split("\t") for line in file if line.strip() and not line.startswith("#")]


def set_process_time_zone(name):
    if name is None:
        os.environ.pop("TZ", None)
    else:
        os.environ["TZ"] = name
    time.tzset()


@unittest.skipUnless(hasattr(time, "tzset"), "time.tzset is not available")
class TimeParseTest(unittest.TestCase):

    def setUp(self):
        self.addCleanup(set_process_time_zone, os.environ.get("TZ"))

    def test_shared_cases(self):
        cases = read_cases()
        self.assertGreater(len(cases), 50)
        for zone, text, expected in cases:
            with self.subTest(zone=zone, text=text):
                set_process_time_zone(zone)
                try:
                    got = path_utils.local_to_utc(path_utils.parse_time(text)).strftime("%Y-%m-%d %H:%M:%S.%f")
                except ValueError:
                    got = "ERROR"
                self.assertEqual(got, expected)

    def test_minimum_mode_pads_with_zeros(self):
        self.assertEqual(path_utils.parse_time("2024-02", max_time_by_default=False), datetime(2024, 2, 1))
        self.assertEqual(path_utils.parse_time("2024-02-03 04:05:06.7", max_time_by_default=False),
                         datetime(2024, 2, 3, 4, 5, 6, 700000))

    def test_round_trip_through_the_repeated_hour(self):
        set_process_time_zone("America/New_York")
        # 2024-11-03 01:30 happens twice: 05:30 UTC (EDT) and 06:30 UTC (EST)
        for utc in (datetime(2024, 11, 3, 5, 30, 0, 123456, tzinfo=timezone.utc),
                    datetime(2024, 11, 3, 6, 30, 0, 123456, tzinfo=timezone.utc)):
            local = path_utils.utc_to_local(utc)
            self.assertEqual(local.replace(fold=0), datetime(2024, 11, 3, 1, 30, 0, 123456))
            self.assertEqual(path_utils.local_to_utc(local), utc)
        # a naive UTC value is read as UTC
        self.assertEqual(path_utils.utc_to_local(datetime(2024, 6, 1, 16, 0)), datetime(2024, 6, 1, 12, 0))

    def test_request_time_has_microseconds(self):
        set_process_time_zone("UTC")
        request = path_utils.parse_request("/test/table:100:default:2024-03-01 12:30:15.25")
        self.assertTrue(request.time_is_parsed)
        self.assertEqual(request.time, datetime(2024, 3, 1, 12, 30, 15, 259999))


if __name__ == '__main__':
    unittest.main()
