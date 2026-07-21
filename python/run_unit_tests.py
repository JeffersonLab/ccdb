import unittest
import os
from ccdb import testing as ccdb_testing

test_names = [
    'unit_test_authentication',
    'unit_test_exceptions',
    'unit_test_cli_context',
    'unit_test_dump_comments',
    'unit_test_path_utils',
    'unit_test_utility_argument_parse',
    'unit_test_version',
    'integ_test_cli_manager',
    'integ_test_provider_sqlite',
    'integ_test_provider_mysql'
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

    if ccdb_testing.ENV_TEST_MYSQL not in os.environ:
        print(f"(!)WARNING(!) TESTS Mysql Connection string is not set in {ccdb_testing.ENV_TEST_MYSQL}")
        print(f"Using default: {ccdb_testing.mysql_test_connection_str}")

    if ccdb_testing.ENV_TEST_SQLITE not in os.environ:
        print(f"(!)WARNING(!) TESTS SQLite Connection string is not set in {ccdb_testing.ENV_TEST_SQLITE}")
        print(f"Using default: {ccdb_testing.sqlite_test_file_path}")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    unit_test_dir = os.path.join(script_dir, "tests")
    os.chdir(unit_test_dir)
    result = run_unit_tests()
    exit(len(result.failures))
