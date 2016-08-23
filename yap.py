#!/usr/bin/env python

# Copyright 2016 Aurélien Nicolas
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import sys
import re
from itertools import starmap


dry_run = False

# No colored output for now
blue = gray = green = orange = red = _yap_color = lambda s, c='': s
debug = lambda *args: None


def parse_cmd(s, flags):
    ''' Extract arguments from a shell command while parsing the {expressions}.
        Return [ (argument, [expressions, ..]), .. ].
    '''
    parse_dollar = not 's' in flags
    parts = []
    current_part = ''
    current_exprs = []

    def finish_arg():
        if current_part:
            parts.append((current_part, current_exprs))
        return '', []

    after = s
    while after:
        before, expr, after = extract_next_space_or_py_expr(after, parse_dollar)
        current_part += before
        if expr is not None:
            if expr == '>':
                current_part, current_exprs = finish_arg()
                parts.append((after.strip(), expr))
                break  # All the rest is the output expression
            elif expr.isspace():  # New argument
                current_part, current_exprs = finish_arg()
            else:  # An expression in the current argument
                current_part += '{}'  # for format()
                if expr == '{}':
                    expr = '{"{}"}'  # Replace literal {} by itself
                current_exprs.append(expr)
    finish_arg()
    return parts


def combine_re(res, flags=0):
    return re.compile(
        '({})'.format(
            ')|('.join(res)),
        flags)

