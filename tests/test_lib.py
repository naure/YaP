#!/usr/bin/env python3
import unittest
import sys
sys.path.append('.')

from yap import call_lib
escape_sh = None
exec(call_lib)


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
                escape_sh(B(raw)),
                B(escaped),
            )


if __name__ == '__main__':
    unittest.main(verbosity=2)
