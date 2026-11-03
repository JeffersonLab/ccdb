"""The CLI-like API page (docs/apis/python-cli-like.md) shows python/examples/example_cli_like_api.py as it is.

The example runs in CI (python-examples.yml), so the page's code is code that works (issue #98).

Run from the repository root:  python3 -m unittest discover -s scripts/docs -p 'test_*.py'
"""

import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def read(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as file:
        return file.read()


class CliLikeDocsTest(unittest.TestCase):

    def test_page_block_equals_the_example(self):
        page = read("docs/apis/python-cli-like.md")
        block = re.search(r"example_cli_like_api.py: begin.*?\n```python\n(.*?)```\n<!-- example_cli_like_api.py: end",
                          page, re.DOTALL)
        self.assertIsNotNone(block, "the example block markers are missing from the page")
        example = read("python/examples/example_cli_like_api.py")
        code = example.split('"""', 2)[2].lstrip("\n")
        self.assertEqual(block.group(1), code)

    def test_example_runs_in_ci(self):
        self.assertIn("examples/example_cli_like_api.py", read(".github/workflows/python-examples.yml"))


if __name__ == "__main__":
    unittest.main()
