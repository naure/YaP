#!/usr/bin/env python

import os
from os import listdir
from os.path import *
import sys
from sys import stdin, stdout, stderr, exit
from pprint import pprint
from glob import glob


import logging
from logging import debug, info, warning, error
logging.basicConfig(format='{}: %(levelname)s: %(message)s'.format(__file__))


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

def read(filename):
    with open(filename) as fd:
        return filename.read()

def write(filename, content):
    with open(filename, 'w') as fd:
        fd.write(content)

def grep(regex, lines):
    if isinstance(lines, str):
        lines = lines.splitlines()
    regexc = re.compile(regex)
    return filter(regexc.search, lines)


def listget(array, i, alt=None):
    return array[i] if 0 <= i < len(array) else alt


class MissingParameter(object):
    def __init__(self, what):
        self.what = what

    def access(self, *args):
        raise KeyError(self.what)

    __str__ = __repr__ = __getitem__ = __getattr__ = __getslice__ = __call__ = access
    __int__ = __add__ = __sub__ = __gt__ = __lt__ = __ge__ = __le__ = access

    def __bool__(self):
        return False

def missingget(obj, variable):
    v = obj.get(variable)
    return v if v is not None else MissingParameter(variable)

def missingindex(array, i):
    return array[i] if 0 <= i < len(array) else MissingParameter(
        "Argument {}".format(i))


from subprocess import Popen, PIPE, STDOUT, CalledProcessError
import re

re_escape_sh = re.compile(r'([\\ ])')

def escape_sh(s):
    return re_escape_sh.sub(r'\\\1', s)

def yap_call(cmd, flags='', infile=None, convert=None, outfile=None):
    if 'h' in flags:  # Shell mode
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
        shell='h' in flags,
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

#!./yap.py
# vim: set ft=python:

__doc__ = '''
Doc string
Usage: cmd.yp command argument
'''


if missingindex(sys.argv, 1) == 'list':
    print(gray('Listing nicely'))
    filenames = listdir(missingindex(sys.argv, 2) or '.')
    for name in filenames:
        print(
            blue(name.rjust(15)),
            joinfields(
                (yap_call(["file", str(name)], "fo", (None), str.split, None))[1:]
            )
        )

elif missingindex(sys.argv, 1) == 'write':
    yap_call(["echo", "Out"], "o", (None), None, open(missingindex(sys.argv, 2) or "default.txt", "w"))

elif missingindex(sys.argv, 1) == 'grep':
    print(concat(
        grep(missingindex(sys.argv, 2), open(missingindex(sys.argv, 3)))
    ))

elif missingindex(sys.argv, 1) == 'demo':
    (yap_call(["echo"], "", ("Hi!"), None, None))
    (yap_call(["cmd"], "", (open("input.txt" , "r")), None, None))
    (yap_call([], "o", ("data"), None, open("out.txt", "w")))
    (yap_call(["echo"], "", (open("input.txt" , "r")), None, None))

else:
    print(red('Unknown command: %s' % missingindex(sys.argv, 1)))
