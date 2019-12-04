import unittest
import os
from ccdb.cmd import CliContext


class CliContextTest(unittest.TestCase):

    def setUp(self):
        pass

    def test_prepare_path(self):
        context = CliContext()
        context.current_path = '/cat'
        result = context.prepare_path('mew/')
        self.assertEqual(result, '/cat/mew')

    def test_prepare_abs_path(self):
        context = CliContext()
        context.current_path = '/cat'
        result = context.prepare_path('/dog/bark/')
        self.assertEqual(result, '/dog/bark')
