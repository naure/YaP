#!/usr/bin/env python
import os
from os import listdir
from os.path import *
import sys
from sys import stdin, stdout, stderr, exit
from pprint import pprint
from glob import glob
import json

if sys.stdout.isatty():
    def _yap_color(s, code):
        ' Make `s` a colored text. Can be nested. '
        return '{}{}{}'.format(
            code,
            s.replace('\033[0m', code),
            '\033[0m',
        )

    def blue(s):
        return _yap_color(s, '\033[94m')

    def gray(s):
        return _yap_color(s, '\033[97m')

    def green(s):
        return _yap_color(s, '\033[92m')

    def orange(s):
        return _yap_color(s, '\033[93m')

    def red(s):
        return _yap_color(s, '\033[91m')

else:
    blue = gray = green = orange = red = _yap_color = lambda s, c='': s


def softindex(array, i, alt=None):
    return array[i] if i < len(array) else alt


class MissingParameter(object):
    def __init__(self, what):
        self.what = what

    def __str__(self):
        raise KeyError(self.what)

    def __bool__(self):
        return False

def missingget(obj, variable):
    v = obj.get(variable)
    return v if v is not None else MissingParameter(variable)

def missingindex(array, i):
    return array[i] if i < len(array) else MissingParameter(
        "Argument {}".format(i))


from subprocess import Popen, PIPE, STDOUT, CalledProcessError
import re

re_escape_sh = re.compile(r'([\\ ])')

def escape_sh(s):
    return re_escape_sh.sub(r'\\\1', s)

def yap_call(cmd, flags='', indata=None, convert=None):
    if 'h' in flags:  # Shell mode
        cmd = ' '.join(map(escape_sh, cmd))
    proc = Popen(
        cmd,
        stdin=PIPE if indata is not None else None,
        stdout=PIPE if ('o' in flags or 'O' in flags) else None,
        stderr=(
            PIPE if 'e' in flags else
            STDOUT if 'O' in flags else None),
        universal_newlines='b' not in flags,
        shell='h' in flags,
        env={} if 'v' in flags else None,
        bufsize=-1,  # Buffered
    )
    if 'p' in flags:  # Run in the background
        return proc
    out, err = proc.communicate(indata)
    code = proc.returncode
    ret = []
    if ('o' in flags or 'O' in flags):
        if convert:
            ret.append(convert(out))
        else:
            ret.append(out)
    if 'e' in flags:
        ret.append(err)
    if 'r' in flags:
        ret.append(code)
    else:  # The user won't check the return code, so do it now
        if code != 0 and 'n' not in flags:
            raise CalledProcessError(code, cmd, ret)
    # Return either the unique output, the list of outputs, or None
    return ret[0] if len(ret) == 1 else ret or None

#!./yap.py

# Regular python
print("Python")
numbers = {1: 'one', 2: 'two'}
print(sys.argv)

# Regular shell commands
yap_call(["echo", "Shell command"], "", None, None)
# Capture the output
now = yap_call(["date", "+%s"], "o", None, None)
# Command in brackets. Print result
print(yap_call(["date", "+%s"], "o", None, None))

multiline = (yap_call(["echo", "A", "B", "-o", "(parentheses)", "-and", "!", "are", "ignored"], "o", None, None))

system_shell = (yap_call(["A=\"Aaa\";", "echo", "$A;", "echo", "Semi-colons are", "required to separate commands."], "ho", None, None))
print(system_shell)

# Interpolation of commands
for key, value in numbers.items():
    yap_call(["echo", "{}={}".format(key, value)], "", None, None)

yap_call(["echo", str("Any python expression, ignore in quotes".upper())], "", None, None)

yap_call(["echo", str(
    "Same lines joining rules as Python"
)], "", None, None)

yap_call(["echo", str(
    {"inline": "dictionnary"}
)], "", None, None)

yap_call(["echo", "With \'quotes\'"], "", None, None)

# Environment variable in shell. Raises an error if missing.
yap_call(["echo", "{}/somewhere".format(os.environ["HOME"])], "", None, None)
# Environment variable in Python. Returns None if missing.
missingget(os.environ, "missing_variable") is None
yap_call(["echo", "a_{}".format(missingget(os.environ, "variable") or "default value"), "b_c"], "", None, None)
yap_call(["echo", "find", ".", "-exec", "cat", str("{}"), "+"], "", None, None)

# Same applies to program arguments
if missingindex(sys.argv, 1):
    yap_call(["echo", "First argument: {}".format(sys.argv[1])], "", None, None)
    for arg in sys.argv:
        print(arg)


# Output conversion
file_list = yap_call(["ls", "-1"], "lo", None, str.splitlines)

simple_string = 'Output: ' + yap_call(["echo", "some", "output"], "o", None, None)
from_json = yap_call(["echo", "[1, 2]"], "jo", None, json.loads)
to_integer = 2 + (yap_call(["echo", "2"], "io", None, int)) + 2
list_of_lines = yap_call(["ls"], "lo", None, str.splitlines)
rows_then_columns = yap_call(["ls", "-l"], "co", None, None)
fields_then_rows = yap_call(["ls", "-l"], "r", None, None)
binary = yap_call(["echo", "cat", "doc.pdf"], "bo", None, None)

# Print stdout and stderr
yap_call(["echo"], "", None, None)
# Capture stdout, print stderr
out = yap_call(["echo"], "o", None, None)
# Capture stderr, print stdout
err = yap_call(["echo"], "e", None, None)
# Capture both
out, err = yap_call(["echo"], "oe", None, None)
# Include the return code
out, err, ret = yap_call(["echo", "May fail.."], "oer", None, None)
if ret == 0:
    print(out)
# n to ignore errors
yap_call(["false", "unsafe", "cmd"], "n", None, None)
# p to run in the background and get a proc object
proc = yap_call(["echo", "sleep", "1"], "po", None, None)
out, err = proc.communicate("input")
# h to run through a shell
print(yap_call(["echo", "a", "b", "|", "grep", "a"], "ho", None, None))
# v to run with a clean environment
print(yap_call(["echo", "clean"], "vo", None, None))
yap_call(["echo", "Ok!"], "", None, None)
