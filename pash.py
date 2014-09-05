#!/usr/bin/env python3

import sys
import re
from itertools import starmap

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('source', nargs='?', default='-')
parser.add_argument('-o', '--output',
                    help='Compile source to python and write it into output')
args = parser.parse_args()

# Optional colored output
if args.output == '-' and sys.stdout.isatty():
    ENDCOLOR = '\033[0m'

    def color(s, code):
        ' Make `s` a colored text. Can be nested. '
        return '{}{}{}'.format(
            code,
            s.replace(ENDCOLOR, code),
            ENDCOLOR,
        )

    def gray(s):
        return color(s, '\033[97m')

    def blue(s):
        return color(s, '\033[94m')

    def green(s):
        return color(s, '\033[92m')

    def orange(s):
        return color(s, '\033[93m')

    def red(s):
        return color(s, '\033[91m')
else:
    def color(s, code=None):
        return s
    gray = blue = green = orange = red = color

# Find python expression in shell commands
re_py_inline = re.compile(r'(\{[^}]+\}|\$\w+)')  # {expression}
re_arg = re.compile(r'\$([0-9]+)')  # $1
re_all_args = re.compile(r'\$\*')  # $*
re_env = re.compile(r'\$(\w+)')  # $variable

# Find shell command in python expressions
re_sh_inline = re.compile(r'\w?!\(([^)]+)\)')  # ![inline command]
re_sh_end = re.compile(r'\w?!([^(].*)')  # !command until end of line
re_sh_both = re.compile(r'''
    (\w*)!  # Operator + leading flags
    (?:  # Non-capturing group
        \( ( [^)]+ ) \)  # !(inline)
    |
        ( [^(] .* )$  # ! command until end of line
    )
    ''', re.X)

# Find comments
re_comment = re.compile(r'^\s*#')

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




def x(regex, s):


    scanner = re.Scanner([
        r'[([{]',
        r'[)\]}]',
        r'"\'\\',
        regex,
    ])

#                          Capture       Opening   Closing     Quoting
re_symbol = re.compile(
    r'''(
    \w*!  )|(
    [({[]     )|(
    [)}\]]    )|(
    ["\'\\]   )|(
    \s* (?:\#.*)? $    )
    ''',
    re.X | re.MULTILINE)


def safe_split(s):
    ' Like re.split() but aware of parenthesis, quotes, and escaping. '
    #escaped = False  # XXX Support escaping
    in_quotes = False
    in_dquotes = False
    depth = 0

    capturing_since = None
    capturing_depth = None

    parts = []
    part_start = 0

    for m in re_symbol.finditer(s):
        capture, opening, closing, quote, eol = m.groups()
        eol = eol is not None
        if quote:
            # Toggle quote state and move on
            if quote == "'":
                in_quotes = not in_quotes
            elif quote == '"':
                in_dquotes = not in_dquotes

        elif not in_quotes and not in_dquotes:
            if opening:
                depth += 1
            elif closing:
                depth -= 1

            if capturing_depth is None:
                if capture:
                    # Start capturing
                    capturing_since = m.start()
                    capturing_depth = depth

            elif depth < capturing_depth or (eol and depth == 0):
                    # Finish capturing
                    parts.append((
                        s[part_start:capturing_since],  # Regular
                        s[capturing_since:m.start()],  # Captured
                    ))
                    part_start = m.start()
                    capturing_depth = None
        #else: ignore quoted part
    parts.append((s[part_start:], None))  # Regular end, possibly empty
    return parts



def decompose(regex, s):
    ''' Split s using regex and return it in this format:
        [(non-matching part, None),
         (matching part, groups),
         ...
        ]
        The first and last non-matching parts may be empty strings.
    '''
    matches = regex.finditer(s)
    zipped = []
    idx = 0
    for m in matches:
        zipped.append((s[idx:m.start()], None))
        zipped.append((m.group(), m.groups()))
        idx = m.end()
    zipped.append((s[idx:], None))
    return zipped


