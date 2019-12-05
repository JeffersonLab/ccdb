import glob
import unittest
import inspect
import os
import tests

test_names = [
    'unit_test_authentication',
    'unit_test_cli_context',
    'unit_test_dump_comments',
    'unit_test_path_utils',
    'unit_test_utility_argument_parse',
    'integ_test_cli_manager',
    'integ_test_provider_sqlite'
]


def get_unit_tests_suite():
    """Searches unit tests (and only unit tests, no integration tests) in this folder"""
    suites = [unittest.defaultTestLoader.loadTestsFromName("tests."+name) for name in test_names]
    for suite in suites:
        print(suite)
    test_suite = unittest.TestSuite(suites)
    return test_suite


def run_unit_tests():
    test_suite = get_unit_tests_suite()
    text_runner = unittest.TextTestRunner().run(test_suite)
    return text_runner


if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
    os.chdir(script_dir)
    run_unit_tests()