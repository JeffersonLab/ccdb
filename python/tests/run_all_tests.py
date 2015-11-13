import glob
import unittest
import inspect
import os

dir_backup = os.getcwd()
script_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
dir_changed = False

if dir_backup != script_dir:
    os.chdir(script_dir)
    dir_changed = True

try:
    test_file_strings = glob.glob('test_*.py')
    module_strings = [module_string[0:len(module_string)-3] for module_string in test_file_strings]

    suites = [unittest.defaultTestLoader.loadTestsFromName(module_string) for module_string in module_strings]
    testSuite = unittest.TestSuite(suites)
    text_runner = unittest.TextTestRunner().run(testSuite)

finally:
    if dir_changed: os.chdir(dir_backup)

