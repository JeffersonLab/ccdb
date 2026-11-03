"""Version 2.5.0.dev0 (T8 of notes/schema6.md §14; plan D15, Q37).

`ccdb.version.version` becomes `2.5.0.dev0` in PHASE0 item 2, and `version.py` gains
`parse_version(text)` (§14.1, version parser), which returns `(major, minor, patch)` and accepts a
`.devN`, `aN`, `bN`, `rcN` or `.postN` suffix, while `version_tuple` stays three integers. Today
`version.py` parses every dot-part as `int`, so `2.5.0.dev0` would break `import ccdb` (F9).

`parse_version` is looked up inside the test, so the test fails on its own feature until item 2
exists, instead of the whole module failing at import.
"""
import unittest

import ccdb
import ccdb.version

EXPECTED_VERSION = "2.5.0"

# version text -> (major, minor, patch): a release and one case of each suffix §14.1 lists
PARSE_CASES = (
    ("2.5.0.dev0", (2, 5, 0)),
    ("2.5.0", (2, 5, 0)),
    ("2.6.1.dev3", (2, 6, 1)),
    ("2.5.0a1", (2, 5, 0)),
    ("2.5.10b2", (2, 5, 10)),
    ("3.0.0rc1", (3, 0, 0)),
    ("2.4.1.post2", (2, 4, 1)),
)


class VersionV6Test(unittest.TestCase):

    def test_dev_suffix(self):
        """T8, §14 (D15): import ccdb works with version 2.5.0.dev0 and version_tuple == (2, 5, 0)."""
        self.assertEqual(ccdb.version.version, EXPECTED_VERSION)
        self.assertEqual(ccdb.ccdb_version, EXPECTED_VERSION)
        self.assertEqual(ccdb.version.version_tuple, (2, 5, 0))
        self.assertEqual((ccdb.version.major, ccdb.version.minor, ccdb.version.patch), (2, 5, 0))

    def test_parser_reads_dev_suffix(self):
        """T8, §14 (D15), §14.1: parse_version reads a .devN, aN, bN, rcN or .postN suffix into three integers, and a release as before."""
        parse_version = ccdb.version.parse_version
        for version_string, expected in PARSE_CASES:
            with self.subTest(version=version_string):
                self.assertEqual(parse_version(version_string), expected)

        # the module's own tuple is what the parser gives for the installed version
        self.assertEqual(ccdb.version.version_tuple, parse_version(ccdb.version.version))


if __name__ == "__main__":
    unittest.main()
