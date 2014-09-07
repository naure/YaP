#!/usr/bin/env python
import os
import unittest
import subprocess
from glob import glob


class Test(unittest.TestCase):
    examples_dir = 'examples'
    examples_path = os.path.join(examples_dir, '*.ph')
    pash_path = './pash.py'

    def test_examples(self):
        ''' Check that example.ph compiles to example.ph.py.
            If not, the compiled file will be stored in example.ph-test.py
        '''
        for ph in glob(self.examples_path):
            print('Testing {}'.format(ph))
            refpy = '{}.py'.format(ph)
            testpy = '{}-test.py'.format(ph)
            subprocess.check_call([self.pash_path, '-o', testpy, ph])
            with open(testpy) as testf, open(refpy) as reff:
                self.assertEqual(testf.read(), reff.read())
            os.remove(testpy)


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(Test)
    unittest.TextTestRunner(verbosity=2).run(suite)
