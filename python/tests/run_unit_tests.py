import glob
import unittest
import inspect
import os


script_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
os.chdir(script_dir)
test_file_strings = glob.glob('unit_test_*.py')
module_strings = [module_string[0:len(module_string)-3] for module_string in test_file_strings]

suites = [unittest.defaultTestLoader.loadTestsFromName(module_string) for module_string in module_strings]
for suite in suites:
    print (suite)
testSuite = unittest.TestSuite(suites)
text_runner = unittest.TextTestRunner().run(testSuite)


