#!/usr/bin/env python3

import sys
from logging import debug
import re
from itertools import starmap

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('source')
parser.add_argument('script_args', nargs=argparse.REMAINDER)
parser.add_argument('-p', '--python', action='store_true',
                    help='Compile source to python and write it')
parser.add_argument('-o', '--output',
                    help='Python code output file. Implies --python')
parser.add_argument('-n', '--dry-run', action='store_true',
                    help='Shell commands will not execute, but output their '
                         'command line instead')
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


def parse_cmd(s, flags):
    ''' Extract arguments from a shell command while parsing the {expressions}.
        Return [ (argument, [expressions, ..]), .. ].
    '''
    parse_dollar = not 'h' in flags
    parts = []
    current_part = ''
    current_exprs = []
    after = s
    while after:
        debug('<< ' + after)
        before, expr, after = extract_next_space_or_py_expr(after, parse_dollar)
        debug('==== {} = <{}> = {}'.format(before, expr, after))
        current_part += before
        if expr is not None:
            if expr.isspace():  # New argument
                parts.append((current_part, current_exprs))
                current_part = ''
                current_exprs = []
            else:  # An expression in the current argument
                current_part += '{}'  # for format()
                if expr == '{}':
                    expr = '{"{}"}'  # Replace literal {} by itself
                current_exprs.append(expr)
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
    r'["\']',   # Quotes
], re.X | re.MULTILINE)

re_symbols_expr_close = combine_re([
    r'\}',  # End capture
    r'\{',     # Ignore other brackets
    r'\}',     # Ignore other brackets
    r'["\']',   # Quotes
], re.X | re.MULTILINE)

re_symbols_dollar_close = combine_re([
    r'\w+',     # capture all alphanumeric characters
    r'$x^',     # Ignore brackets (never matches)
    r'$x^',     # Ignore brackets (never matches)
    r'$x^',     # Ignore quotes (never matches)
], re.X | re.MULTILINE)


def extract_next_space_or_py_expr(s, parse_dollar=True):
    ' Extract the next {python} or next argument from a shell command '
    def ret(mopen, mclose):
        return (
            s[:mopen.start()],
            s[mopen.start():mclose.end()],
            s[mclose.end():],
        )

    for mopen, quoted, depth in safe_search(re_symbols_expr_open, s):
        if not mopen:
            break

        if mopen.group() == '{':
            for mclose, close_quoted, close_depth in safe_search(
                    re_symbols_expr_close, s, pos=mopen.end()):

                if mclose and not close_quoted and close_depth == 0:
                    return ret(mopen, mclose)

        elif mopen.group() == '$':
            if not parse_dollar:
                continue
            for mclose, close_quoted, close_depth in safe_search(
                    re_symbols_dollar_close, s, pos=mopen.end()):

                if mclose:
                    return ret(mopen, mclose)

        # Just spaces
        elif quoted:
            continue
        else:  # Split around the spaces and return
            return ret(mopen, mopen)

        break  # Close not found, ignore. Could raise SyntaxError instead XXX
    return s, None, ''  # Nothing found


# XXX Add a 'stop capture' regex group, that goes after closing. 'closing' will
# retry the 'stop' regex.
def safe_search(re_symbols, s, pos=0, openings='({[', closings=')}]'):
    ' Like re.search() but aware of parenthesis, quotes, and escaping. '
    #escaped = False  # XXX Support escaping
    in_quotes = False
    in_dquotes = False
    quoted = False
    depth = 0

    for m in re_symbols.finditer(s, pos=pos):
        c = m.group()
        capture, opening, closing, quote = m.groups()
        # Toggle quote state
        if c == "'":
            in_quotes = not in_quotes
        elif c == '"':
            in_dquotes = not in_dquotes
        quoted = in_quotes or in_dquotes

        if capture:  # Found it
            yield m, quoted, depth

        if not quoted:
            if c in openings:
                depth += 1
            elif c in closings:
                depth -= 1

    yield None, quoted, depth  # Not found


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
                if eol and depth == 0:  # End of pure Python statement
                    parts.append((s[part_start:m.end()], None))
                    part_start = m.end()

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


re_escape_py = re.compile(r'([\\\'"])')

def escape_py(s):
    return re_escape_py.sub(r'\\\1', s)

# XXX Support escaping and keep quoted quotes ('"')
def render_arg(arg):
    if arg.startswith('"'):
        assert arg.endswith('"')
        return escape_py(arg[1:-1])
    else:
        return escape_py(arg)


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
        return 'str({})'.format(rendered_exprs[0])
    # Will evaluate and render all expressions in the argument
    format_args = ', '.join(rendered_exprs)
    return '"{}".format({})'.format(orange(rendered_arg), format_args)


def split_and_expand_shell(sh, flags):
    ' Expand expressions in a shell command or argument. '
    parts = parse_cmd(sh.strip(), flags)
    rendered_parts = [render_sh_arg(arg, exprs) for arg, exprs in parts]
    return rendered_parts


output_flags = ('o', 'e', 'r')
re_sh = re.compile(r'(\w*)!(.*)', re.DOTALL)

def compile_sh(cmd, is_expr):
    ' Compile a shell command into python code'
    flags, sh = re_sh.match(cmd).groups()
    if is_expr and not any(f in flags for f in output_flags):
        flags += 'o'  # By default, capture stdout if inside an expression

    # The command and arguments list
    cmd_args = split_and_expand_shell(sh, flags)
    if args.dry_run:
        cmd_args.insert(0, '"echo"')

    # Input (XXX Not implemented)
    indata = 'None'

    # Output conversions
    convert = 'None'
    if 'l' in flags:
        convert = 'str.splitlines'
    if 'i' in flags:
        convert = 'int'
    if 'f' in flags:
        convert = 'float'
    if 'j' in flags:
        convert = 'json.loads'

    # Call the process
    process = 'pash_call([{}], "{}", {}, {})'.format(
        ', '.join(cmd_args), flags, indata, convert)
    return process


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

    def do_inline_sh(py, cmd):
        expanded_py = expand_env_soft(py)
        if not cmd:
            return expanded_py
        mixed = bool(py.strip())  # Shell inside of a Python expression
        return '{}{}'.format(expanded_py, gray(
            compile_sh(cmd, is_expr=mixed)))

    return ''.join(starmap(do_inline_sh, parts))


# A convenience function around Popen, configured by letters flags.
# Allows to perform several operations as a single expression (function call).
with open('pashlib.py') as f:
    call_lib = f.read()

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


def main(args):
    with sys.stdin if args.source == '-' else open(args.source) as f:
        source = f.read()

    header = [
        '#!/usr/bin/env python',
        'import os',
        'import sys',
        'from os.path import *',
        'from sys import stdin, stdout, stderr, exit',
        'from glob import glob',
        'import json',
    ]
    header.append(soft_index_lib)
    header.append(call_lib)

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
        sys.argv = [args.source] + args.script_args
        exec(pycode, {})


if __name__ == '__main__':
    main(args)