def expand_shell(sh):
    ' Expand expressions in a shell command or argument. '
    parts = split_expressions(re_py_inline, sh)
    if len(parts) == 1:
        return '"{}"'.format(orange(parts[0]))  # No expansion

    exprs = [green(expand_env_strict(p)) for p in parts[1::2]]
    # XXX Use ..strict with $var and ..soft with {expression}.
    if len(parts) == 3 and parts[0] == '' and parts[2] == '':
        return 'str({})'.format(exprs[0])  # Only one expansion without text

    for i in range(1, len(parts), 2):
        parts[i] = green('{}')  # Transform expressions into template arguments

    template = ''.join(parts)  # Recompose the command with {} in it
    args = ', '.join(exprs)  # XXX Should wrap with ()
    return '"{}".format({})'.format(orange(template), args)  # Will evaluate and render


re_sh = re.compile(r'(\w*)!(.*)', re.DOTALL)

def compile_sh(cmd):
    ' Compile a shell command into python code'
    flags, sh = re_sh.match(cmd).groups()
    parts = sh.split()  # XXX Support { with spaces }
    expanded = map(expand_shell, parts)
    args = ', '.join(expanded)
    process = "subprocess.check_output([{}])".format(args)
    if 'l' in flags:
        return "{}.splitlines()".format(process)
    if 'i' in flags:
        return "int({})".format(process)
    if 'f' in flags:
        return "float({})".format(process)
    if 'j' in flags:
        return "json.loads({})".format(process)
    return process


soft_index_lib = '''
def softindex(array, i, alt=None):
    return array[i] if i < len(array) else alt
'''

missing_lib = '''
class Missing(object):
    def __init__(self, what):
        self.what = what

    def __str__(self):
        raise KeyError(self.what)

    def __bool__(self):
        return False

missingget(obj, variable):
    return obj.get(variable) or Missing(variable)

missingindex(array, i):
    return softindex(array, i) or Missing(
        "Argument {}".format(i))
'''


def expand_env_strict(py):
    # XXX Should use Missing instead
    return re_env.sub(
        r'os.environ["\1"]',
        re_arg.sub(
            r'sys.argv[\1]',
            re_all_args.sub(
                r'sys.argv', py)))


def expand_env_soft(py):
    return re_env.sub(
        r'os.environ.get("\1")',
        re_arg.sub(
            r'softindex(sys.argv, \1)',
            re_all_args.sub(
                r'sys.argv', py)))


def _expand_python(py):
    ' Expand shell commands in python expressions. '
    parts = re_sh_inline.split(py)
    # Expand environment variables
    for i in range(0, len(parts), 2):
        parts[i] = expand_env_soft(parts[i])
    if len(parts) == 1:
        return '{}'.format(parts[0])  # No expansion

    for i in range(1, len(parts), 2):
        parts[i] = compile_sh(parts[i])
    return ''.join(parts)


def expand_python(s, compile_fn):
    ' Expand shell commands in python code. '
    parts = safe_split(s)

    def do(py, cmd):
        expanded_py = expand_env_soft(py)
        if not cmd:
            return expanded_py
        return '{}{}'.format(expanded_py, compile_fn(cmd))

    return ''.join(starmap(do, parts))


def process_line(line):
    if re_comment.match(line):
        return line

    before, after = split_sh(line)
    sh = compile_sh(after) if after else ''
    return expand_python(before) + sh


with sys.stdin if args.source == '-' else open(args.source) as f:
    source = f.read().splitlines()

dest = [
    source[0],  # The #! line. XXX
    'import os',
    'import sys',
    'import subprocess',
    'import json',
    'from os.path import *',
    'from sys import stdin, stdout, stderr, exit',
    'from glob import glob',
]
dest.extend(soft_index_lib.splitlines())
#dest.extend(map(process_line, source[1:]))
rest = '\n'.join(source[1:])
dest.append(blue(expand_python(
    rest,
    lambda cmd: gray(compile_sh(cmd)),
)))

output = '\n'.join(dest)
if args.output:
    with sys.stdout if args.output == '-' else open(args.output) as f:
        print(output)
else:
    exec(output, {}, {})
