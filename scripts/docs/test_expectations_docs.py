"""The analysis page (docs/apis/analysis.md) shows python/examples/example_expectations_parquet.py as it is, and CI
runs the example (python-examples.yml), so the page's suite is a suite that passes.

Run from the repository root:  python3 -m unittest discover -s scripts/docs -p 'test_*.py'
"""
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def read(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as file:
        return file.read()


class ExpectationsDocsTest(unittest.TestCase):

    def test_page_block_equals_the_example(self):
        page = read("docs/apis/analysis.md")
        block = re.search(r"example_expectations_parquet.py: begin -->\n```python\n(.*?)```\n<!-- example_expectations_parquet.py: end",
                          page, re.DOTALL)
        self.assertIsNotNone(block, "the example block markers are missing from the page")
        example = read("python/examples/example_expectations_parquet.py")
        self.assertEqual(block.group(1), example.split('"""', 2)[2].lstrip("\n"))

    def test_example_runs_in_ci(self):
        self.assertIn("examples/example_expectations_parquet.py", read(".github/workflows/python-examples.yml"))


if __name__ == "__main__":
    unittest.main()