re_symbols_expr_open = combine_re([
    r'(?: \s+ | \{ | > | \$)',   # Start capture
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

    for mopen, quoted, stack in safe_search(re_symbols_expr_open, s):
        if not mopen:
            break

        if mopen.group() == '{':
            for mclose, close_quoted, close_stack in safe_search(
                    re_symbols_expr_close, s, pos=mopen.end()):

                close_depth = len(close_stack)
                if mclose and not close_quoted and close_depth == 0:
                    return ret(mopen, mclose)

        elif mopen.group() == '$':
            if not parse_dollar:
                continue
            for mclose, close_quoted, close_stack in safe_search(
                    re_symbols_dollar_close, s, pos=mopen.end()):

                if mclose:
                    return ret(mopen, mclose)

        # The rest are not interpreted in quotes
        elif quoted:
            continue

        elif mopen.group() == '>':
            return ret(mopen, mopen)

        else:  # Split around the spaces and return
            return ret(mopen, mopen)

        break  # Close not found, ignore. Could raise SyntaxError instead XXX
    return s, None, ''  # Nothing found


def safe_search(re_symbols, s, pos=0, openings='({[', closings=')}]'):
    ' Like re.search() but aware of parenthesis, quotes, and escaping. '
    #escaped = False  # XXX Support escaping
    in_quotes = False
    in_dquotes = False
    quoted = False
    stack = []

    for m in re_symbols.finditer(s, pos):
        c = m.group()
        capture, opening, closing, quote = m.groups()
        # Toggle quote state
        if c == "'":
            in_quotes = not in_quotes
        elif c == '"':
            in_dquotes = not in_dquotes
        quoted = in_quotes or in_dquotes

        if capture is not None:  # Found it
            yield m, quoted, stack

        if c and not quoted:
            if c in openings:
                stack.append(m)
            elif c in closings and stack:
                stack.pop()

    yield None, quoted, stack  # Not found


## Looking for a (!) expression
re_symbols_bang_open = combine_re([
    r'\w*! (?! = )  |  \s* (?: \# .* )? $ ',   # Capture bang or EOL
    r'\(',     # Count only parenthesis
    r'\)',     # Count only parenthesis
    r'["\']',  # Quotes
], re.X | re.MULTILINE)

re_symbols_bang_close = combine_re([
    r' \)  |  $ ',   # Capture end or EOL
    r'[({[]',     # Count all brackets
    r'[)}\]]',    # Count all brackets
    r'["\']',     # Quotes
], re.X | re.MULTILINE)


def split_bang(s):
    ' Extract the next (..!...), yield (pure py, input, flags!, cmd) '
    last_cut = 0

    for mbang, open_quoted, open_stack in safe_search(re_symbols_bang_open, s):
        if not mbang:
            break
        if open_quoted or mbang.start() < last_cut:
            continue

        matched = mbang.group()
        if matched and matched[-1] == '!':
            # Found a bang, look for the end of the expression
            for mclose, close_quoted, close_stack in safe_search(
                    re_symbols_bang_close, s, pos=mbang.end()
            ):

                # Candidate end
                if not mclose or close_quoted or close_stack:
                    continue  # Ignore if in quotes or in pending brackets
                elif open_stack and mclose.group() != ')':
                    continue  # We are in (! expr), wait for the closing bracket
                else:
                    # Found the end
                    # Format: input flags! cmd
                    bang_start = mbang.start()
                    cmd_start = mbang.end()
                    stop = mclose.start()
                    if open_stack:  # Go back to opening (, don't include the ()
                        in_start = open_stack[-1].end()
                    else:  # Not in (), start at: flags! ...
                        in_start = bang_start

                    yield (
                        s[last_cut:in_start],
                        s[in_start:bang_start],
                        s[bang_start:cmd_start],
                        s[cmd_start:stop],
                    )
                    last_cut = stop
                    break  # Done, look for next bang item

        else:  # End-of-line
            if not open_stack:  # End of statement
                stop = mbang.end()
                yield (
                    s[last_cut:stop],
                    None, None, None
                )
                last_cut = stop

    assert last_cut == len(s), 'Did not consume all the source: <%s>' % s[last_cut:]


re_escape_py = re.compile(r'([\\\'"])')

def escape_py(s):
    return re_escape_py.sub(r'\\\1', s)

# XXX Support escaping and keep quoted quotes ('"')
def render_arg(arg):
    arg = arg.strip()
    if arg.startswith('"'):
        assert arg.endswith('"'), 'Dangling quote: %s' % arg
        return escape_py(arg[1:-1])
    else:
        return escape_py(arg)


def render_py_expr(expr):
    if expr.startswith('{'):
        return expand_env_soft(expr[1:-1])
    elif expr.startswith('$'):
        return expand_env_strict(expr)


def render_sh_arg(arg, exprs):
    rendered_arg = render_arg(arg)
    if not exprs:  # No expansion, "plain string"
        return '"{}"'.format(orange(rendered_arg))
    rendered_exprs = [green(render_py_expr(p)) for p in exprs]
    if arg == '{}':  # Only one expression without text
        return 'str({})'.format(rendered_exprs[0])
    # Will evaluate and render all expressions in the argument
    format_args = ', '.join(rendered_exprs)
    return '"{}".format({})'.format(orange(rendered_arg), format_args)


def flags_to_function(flags):
    convert = 'None'
    if 'i' in flags:
        convert = 'int'
    if 'd' in flags:
        convert = 'float'
    if 'j' in flags:
        convert = 'json.loads'
    if 'lf' in flags:
        convert = 'split_lines_fields'
    elif 'fl' in flags:
        convert = 'split_fields_lines'
    elif 'l' in flags:
        convert = 'str.splitlines'
    elif 'f' in flags:
        convert = 'str.split'
    return convert


def render_file(raw, mode):
    expanded = expand_env_soft(raw)
    return 'open({}, "{}")'.format(expanded, mode)


output_flags = ('o', 'e', 'r')

def compile_sh(in_expr, bang, cmd, must_capture):
    ' Compile a shell command into python code'
    flags = bang[:-1]

    # Input as Python expression. Can be a filename, data, or nothing
    in_expr = in_expr.strip()
    if in_expr.endswith('>'):
        infile = render_file(in_expr[:-1], 'r')
    else:
        infile = in_expr or 'None'

    # The command, arguments list and output file
    parts = parse_cmd(cmd.strip(), flags)
    if parts and parts[-1][1] == '>':
        argparts = parts[:-1]
        # Prepare the output file which is a Python expression
        outfile = render_file(parts[-1][0], 'w')
        must_capture = True
    else:
        argparts = parts
        outfile = 'None'

    if must_capture and not any(f in flags for f in output_flags):
        flags += 'o'  # By default, capture stdout if inside an expression

    # Render the expressions in arguments
    cmd_args = [render_sh_arg(arg, exprs) for arg, exprs in argparts]
    if dry_run:
        cmd_args.insert(0, '"echo"')

    # Output conversions
    convert = flags_to_function(flags)

    # Call the process
    process = 'yap_call([{}], "{}", ({}), {}, {})'.format(
        ', '.join(cmd_args), flags, infile, convert, outfile)
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
                r'sys.argv[1:]', py)))


def expand_env_soft(py):
    return re_env.sub(
        r'missingget(os.environ, "\1")',
        re_arg.sub(
            r'missingindex(sys.argv, \1)',
            re_all_args.sub(
                r'sys.argv[1:]', py)))


def expand_python(s):
    ' Expand shell commands in python code. '
    parts = split_bang(s)

    def do_inline_sh(py, in_expr, bang, cmd):
        expanded_py = expand_env_soft(py)
        if not cmd:
            return expanded_py
        pystrip = py.strip()
        mixed = pystrip and pystrip != '('  # Shell inside of a Python expression
        in_expr = in_expr.strip() or 'None'
        return '{}{}'.format(expanded_py, gray(
            compile_sh(in_expr, bang, cmd, must_capture=mixed)))

    return ''.join(starmap(do_inline_sh, parts))


