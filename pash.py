#!/usr/bin/env python3

import sys
from logging import debug
import re
from itertools import starmap

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('source', nargs='?', default='-')
parser.add_argument('-p', '--python', action='store_true',
                    help='Compile source to python and write it')
parser.add_argument('-o', '--output',
                    help='Python code output file. Implies --python')
args = parser.parse_args()

if args.python and not args.output:
    args.output = args.source + '.py'


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
    # No colored output
    def color(s, code=None):
        return s
    gray = blue = green = orange = red = color


def parse_cmd(s):
    ''' Extract arguments from a shell command while parsing the {expressions}.
        Return [ (argument, [expressions, ..]), .. ].
    '''
    parts = []
    current_part = ''
    current_exprs = []
    after = s
    while after:
        debug('<< ' + after)
        before, expr, after = extract_next_space_or_py_expr(after)
        debug('==== {} = <{}> = {}'.format(before, expr, after))
        current_part += before
        if expr is not None:
            current_part += '{}'  # for format()
            if expr == '{}':
                expr = '{"{}"}'  # Replace literal {} by itself
            current_exprs.append(expr)
        else:  # New argument
            parts.append((current_part, current_exprs))
            current_part = ''
            current_exprs = []
    if current_part:
        parts.append((current_part, current_exprs))
    return parts


def combine_re(res, flags=0):
    return re.compile(
        '({})'.format(
            ')|('.join(res)),
        flags)

re_symbols_expr_open = combine_re([
    r'(?: \s+ | \{ | \$)',   # Start capture
    r'$x^',     # Ignore brackets (never matches)
    r'$x^',     # Ignore brackets (never matches)
    r'$x^',     # Ignore quotes (never matches)
], re.X | re.MULTILINE)

re_symbols_expr_close = combine_re([
    r'\}',  # End capture
    r'$x^',     # Ignore brackets (never matches)
    r'$x^',     # Ignore brackets (never matches)
    r'["\']',   # Quote
], re.X | re.MULTILINE)

re_symbols_dollar_close = combine_re([
    r'\w+',     # capture all alphanumeric characters
    r'$x^',     # Ignore brackets (never matches)
    r'$x^',     # Ignore brackets (never matches)
    r'$x^',     # Ignore quotes (never matches)
], re.X | re.MULTILINE)


def extract_next_space_or_py_expr(s):
    ' Extract the next {python} from a shell command '
    mopen = safe_search(re_symbols_expr_open, s)
    if mopen:
        if mopen.group() == '{':
            mclose = safe_search(re_symbols_expr_close, s, pos=mopen.end())
        elif mopen.group() == '$':
            mclose = safe_search(re_symbols_dollar_close, s, pos=mopen.end())
        else:  # Just spaces, split around it and return
            return s[:mopen.start()], None, s[mopen.end():]

        if mclose:
            return (
                s[:mopen.start()],
                s[mopen.start():mclose.end()],
                s[mclose.end():],
            )
    return s, None, ''  # Nothing found


# XXX Add a 'stop capture' regex group, that goes after closing. 'closing' will
# retry the 'stop' regex.
def safe_search(re_symbols, s, pos=0):
    ' Like re.search() but aware of parenthesis, quotes, and escaping. '
    #escaped = False  # XXX Support escaping
    in_quotes = False
    in_dquotes = False
    depth = 0

    for m in re_symbols.finditer(s, pos=pos):
        capture, opening, closing, quote = m.groups()
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

            if capture:
                # Found it
                return m
    return None  # Not found


re_symbols_py = re.compile(
    r'''(
    \w*!  )|(       # Start capture
    \s* (?:\#.*)? $ )|(  # EOL
    [({[]     )|(   # Open bracket
    [)}\]]    )|(   # Close bracket
    ["\']           # Quote
    )''',
    re.X | re.MULTILINE)

# XXX Make use of safe_search
def safe_split(re_symbols, s):
    ' Like re.split() but aware of parenthesis, quotes, and escaping. '
    #escaped = False  # XXX Support escaping
    in_quotes = False
    in_dquotes = False
    depth = 0

    capturing_since = None
    capturing_depth = None

    parts = []
    part_start = 0

    for m in re_symbols.finditer(s):
        capture, eol, opening, closing, quote = m.groups()
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


# XXX Support escaping and keep quoted quotes ('"')
def render_arg(arg):
    return re.sub(r'["\']', '', arg)


def render_py_expr(expr):
    debug('==== render: ' + expr)
    if expr.startswith('{'):
        return expand_env_soft(expr[1:-1])
    elif expr.startswith('$'):
        return expand_env_strict(expr)


def render_sh_arg(arg, exprs):
    rendered_arg = render_arg(arg)
    if not exprs:  # No expansion, "plain string"
        return '"{}"'.format(orange(rendered_arg))
    # XXX Should wrap the expressions with ()
    rendered_exprs = [green(render_py_expr(p)) for p in exprs]
    if arg == '{}':  # Only one expression without text
        # XXX Use ..strict with $var and ..soft with {expression}.
        return 'str({})'.format(rendered_exprs[0])
    # Will evaluate and render all expressions in the argument
    format_args = ', '.join(rendered_exprs)
    return '"{}".format({})'.format(orange(rendered_arg), format_args)


def split_and_expand_shell(sh):
    ' Expand expressions in a shell command or argument. '
    parts = parse_cmd(sh.strip())
    rendered_parts = starmap(render_sh_arg, parts)
    return rendered_parts


re_sh = re.compile(r'(\w*)!(.*)', re.DOTALL)

def compile_sh(cmd):
    ' Compile a shell command into python code'
    flags, sh = re_sh.match(cmd).groups()
    parts = split_and_expand_shell(sh)
    args = ', '.join(parts)
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


# Find environment variables
re_arg = re.compile(r'\$([0-9]+)')  # $1
re_all_args = re.compile(r'\$\*')  # $*
re_env = re.compile(r'\$(\w+)')  # $variable


def expand_env_strict(py):
    return re_env.sub(
        r'os.environ["\1"]',
        re_arg.sub(
            r'sys.argv[\1]',
            re_all_args.sub(
                r'sys.argv', py)))


# XXX Should use Missing instead
def expand_env_soft(py):
    return re_env.sub(
        r'os.environ.get("\1")',
        re_arg.sub(
            r'softindex(sys.argv, \1)',
            re_all_args.sub(
                r'sys.argv', py)))


def expand_python(s):
    ' Expand shell commands in python code. '
    parts = safe_split(re_symbols_py, s)

    def do(py, cmd):
        expanded_py = expand_env_soft(py)
        if not cmd:
            return expanded_py
        return '{}{}'.format(expanded_py, gray(compile_sh(cmd)))

    return ''.join(starmap(do, parts))


def main(args):
    with sys.stdin if args.source == '-' else open(args.source) as f:
        source = f.read()

    header = [
        '#!/usr/bin/env python',
        'import os',
        'import sys',
        'import subprocess',
        'import json',
        'from os.path import *',
        'from sys import stdin, stdout, stderr, exit',
        'from glob import glob',
    ]
    header.append(soft_index_lib)

    compiled = blue(expand_python(source))
    pycode = '\n'.join(header) + '\n' + compiled

    if args.output:
        if args.output == '-':
            print(pycode)
        else:
            with open(args.output, 'w') as f:
                f.write(pycode)
            print('Compiled to {}'.format(args.output))
    else:
        exec(pycode, {}, {})


if __name__ == '__main__':
    main(args)
