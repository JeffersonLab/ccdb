import unittest

import ccdb.path_utils


class PathUtilsTest(unittest.TestCase):

    def test_parse_time(self):
        # test of simple parse
        dt = ccdb.path_utils.parse_time("2012-11x13_12-37:55")  # set different symbols as separators
        self.assertEqual(dt.strftime("%Y-%m-%d_%H-%M-%S"), "2012-11-13_12-37-55")

        # test of non full parse
        dt = ccdb.path_utils.parse_time("2012-11x13")   # set different symbols as separators
        self.assertEqual(dt.strftime("%Y-%m-%d_%H-%M-%S"), "2012-11-13_23-59-59")

    def test_parse_year_month(self):
        # test of simple parse
        dt = ccdb.path_utils.parse_time("2012-11")  # set different symbols as separators
        self.assertEqual(dt.strftime("%Y-%m-%d_%H-%M-%S"), "2012-11-30_23-59-59")

    def test_full_parse_request(self):
        # test full request
        result = ccdb.path_utils.parse_request("/test/test_vars/test_table:100:mc:2012-11-13_12:37:55")
        self.assertTrue(result.path_is_parsed)
        self.assertEqual(result.path, "/test/test_vars/test_table")
        self.assertTrue(result.run_is_parsed)
        self.assertEqual(result.run, 100)
        self.assertTrue(result.variation_is_parsed)
        self.assertEqual(result.variation, "mc")
        self.assertTrue(result.time_is_parsed)
        self.assertEqual(result.time_str, "2012-11-13_12:37:55")
        self.assertEqual(result.time.strftime("%Y-%m-%d_%H-%M-%S"), "2012-11-13_12-37-55")

    def test_partial1_parse_request(self):
        # test full request
        result = ccdb.path_utils.parse_request("/test/test_vars/test_table")
        self.assertTrue(result.path_is_parsed)
        self.assertEqual(result.path, "/test/test_vars/test_table")
        self.assertFalse(result.run_is_parsed)
        self.assertFalse(result.variation_is_parsed)
        self.assertFalse(result.time_is_parsed)

    def test_partial2_parse_request(self):
        # test full request
        result = ccdb.path_utils.parse_request("/test/test_vars/test_table::mc")
        self.assertTrue(result.path_is_parsed)
        self.assertEqual(result.path, "/test/test_vars/test_table")
        self.assertFalse(result.run_is_parsed)
        self.assertTrue(result.variation_is_parsed)
        self.assertEqual(result.variation, "mc")
        self.assertFalse(result.time_is_parsed)

    def test_validate_name(self):
        """ Checks if name is valid ccdb object name """
        self.assertTrue(ccdb.path_utils.validate_name("this_is_variation2"))
        self.assertFalse(ccdb.path_utils.validate_name("this-is_variation2"))
        self.assertFalse(ccdb.path_utils.validate_name("this:isvariation2"))


class FormatRequestTimeTest(unittest.TestCase):
    """format_request_time renders local wall time, whatever the datetime it gets (F34)"""

    def test_naive_local_time_as_is(self):
        import datetime
        from ccdb.path_utils import format_request_time
        self.assertEqual(format_request_time(datetime.datetime(2026, 3, 1, 12, 30, 15)), "2026-03-01_12-30-15")
        self.assertEqual(format_request_time(datetime.datetime(2026, 3, 1, 12, 30, 15, 820564)),
                         "2026-03-01_12-30-15.820564")

    def test_aware_utc_time_becomes_local(self):
        import datetime
        from ccdb.path_utils import format_request_time, utc_to_local
        instant = datetime.datetime(2026, 11, 3, 16, 3, 33, 820564, tzinfo=datetime.timezone.utc)
        self.assertEqual(format_request_time(instant), format_request_time(utc_to_local(instant)))
        offset = instant.astimezone().utcoffset()
        if offset:    # the zone of this process is not UTC: the rendered hour differs from the UTC hour
            self.assertNotEqual(format_request_time(instant), "2026-11-03_16-03-33.820564")

