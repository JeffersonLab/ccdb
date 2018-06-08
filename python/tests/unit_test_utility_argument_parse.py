import unittest
from ccdb.cmd.utility_argument_parser import UtilityArgumentParser, ArgumentParseError


class UtilityArgumentParserTest(unittest.TestCase):

    def test_exception_thrown(self):
        parser = UtilityArgumentParser()
        parser.add_argument("x")
        self.assertRaises(ArgumentParseError, parser.parse_args, [])

        try:
            parser.parse_args([])
        except Exception as ex:
            self.assertIn("too few", str(ex))
