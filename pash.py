#!/usr/bin/env python3

import sys
import re

# Find python expression in shell commands
re_py_inline = re.compile(r'\$(\{[^}]+\}|\w+)')  # ${expression} or $variable
re_py_simple = re.compile(r'\$(\w+)')  # $variable

# Find shell command in python expressions
re_sh_inline = re.compile(r'!\[([^]]+)\]')  # ![inline command]
re_sh_end = re.compile(r'!([^[].*)')  # !command until end of line

def split_sh(line):
    ' Decide if this line has a shell command and extract it. '
    parts = re_sh_end.split(line, maxsplit=1)
    return parts[0], parts[1] if len(parts) >= 2 else None


def check_curly(e):
    ' Check that `e` is enclosed in {} or not at all. '
    curlies = e.startswith('{') + e.endswith('}')
    if curlies == 0:
        return e
    if curlies == 2:
        return e[1:-1]
    if curlies == 1:
        raise SyntaxError(e)


def split_expressions(regex, raw):
    ' Split the raw string with regex, checking the {}. '
    parts = regex.split(raw)
    for i in range(1, len(parts), 2):
        parts[i] = check_curly(parts[i])  # Check and clean all expressions
    return parts


def expand_shell(sh):
    ' Expand expressions in a shell command or argument. '
    parts = split_expressions(re_py_inline, sh)
    if len(parts) == 1:
        return '"{}"'.format(parts[0])  # No expansion
    if len(parts) == 3 and parts[0] == '' and parts[2] == '':
        return 'str({})'.format(parts[1])  # Only one expansion without text

    exprs = parts[1::2]
    for i in range(1, len(parts), 2):
        parts[i] = '{}'  # Transform expressions into template arguments

    template = ''.join(parts)
    args = ', '.join(exprs)  # XXX Should wrap with ()
    return '"{}".format({})'.format(template, args)  # Will evaluate and render


def compile_sh(sh):
    ' Compile a shell command into python code'
    cmd = sh.split()
    expanded = map(expand_shell, cmd)
    args = ', '.join(expanded)
    return "subprocess.check_output([{}])".format(args)


def expand_python(py):
    ' Expand shell commands in python expressions. '
    parts = re_sh_inline.split(py)
    if len(parts) == 1:
        return '{}'.format(parts[0])  # No expansion

    for i in range(1, len(parts), 2):
        parts[i] = compile_sh(parts[i])
    return ''.join(parts)


def process_line(line):
    before, after = split_sh(line)
    sh = compile_sh(after) if after else ''
    return expand_python(before) + sh


with open(sys.argv[1]) as f:
    source = f.read().splitlines()

dest = [
    source[0],  # The #! line. XXX
    'import subprocess',
]
dest.extend(map(process_line, source[1:]))

#print('\n'.join(source))
#print()
#print(">>>>")
#print()
print('\n'.join(dest))
