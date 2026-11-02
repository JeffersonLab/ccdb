"""The repository's license and citation files (PHASE3 item 1; plan D14) and the C++ package version (item 2).

`COPYING.LESSER` carries the LGPL version 3 text and `COPYING` the GPL version 3 text it supplements; `CITATION.cff` and `.zenodo.json` describe the software for GitHub's
"Cite this repository" and for Zenodo. The license they state must be the one `pyproject.toml` declares, and the
version in `CITATION.cff` must be `ccdb.version.version`, so a release that bumps one without the other fails here.
The C++ library's CMake package (`find_package(ccdb 2.5 CONFIG)`) takes its version from `project(... VERSION)` in
`cpp/CMakeLists.txt`, which must be the release `ccdb.version.version_tuple` names.
The files live at the repository root, two levels above this directory; the tests run from a checkout.
"""
import json
import os
import re
import unittest

import yaml

import ccdb.version

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def read_text(name):
    with open(os.path.join(ROOT, name), encoding="utf-8") as file:
        return file.read()


def pyproject_license():
    match = re.search(r'^license\s*=\s*"([^"]+)"', read_text("pyproject.toml"), re.MULTILINE)
    return match.group(1)


class MetadataFilesTest(unittest.TestCase):

    def test_files_exist(self):
        for name in ("COPYING", "COPYING.LESSER", "CITATION.cff", ".zenodo.json"):
            self.assertTrue(os.path.isfile(os.path.join(ROOT, name)), name)

    def test_license_is_lgpl_3(self):
        head = read_text("COPYING.LESSER")[:200].split()
        self.assertEqual(head[:8], ["GNU", "LESSER", "GENERAL", "PUBLIC", "LICENSE", "Version", "3,", "29"])
        head = read_text("COPYING")[:200].split()
        self.assertEqual(head[:7], ["GNU", "GENERAL", "PUBLIC", "LICENSE", "Version", "3,", "29"])
        self.assertEqual(pyproject_license(), "LGPL-3.0-or-later")

    def test_citation_parses_and_agrees(self):
        citation = yaml.safe_load(read_text("CITATION.cff"))
        for key in ("cff-version", "message", "title", "authors"):
            self.assertIn(key, citation)
        self.assertEqual(citation["cff-version"], "1.2.0")
        self.assertEqual(str(citation["version"]), ccdb.version.version)
        self.assertEqual(citation["license"], pyproject_license())
        self.assertEqual(citation["repository-code"], "https://github.com/JeffersonLab/ccdb")
        for author in citation["authors"]:
            self.assertTrue(author.get("family-names") and author.get("given-names"), author)

    def test_zenodo_agrees_with_citation(self):
        zenodo = json.loads(read_text(".zenodo.json"))
        citation = yaml.safe_load(read_text("CITATION.cff"))
        self.assertEqual(zenodo["upload_type"], "software")
        self.assertEqual(zenodo["title"], citation["title"])
        self.assertEqual(zenodo["license"], citation["license"])
        self.assertEqual([creator["name"] for creator in zenodo["creators"]],
                         ["{0}, {1}".format(author["family-names"], author["given-names"]) for author in citation["authors"]])

    def test_cpp_package_version(self):
        match = re.search(r"^project\(ccdb_main\s+VERSION\s+(\d+)\.(\d+)\.(\d+)\)", read_text("cpp/CMakeLists.txt"), re.MULTILINE)
        self.assertIsNotNone(match, "cpp/CMakeLists.txt names no project version")
        self.assertEqual(tuple(int(part) for part in match.groups()), ccdb.version.version_tuple)


if __name__ == '__main__':
    unittest.main()
