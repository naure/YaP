#!/usr/bin/env python
import os
import sys
import subprocess
import json
from os.path import *
from sys import stdin, stdout, stderr, exit
from glob import glob

def softindex(array, i, alt=None):
    return array[i] if i < len(array) else alt

#!./pash.py

# Regular python
print("Python")
numbers = {1: 'one', 2: 'two'}

# Regular shell commands
subprocess.check_output(["echo", "Shell"])
# Capture the output
now = subprocess.check_output(["date", "+%s"])
# Command in brackets. Print result
print(subprocess.check_output(["date", "+%s"]))

multiline = (subprocess.check_output(["echo", "A", "B", "-a", "(parentheses)", "-o", "!", "is", "ignored"]))

# Interpolation of commands
for key, value in numbers.items():
    subprocess.check_output(["echo", "{}={}".format(key, value)])

subprocess.check_output(["echo", str("Any python expression, ignore in quotes".upper())])

# Environment variable in shell. Raises an error if missing.
subprocess.check_output(["echo", "{}/somewhere".format(os.environ["HOME"])])
# Environment variable in Python. Returns None if missing.
os.environ.get("missing_variable") is None
subprocess.check_output(["echo", "a_{}".format(os.environ.get("variable") or "default value"), "b_c"])
subprocess.check_output(["find", ".", "-exec", "cat", str("{}"), "+"])

# Same applies to program arguments
if softindex(sys.argv, 1):
    subprocess.check_output(["echo", "First", "argument:", "{}".format(sys.argv[1])])
    for arg in sys.argv:
        print(arg)


# Output conversion
file_list = subprocess.check_output(["ls", "-1"]).splitlines()

simple_string = 'Output: ' + subprocess.check_output(["echo", "some", "output"])
from_json = json.loads(subprocess.check_output(["echo", "[1,", "2]"]))
to_integer = 2 + (int(subprocess.check_output(["echo", "2"]))) + 2
list_of_lines = subprocess.check_output(["ls"]).splitlines()
rows_then_columns = subprocess.check_output(["ls", "-l"])
fields_then_rows = subprocess.check_output(["ls", "-l"])
