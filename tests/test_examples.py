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


def diff_paths(pa, pb):
    with open(pa) as fa, open(pb) as fb:
        a = fa.read()
        b = fb.read()

    if a != b:
        return diff(a, b, fromfile=pa, tofile=pb)
    else:
        return False


def compare_paths(ref_path, test_path, what='Output'):
    test_diff = diff_paths(ref_path, test_path)
    if test_diff:
        print(red('{} {} is different than reference {}'.format(
            what, test_path, ref_path)))
        print(test_diff)
        return 1
    else:
        return 0


class Test(unittest.TestCase):
    yap_path = './yap.py'

    examples_dir = 'examples'
    examples_path = os.path.join(examples_dir, '*.yp')

    regtests_dir = 'regtests'
    regtests_path = os.path.join(regtests_dir, '*.yp')

    def test_examples(self):
        ''' Check that *.yp compile to *.yp.py.
            If not, the compiled file will be stored in example.yp-test.py
        '''
        yps = glob(self.examples_path)
        self.assertTrue(yps)
        for yp in yps:
            errors = 0
            print('Testing {}'.format(yp))
            ref_path = '{}.py'.format(yp)
            test_path = '{}-test.py'.format(yp)

            # Translate
            subprocess.check_call([self.yap_path, '-o', test_path, yp])

            # Compare with reference code
            errors += compare_paths(ref_path, test_path, 'Compiled')

            # Check output Python syntax
            with open(test_path) as test_f:
                test_py = test_f.read()
            try:
                compile(test_py, test_path, 'exec')
            except Exception as e:
                errors += 1
                print(red(repr(e)))
                print('')

            if errors:
                raise AssertionError(red(
                    'There have been {} errors with {}.'.format(errors, yp)))
            else:
                # Clean up only on success
                os.remove(test_path)

    def test_regressions(self):
        ''' Check that *.yp execute and produce the right output.
            If not, the output will be stored in example.yp-test.out and .err
        '''
        yps = glob(self.regtests_path)
        self.assertTrue(yps)
        for yp in yps:
            errors = 0
            print('Testing {}'.format(yp))
            out_ref_path = '{}.out'.format(yp)
            err_ref_path = '{}.err'.format(yp)
            out_test_path = '{}-test.out'.format(yp)
            err_test_path = '{}-test.err'.format(yp)

            # Execute
            with open(out_test_path, 'w') as out_test_f:
                with open(err_test_path, 'w') as err_test_f:
                    ret = subprocess.call(
                        [self.yap_path, yp],
                        stdout=out_test_f,
                        stderr=err_test_f,
                    )

            if ret != 0:
                errors += 1
                print(red('Return code was {} != 0'.format(ret)))

            # Compare output with reference
            errors += compare_paths(out_ref_path, out_test_path, 'Output')

            # Compare stderr with reference
            errors += compare_paths(err_ref_path, err_test_path, 'Stderr')

            if errors:
                raise AssertionError(red(
                    'There have been {} errors with {}.'.format(errors, yp)))
            else:
                # Clean up only on success
                os.remove(out_test_path)
                os.remove(err_test_path)


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(Test)
    unittest.TextTestRunner(verbosity=2).run(suite)
