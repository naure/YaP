#!/usr/bin/env python
import unittest
import sys
sys.path.append('.')

import yap


def B(s):
    " Avoid quoting backslashes all the time "
    return (s.replace('B', '\\')
            .replace('S', "'")
            .replace('D', '"')
            .replace('N', '\n')
            )

class Test(unittest.TestCase):

    def test_test(self):
        self.assertEqual(B('B S DB'), '\\ \' "\\')

    def test_escape_py(self):
        data = [
            ('nothing', 'nothing'),
            ('with spaces', 'with spaces'),
            ('with Bs', 'with BBs'),
            ('keep DquotesD and SquotesS', 'keep BDquotesBD and BSquotesBS'),
            ('with BDs', 'with BBBDs'),
            #('with New lines', 'with Bnew lines'),  # XXX Not yet
            ('', ''),
        ]
        for raw, escaped in data:
            self.assertEqual(
                yap.escape_py(B(raw)),
                B(escaped),
            )


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(Test)
    unittest.TextTestRunner(verbosity=2).run(suite)
