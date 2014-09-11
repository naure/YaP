#!/usr/bin/env python
import unittest
import sys
sys.path.append('.')

import yaplib


def B(s):
    " Avoid quoting backslashes all the time "
    return s.replace('B', '\\').replace('S', "'").replace('D', '"')

class Test(unittest.TestCase):

    def test_test(self):
        self.assertEqual(B('B S DB'), '\\ \' "\\')

    def test_escape_sh(self):
        data = [
            ('nothing', 'nothing'),
            ('with spaces', 'withB spaces'),
            ('with Bs', 'withB BBs'),
            ('keep DquotesD and SquotesS', 'keepB DquotesDB andB SquotesS'),
            ('with BDs', 'withB BBDs'),
            ('', ''),
        ]
        for raw, escaped in data:
            self.assertEqual(
                yaplib.escape_sh(B(raw)),
                B(escaped),
            )


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(Test)
    unittest.TextTestRunner(verbosity=2).run(suite)
