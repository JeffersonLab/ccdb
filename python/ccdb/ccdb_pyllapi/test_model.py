import random
import unittest

class TestCCDBModel(unittest.TestCase):

    def setUp(self):
        self.seq = range(10)

    def test_library(self):
        import ccdb_pyllapi
        

    def test_variations(self):
        import ccdb_pyllapi
        var = ccdb_pyllapi.Variation()
        var.name = "asd"
        var.comment = "ha ha ha"

        
    def test_runrange(self):
        import ccdb_pyllapi
        
        runrange = ccdb_pyllapi.RunRange()
        runrange.min = 0;
        runrange.max = 100;
        runrange.comment = "af"
        
        
    def test_typetable(self):
        import ccdb_pyllapi
        
        tt = ccdb_pyllapi.ConstantsTypeTable()
        #tt.add_column
        
        
        #self.assertEqual(self.seq, range(10))

        # should raise an exception for an immutable sequence
        #self.assertRaises(TypeError, random.shuffle, (1,2,3))

    def test_choice(self):
        element = random.choice(self.seq)
        self.assertTrue(element in self.seq)

    def test_sample(self):
        with self.assertRaises(ValueError):
            random.sample(self.seq, 20)
        for element in random.sample(self.seq, 5):
            self.assertTrue(element in self.seq)

if __name__ == '__main__':
    unittest.main()