"""docs/cli.md shows the property vocabulary that ccdb.vocabulary defines (vocabulary_table.py --check)"""
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))


class VocabularyTableTest(unittest.TestCase):

    def test_the_page_matches_the_code(self):
        run = subprocess.run([sys.executable, os.path.join(HERE, "vocabulary_table.py"), "--check"],
                             capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)


if __name__ == "__main__":
    unittest.main()
