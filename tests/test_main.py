#!/usr/bin/env python3
import unittest
import sys
sys.path.append('.')
from pprint import pprint

import yap


def B(s):
    " Avoid quoting backslashes all the time "
    return (s.replace('B', '\\')
            .replace('S', "'")
            .replace('D', '"')
            .replace('N', '\n')
            )

class Test(unittest.TestCase):

    def check_regex(self, regex, data):
        for s, expected in data:
            got = [m.group() for m in regex.finditer(s)]
            self.assertEqual(expected, got)

    def test_test(self):
        self.assertEqual(B('B S DB'), '\\ \' "\\')

    def test_split_bang(self):
        yp = '''
            # Comment
            !bang
            Not taking next line
            (! line 1
               line 2)
            ! line 3 { x
                line 4
            }
            # End
        '''
        parsed = yap.split_bang(yp)
        pprint(list(parsed))

    def test_split_bang_multiline(self):
        yp = '''
            # Comment
            stuff

            ! line 3 { x
                line 4 # bang comment
            }
            # End
        '''
        parsed = yap.split_bang(yp)
        pprint(list(parsed))

    def test_re_symbols_bang_close(self):
        data = [
            ('', ['']),
            ('random stuffs', ['']),
            ('random stuffs\nnext line', ['', '']),
            ('opening {\nclosing }', ['{', '', '}', '']),
            ('stuff\n closing ) ', ['', ')', '']),
        ]
        self.check_regex(yap.re_symbols_bang_close, data)

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
    unittest.main(verbosity=2)
