"""The build instructions in the install documents agree with the CMake tree.

Checks docs/get-started/installation.md, install.linux.md and cpp/README.md: every `cmake -S DIR` that builds CCDB
names a directory with a CMakeLists.txt, every `-DCCDB_...` option exists as an option() of the CMake project, every
`find_package(ccdb X.Y ...)` asks for a version the project's version satisfies, and every `$CCDB_HOME/...` path
exists in the repository or is something `cmake --install` puts there. Commands that configure the reader's own
project (`-DCMAKE_PREFIX_PATH`) are not CCDB builds and are skipped.

Run from the repository root:  python3 -m unittest discover -s scripts/docs -p 'test_*.py'
"""

import glob
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOCUMENTS = ("docs/get-started/installation.md", "install.linux.md", "cpp/README.md")

# What `cmake --install` with -DCMAKE_INSTALL_PREFIX=$CCDB_HOME adds to the repository directory
INSTALL_PRODUCTS = ("lib", "include", "bin/ccdb_tests")


def read(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as file:
        return file.read()


def code_blocks(text):
    """The text of every fenced code block."""
    return re.findall(r"^```[a-z]*\n(.*?)^```", text, re.MULTILINE | re.DOTALL)


def cmake_options():
    names = set()
    for path in glob.glob(os.path.join(ROOT, "cpp", "**", "CMakeLists.txt"), recursive=True):
        with open(path, encoding="utf-8") as file:
            names.update(re.findall(r"^\s*option\(\s*(\w+)", file.read(), re.MULTILINE))
    return names


def project_version():
    match = re.search(r"^project\(ccdb_main\s+VERSION\s+(\d+)\.(\d+)\.(\d+)\)", read("cpp/CMakeLists.txt"), re.MULTILINE)
    return tuple(int(part) for part in match.groups())


class InstallDocsTest(unittest.TestCase):

    def test_cmake_source_directories(self):
        for document in DOCUMENTS:
            for block in code_blocks(read(document)):
                for line in block.splitlines():
                    match = re.search(r"\bcmake\s+-S\s+(\S+)", line)
                    if not match or "CMAKE_PREFIX_PATH" in line:
                        continue
                    source = match.group(1).replace("$CCDB_HOME", ROOT)
                    with self.subTest(document=document, line=line):
                        self.assertTrue(os.path.isfile(os.path.join(ROOT, source, "CMakeLists.txt")),
                                        "{0} has no CMakeLists.txt".format(source))

    def test_ccdb_options_exist(self):
        options = cmake_options()
        for document in DOCUMENTS:
            for name in set(re.findall(r"\b(CCDB_[A-Z_]+)\b", read(document))):
                if name in ("CCDB_HOME", "CCDB_USER", "CCDB_CONNECTION") or name.startswith(("CCDB_TEST_", "CCDB_MYSQL_", "CCDB_SQLITE_")):
                    continue
                with self.subTest(document=document, option=name):
                    self.assertIn(name, options)

    def test_find_package_version(self):
        major, minor, patch = project_version()
        for document in DOCUMENTS:
            for wanted in re.findall(r"find_package\(ccdb\s+(\d+)\.(\d+)", read(document)):
                with self.subTest(document=document, version=wanted):
                    self.assertEqual(int(wanted[0]), major)
                    self.assertLessEqual(int(wanted[1]), minor)

    def test_ccdb_home_paths(self):
        for document in DOCUMENTS:
            for path in set(re.findall(r"\$CCDB_HOME/([\w./-]+)", read(document))):
                path = path.rstrip(".")
                if path.startswith(INSTALL_PRODUCTS):
                    continue
                with self.subTest(document=document, path=path):
                    self.assertTrue(os.path.exists(os.path.join(ROOT, path)), path)


if __name__ == "__main__":
    unittest.main()
