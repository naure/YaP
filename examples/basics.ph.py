#!/usr/bin/env python
import os
import sys
import subprocess
from subprocess import Popen, PIPE, STDOUT
import json
from os.path import *
from sys import stdin, stdout, stderr, exit
from glob import glob

def softindex(array, i, alt=None):
    return array[i] if i < len(array) else alt


def pash_call(cmd, flags='', indata=None, convert=None):
    proc = Popen(
        cmd,
        stdin=PIPE if indata else None,
        stdout=PIPE if ('o' in flags or 's' in flags) else None,
        stderr=(
            PIPE if 'e' in flags else
            STDOUT if 's' in flags else None),
    )
    out, err = proc.communicate(indata)
    code = proc.returncode
    ret = []
    if ('o' in flags or 's' in flags):
        if convert:
            ret.append(convert(out))
        else:
            ret.append(out)
    if 'e' in flags:
        ret.append(err)
    if 'r' in flags:
        ret.append(code)
    else:  # The user won't check the return code, so do it now
        if code != 0:
            raise subprocess.CalledProcessError(code, cmd, ret)
    return ret[0] if len(ret) == 1 else ret

#!./pash.py

# Regular python
print("Python")
numbers = {1: 'one', 2: 'two'}

# Regular shell commands
pash_call(["echo", "Shell"], "", None, None)
# Capture the output
now = pash_call(["date", "+%s"], "", None, None)
# Command in brackets. Print result
print(pash_call(["date", "+%s"], "", None, None))

multiline = (pash_call(["echo", "A", "B", "-a", "(parentheses)", "-o", "!", "is", "ignored"], "", None, None))

# Interpolation of commands
for key, value in numbers.items():
    pash_call(["echo", "{}={}".format(key, value)], "", None, None)

pash_call(["echo", str("Any python expression, ignore in quotes".upper())], "", None, None)

# Environment variable in shell. Raises an error if missing.
pash_call(["echo", "{}/somewhere".format(os.environ["HOME"])], "", None, None)
# Environment variable in Python. Returns None if missing.
os.environ.get("missing_variable") is None
pash_call(["echo", "a_{}".format(os.environ.get("variable") or "default value"), "b_c"], "", None, None)
pash_call(["find", ".", "-exec", "cat", str("{}"), "+"], "", None, None)

# Same applies to program arguments
if softindex(sys.argv, 1):
    pash_call(["echo", "First", "argument:", "{}".format(sys.argv[1])], "", None, None)
    for arg in sys.argv:
        print(arg)


# Output conversion
file_list = pash_call(["ls", "-1"], "l", None, str.splitlines)

simple_string = 'Output: ' + pash_call(["echo", "some", "output"], "", None, None)
from_json = pash_call(["echo", "[1,", "2]"], "j", None, json.loads)
to_integer = 2 + (pash_call(["echo", "2"], "i", None, int)) + 2
list_of_lines = pash_call(["ls"], "l", None, str.splitlines)
rows_then_columns = pash_call(["ls", "-l"], "c", None, None)
fields_then_rows = pash_call(["ls", "-l"], "r", None, None)

# Print stdout and stderr
pash_call(["cmd"], "", None, None)
# Capture stdout, print stderr
out = pash_call(["cmd"], "", None, None)
# Capture stderr, print stdout
err = pash_call(["cmd"], "e", None, None)
# Capture both
out, err = pash_call(["cmd"], "oe", None, None)
# Include the return code
out, err, ret = pash_call(["cmd"], "oer", None, None)
