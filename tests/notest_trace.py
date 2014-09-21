#!/usr/bin/env python3
import unittest
import os
from glob import glob
import sys
sys.path.append('.')

from .utils import compare_paths, red
from behavior_tests.trace import trace, format_db
from behavior_tests.store import format_db
#import behavior_tests.tools
import yap


class A(object):
    def m(self, x):
        return x

def main(a):
    a.m(12)


class Test(unittest.TestCase):

    regtests_dir = 'regtests'
    regtests_paths = glob(os.path.join(regtests_dir, '*.yp'))
    assert regtests_paths, 'No example .yp'

    @unittest.skip
    def test_trace_trace(self):
        a = A()
        db, ret = trace(main, [a])
        dbs = format_db(db)
        print(dbs)

    #@behavior_tests.tools.tracing
    @unittest.skip
    def test_trace(self):
        for yp in self.regtests_paths:
            yap.main([
                '-o', '/dev/null', yp,
            ])
            self.assertTrue('Some test')

    def test_big_trace(self):
        self.assertTrue(self.regtests_paths)
        db = None
        for yp in self.regtests_paths:
            print('Tracing compilation of {}'.format(yp))
            db, ret = trace(yap.main, [[
                '-o', '/dev/null', yp,
            ]],
                fndb=db,  # Reuse the same db to merge data
            )

        dbs = format_db(db)

        ref_path = os.path.join(self.regtests_dir, 'trace.yml')
        test_path = os.path.join(self.regtests_dir, 'trace-test.yml')

        with open(test_path, 'w') as f:
            f.write(dbs)
        #with open(ref_path) as f:
        #    dbs_ref = f.read()

        if not os.path.exists(ref_path):
            open(ref_path, 'w').close()

        errors = compare_paths(ref_path, test_path, 'Trace')
        if errors:
            raise AssertionError(red(
                'There have been {} errors with {}.'.format(errors, test_path)))
        else:
            # Clean up only on success
            os.remove(test_path)


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(Test)
    unittest.TextTestRunner(verbosity=2).run(suite)
