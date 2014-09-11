#!/usr/bin/env python
import os
import unittest
import subprocess
from glob import glob
import difflib


def red(s):
    return '\033[91m' + s + '\033[0m'
def green(s):
    return '\033[92m' + s + '\033[0m'


def color_diffline(line):
    if line.startswith('-'):  # Red
        return red(line)
    if line.startswith('+'):  # Green
        return green(line)
    return line


def diff(a, b, **kwargs):
    return '\n'.join(map(
        color_diffline,
        difflib.unified_diff(
            a.splitlines(), b.splitlines(), **kwargs
        )))


class Test(unittest.TestCase):
    examples_dir = 'examples'
    examples_path = os.path.join(examples_dir, '*.yp')
    yap_path = './yap.py'

    def test_examples(self):
        ''' Check that *.yp compile to *.yp.py.
            If not, the compiled file will be stored in example.yp-test.py
        '''
        yps = glob(self.examples_path)
        self.assertTrue(yps)
        for yp in yps:
            print('Testing {}'.format(yp))
            ref_path = '{}.py'.format(yp)
            test_path = '{}-test.py'.format(yp)
            subprocess.check_call([self.yap_path, '-o', test_path, yp])
            with open(test_path) as test_f, open(ref_path) as ref_f:
                ref_py = ref_f.read()
                test_py = test_f.read()

                ok = True
                # Check Python syntax
                try:
                    compile(test_py, test_path, 'exec')
                except Exception as e:
                    ok = False
                    print(red(repr(e)))
                    print('')
                # Check reference code
                if test_py != ref_py:
                    ok = False
                    print(diff(
                        ref_py, test_py, fromfile=ref_path, tofile=test_path,
                    ))
                if not ok:
                    raise AssertionError(
                        'Compiled {} is different than reference {}'.format(
                            test_path, ref_path))
            os.remove(test_path)


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(Test)
    unittest.TextTestRunner(verbosity=2).run(suite)
