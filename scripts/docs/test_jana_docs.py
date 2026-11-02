"""The JANA2 service page (docs/apis/jana.md) agrees with the service's code.

Every parameter CCDB_service declares (SetDefaultParameter("ccdb:...") in jana2/src/CCDB_service.cc) is a row of
the page's parameter table, and the table names no parameter the service does not declare. The plugin and the CMake
component the page tells the reader to use exist in jana2/CMakeLists.txt and cpp/cmake/ccdbConfig.cmake.in.

Run from the repository root:  python3 -m unittest discover -s scripts/docs -p 'test_*.py'
"""

import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def read(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as file:
        return file.read()


class JanaDocsTest(unittest.TestCase):

    def setUp(self):
        self.page = read("docs/apis/jana.md")

    def test_parameter_table_matches_the_service(self):
        declared = set(re.findall(r'SetDefaultParameter\(\s*"(ccdb:\w+)"', read("jana2/src/CCDB_service.cc")))
        self.assertTrue(declared, "no ccdb: parameters found in CCDB_service.cc")
        documented = set(re.findall(r"^\| `(ccdb:\w+)` \|", self.page, re.MULTILINE))
        self.assertEqual(documented, declared)

    def test_plugin_and_component_exist(self):
        self.assertIn("-Pplugins=CCDB_service", self.page)
        self.assertIn("add_library(CCDB_service ", read("jana2/CMakeLists.txt"))
        self.assertIn("COMPONENTS jana2", self.page)
        self.assertIn('_ccdb_component STREQUAL "jana2"', read("cpp/cmake/ccdbConfig.cmake.in"))
        self.assertIn("ccdb::ccdb_jana2", self.page)
        self.assertIn("add_library(ccdb::ccdb_jana2 ALIAS ccdb_jana2)", read("jana2/CMakeLists.txt"))


if __name__ == "__main__":
    unittest.main()
