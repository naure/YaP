#!/usr/bin/env python3
import unittest
import sys
sys.path.append('.')

from yap import expand_env_soft

from yap import call_lib
escape_sh = None
exec(call_lib)

from yap import missing_lib
exec(missing_lib)


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

    def test_expand_env_soft(self):
        class O(object):
            pass
        # Arguments
        sys = O()
        sys.argv = ['zero', 'un']

        self.assertEqual(eval(
            expand_env_soft('bool($1)')), True
        )
        self.assertEqual(eval(
            expand_env_soft('$1 == "un"')), True
        )
        self.assertEqual(eval(
            expand_env_soft('bool($2)')), False
        )
        self.assertEqual(eval(
            expand_env_soft('$2 == "deux"')), False
        )
        self.assertEqual(eval(
            expand_env_soft('$2 == $2')), False
        )
        with self.assertRaises(KeyError):
            eval(expand_env_soft('"error: {}".format($2)'))
        with self.assertRaises(KeyError):
            eval(expand_env_soft('$2[0]'))
        with self.assertRaises(KeyError):
            eval(expand_env_soft('$2[-3:]'))
        with self.assertRaises(KeyError):
            eval(expand_env_soft('$2.attr'))
        with self.assertRaises(KeyError):
            eval(expand_env_soft('$2 + "nope"'))
        with self.assertRaises(KeyError):
            eval(expand_env_soft('int($2)'))

        # Environment variables
        os = O()
        os.environ = {'env': 'ENV!', 'empty': ''}
        self.assertEqual(eval(
            expand_env_soft('$env')), 'ENV!'
        )
        self.assertEqual(eval(
            expand_env_soft('$empty')), ''
        )
        self.assertEqual(eval(
            expand_env_soft('bool($missing)')), False
        )
        with self.assertRaises(TypeError):
            eval(expand_env_soft('"error: " + $missing'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
