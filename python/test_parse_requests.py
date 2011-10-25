import random
import unittest
import ccdb.PathUtils as PathUtils
import time

class TestParseRequest(unittest.TestCase):

    def setUp(self):
        self.seq = range(10)
        
    def test_parse_partial_time(self):
        result = time.localtime(PathUtils.parse_time("2029"))

        self.assertIsNotNone(result)        
        self.assertIsInstance(result, time.struct_time)
        self.assertEqual(result.tm_year, 2029)
        
        
        

    def test_parse_simple_request(self):
        result= PathUtils.parse_request("/my/value");

        self.assertTrue(result.Path == "/my/value")
        self.assertTrue(result.WasParsedPath)
        self.assertFalse(result.WasParsedRunNumber)
        self.assertFalse(result.WasParsedVariation)
        self.assertFalse(result.WasParsedTime)

    def test_parse_full_request(self):
        """ parse full request """

        result= PathUtils.parse_request("/my/value:100:mc:2029");

        #now check
        self.assertTrue(result.Path == "/my/value")
        self.assertTrue(result.WasParsedPath)
        self.assertTrue(result.RunNumber == 100)
        self.assertFalse(result.IsInvalidRunNumber)
        self.assertTrue(result.WasParsedRunNumber)
        self.assertTrue(result.Variation == "mc")
        self.assertTrue(result.WasParsedVariation)
        self.assertTrue(result.Time != 0)
        self.assertTrue(result.WasParsedTime)
    
    def test_parse_partial_request(self):
        """ * * * parse partial request  * * * """
            
        result= PathUtils.parse_request("/my/value::mc")

        self.assertTrue(result.Path == "/my/value")
        self.assertTrue(result.WasParsedPath)
        self.assertFalse(result.WasParsedRunNumber)
        self.assertTrue(result.Variation == "mc")
        self.assertTrue(result.WasParsedVariation)
        self.assertFalse(result.WasParsedTime)
   
if __name__ == '__main__':
    unittest.main()