# A convenience function around Popen, configured by letters flags.
# Allows to perform several operations as a single expression (function call).
call_lib = r'''
from subprocess import Popen, PIPE, STDOUT, CalledProcessError
import re

re_escape_sh = re.compile(r'([\\ ])')

def escape_sh(s):
    return re_escape_sh.sub(r'\\\1', s)

def yap_call(cmd, flags='', infile=None, convert=None, outfile=None):
    if 's' in flags:  # Shell mode
        cmd = ' '.join(map(escape_sh, cmd))
    if infile is None or hasattr(infile, 'fileno'):
        infd = infile
        indata = None
    else:
        infd = PIPE
        indata = infile
    outfd = outfile or PIPE

    proc = Popen(
        cmd,
        stdin=infd,
        stdout=outfd if ('o' in flags or 'O' in flags) else None,
        stderr=(
            outfd if 'e' in flags else
            STDOUT if 'O' in flags else None),
        universal_newlines='b' not in flags,
        shell='s' in flags,
        env={} if 'v' in flags else None,
        bufsize=-1,  # Buffered
    )
    if 'p' in flags:  # Run in the background
        return proc

    out, err = proc.communicate(indata)
    if outfile:
        outfile.close()

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
'''

convert_lib = r'''
import json
try:
    from itertools import zip_longest
except ImportError:
    from itertools import izip_longest as zip_longest

def split_lines_fields(s):
    return list(map(str.split, s.splitlines()))

def split_fields_lines(s):
    return list(zip_longest(*split_lines_fields(s)))

def concat(strings):
    return ''.join(strings)

def joinlines(lines):
    return '\n'.join(lines)

def joinfields(fields):
    return ' '.join(fields)

def joinpaths(*args):
    return os.sep.join(args)

def read(filename):
    with open(filename) as fd:
        return fd.read()

def write(filename, content):
    with open(filename, 'w') as fd:
        fd.write(content)

def grep(regex, lines):
    if isinstance(lines, str):
        lines = lines.splitlines()
    regexc = re.compile(regex)
    return filter(regexc.search, lines)
'''


listget_lib = r'''
def listget(array, i, alt=None):
    return array[i] if 0 <= i < len(array) else alt
'''

missing_lib = r'''
class MissingParameter(object):
    def __init__(self, what):
        self.what = what

    def access(self, *args):
        raise KeyError(self.what)

    __str__ = __repr__ = __getitem__ = __getattr__ = __getslice__ = __call__ = access
    __int__ = __add__ = __sub__ = __gt__ = __lt__ = __ge__ = __le__ = access

    def __nonzero__(self):
        return False

    def __bool__(self):
        return False

def missingget(obj, variable):
    v = obj.get(variable)
    return v if v is not None else MissingParameter(variable)

def missingindex(array, i):
    return array[i] if 0 <= i < len(array) else MissingParameter(
        "Argument {}".format(i))
'''

color_lib = r'''
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
'''

imports = '''
import os
from os import listdir
from os.path import *
import sys
from sys import stdin, stdout, stderr, exit
from pprint import pprint
from glob import glob
'''

logging_lib = '''
import logging
from logging import debug, info, warning, error
logging.basicConfig(level=logging.INFO, format='{}: %(levelname)s: %(message)s'.format(__file__))
'''


def make_globals(filename):
    return {
        '__file__': filename,
        '__name__': '__main__',
        '__package__': None,
        '__doc__': None,
    }


def compile_yap(source):

    headers = [
        '#!/usr/bin/env python',
        imports,

        # YaP libs
        logging_lib,
        color_lib,
        convert_lib,
        listget_lib,
        missing_lib,
        call_lib,
    ]

    pycode = '\n'.join(headers) + '\n\n' + expand_python(source)
    return pycode


def run(args):
    " Compile yap file and execute it, or just save it "
    with sys.stdin if args.source == '-' else open(args.source) as f:
        source = f.read()

    pycode = compile_yap(source)

    if args.output:
        if args.output == '-':
            print(pycode)
        else:
            with open(args.output, 'w') as f:
                f.write(pycode)
            print('Compiled to {}'.format(args.output))
    else:
        sys.argv = [args.source] + args.script_args
        exec(compile(pycode, args.source, 'exec'), make_globals(args.source))


def main(cmd_args):
    " Parse arguments and call run() "
    global dry_run

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
    args = parser.parse_args(cmd_args)

    if args.python and not args.output:
        args.output = args.source + '.py'

    dry_run = args.dry_run

    # Optional colored output
    if args.output == '-':
        exec(color_lib, globals())  # Bring in the same code as in outputs

    run(args)


if __name__ == '__main__':
    main(sys.argv[1:])
