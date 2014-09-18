#!/usr/bin/env python3

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
    parse_dollar = not 'h' in flags
    parts = []
    current_part = ''
    current_exprs = []
    after = s
    while after:
        before, expr, after = extract_next_space_or_py_expr(after, parse_dollar)
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

        # Just spaces
        elif quoted:
            continue
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
        debug('fooound <%s>' % c)
        capture, opening, closing, quote = m.groups()
        # Toggle quote state
        if c == "'":
            in_quotes = not in_quotes
        elif c == '"':
            in_dquotes = not in_dquotes
        quoted = in_quotes or in_dquotes

        if capture is not None:  # Found it
            debug('caaaapture <%s> ' % c, stack)
            yield m, quoted, stack

        if c and not quoted:
            if c in openings:
                debug('ooopen')
                stack.append(m)
            elif c in closings and stack:
                debug('cloooose')
                stack.pop()
        debug('staaack <%s>  ' % c, stack)

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
    ' Extract the next (..!...), yield (pure py, !expr) '
    last_cut = 0

    for mbang, open_quoted, open_stack in safe_search(re_symbols_bang_open, s):
        if not mbang:
            break
        if open_quoted or mbang.start() < last_cut:
            continue

        matched = mbang.group()
        if matched and matched[-1] == '!':
            debug('loooking for closing. <%s>' % matched)
            # Found a bang, look for the end of the expression
            for mclose, close_quoted, close_stack in safe_search(
                    re_symbols_bang_close, s, pos=mbang.end()
            ):

                debug('candidaaaate closing ', mclose.group(), close_quoted, close_stack)
                # Candidate end
                if not mclose or close_quoted or close_stack:
                    continue  # Ignore if in quotes or in pending brackets
                elif open_stack and mclose.group() != ')':
                    continue  # We are in (! expr), wait for the closing bracket
                else:
                    # Found the end
                    debug('closing')
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
    #yield (s[last_cut:], None)  # Regular end, possibly empty


def old_split_bang(s):
    return safe_split(re_symbols_py, s)

re_symbols_py = re.compile(
    r'''(
    \w*! (?! = )      )|(  # Start capture
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
    arg = arg.strip()
    if arg.startswith('"'):
        assert arg.endswith('"'), 'Dangling quote: %s' % arg
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
re_sh = re.compile(r'(\w*)!', re.DOTALL)

def compile_sh(in_expr, bang, cmd, is_expr):
    ' Compile a shell command into python code'
    flags = bang[:-1]
    if is_expr and not any(f in flags for f in output_flags):
        flags += 'o'  # By default, capture stdout if inside an expression

    # The command and arguments list
    cmd_args = split_and_expand_shell(cmd, flags)
    if dry_run:
        cmd_args.insert(0, '"echo"')

    # Output conversions
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

    # Call the process
    process = 'yap_call([{}], "{}", ({}), {})'.format(
        ', '.join(cmd_args), flags, in_expr, convert)
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


def expand_env_soft(py):
    return re_env.sub(
        r'missingget(os.environ, "\1")',
        re_arg.sub(
            r'missingindex(sys.argv, \1)',
            re_all_args.sub(
                r'sys.argv', py)))


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
            compile_sh(in_expr, bang, cmd, is_expr=mixed)))

    return ''.join(starmap(do_inline_sh, parts))


# A convenience function around Popen, configured by letters flags.
# Allows to perform several operations as a single expression (function call).
call_lib = r'''
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
'''

convert_lib = r'''
import json
from itertools import zip_longest

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
'''


listget_lib = r'''
def listget(array, i, alt=None):
    return array[i] if i < len(array) else alt
'''

missing_lib = r'''
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

usage_lib = '''
def set_usage(usage):
    print(orange('Usage yet not implemented'))
'''


def run(args):
    " Compile yap file and execute it, or just save it "
    with sys.stdin if args.source == '-' else open(args.source) as f:
        source = f.read()

    header = [
        '#!/usr/bin/env python',
        'import os',
        'from os import listdir',
        'from os.path import *',
        'import sys',
        'from sys import stdin, stdout, stderr, exit',
        'from pprint import pprint',
        'from glob import glob',

        # YaP libs
        usage_lib,
        color_lib,
        convert_lib,
        listget_lib,
        missing_lib,
        call_lib,
    ]

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
