#!/usr/bin/env python
import os
import unittest
import subprocess
from glob import glob
import difflib


def color_diffline(line):
    if line.startswith('-'):  # Red
        return '\033[91m' + line + '\033[0m'
    if line.startswith('+'):  # Green
        return '\033[92m' + line + '\033[0m'
    return line


def diff(a, b, **kwargs):
    return '\n'.join(map(
        color_diffline,
        difflib.unified_diff(
            a.splitlines(), b.splitlines(), **kwargs
        )))


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
            ref_path = '{}.py'.format(ph)
            test_path = '{}-test.py'.format(ph)
            subprocess.check_call([self.pash_path, '-o', test_path, ph])
            with open(test_path) as test_f, open(ref_path) as ref_f:
                ref_py = ref_f.read()
                test_py = test_f.read()
                if test_py != ref_py:
                    print(diff(
                        ref_py, test_py, fromfile=ref_path, tofile=test_path,
                    ))
                    raise AssertionError(
                        'Compiled {} is different than reference {}'.format(
                            test_path, ref_path))
            os.remove(test_path)


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(Test)
    unittest.TextTestRunner(verbosity=2).run(suite)
